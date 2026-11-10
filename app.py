from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, webbrowser, threading, time, json, uvicorn

app = FastAPI(
    title="Estacionamento Inteligente IoT - SENAI",
    description="API REST para monitoramento de vaga com sensor HC-SR04, LEDs e alarme sonoro buzzer (Escala Maquete/Bancada Máx 80 cm).",
    version="1.0.0", docs_url="/docs", redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(PASTA_PROJETO, "static")), name="static")
CAMINHO_BANCO_DADOS = os.path.join(PASTA_PROJETO, 'estacionamento.db')
porta_serial_ativa = None

class DadosLeitura(BaseModel):
    vaga_codigo: str = 'VAGA-01'
    distancia_cm: Optional[float] = None
    distancia: Optional[float] = None

class DadosComandoAtuador(BaseModel):
    atuador: str = 'buzzer'
    acao: str = 'TESTE'

def conectar_banco():
    conexao = sqlite3.connect(CAMINHO_BANCO_DADOS)
    conexao.row_factory = sqlite3.Row
    return conexao

def iniciar_banco():
    with conectar_banco() as conexao:
        conexao.executescript('''
            CREATE TABLE IF NOT EXISTS vagas (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT UNIQUE, nome TEXT, status TEXT DEFAULT 'LIVRE');
            CREATE TABLE IF NOT EXISTS leituras (id INTEGER PRIMARY KEY AUTOINCREMENT, vaga_codigo TEXT, distancia_cm REAL, nivel_alerta TEXT, descricao_alerta TEXT, sensor_status TEXT, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS logs_atuadores (id INTEGER PRIMARY KEY AUTOINCREMENT, atuador TEXT, acao TEXT, origem TEXT, data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        ''')
        if conexao.execute('SELECT COUNT(*) FROM leituras').fetchone()[0] == 0:
            conexao.execute("INSERT INTO leituras (vaga_codigo, distancia_cm, nivel_alerta, descricao_alerta, sensor_status) VALUES ('VAGA-01', 35.0, 'Atenção', 'Bipes moderados', 'Ativo')")
        if conexao.execute('SELECT COUNT(*) FROM logs_atuadores').fetchone()[0] == 0:
            conexao.execute("INSERT INTO logs_atuadores (atuador, acao, origem) VALUES ('buzzer', 'SISTEMA_INICIADO', 'SISTEMA')")

def classificar_distancia(distancia):
    """Escala compacta para maquete/bancada (máx 80 cm):
       - > 50 cm: Longe (Verde, bipes lentos)
       - 20 a 50 cm: Atenção (Amarelo, bipes moderados)
       - < 20 cm: Muito Perto (Vermelho, bipes rápidos)
       - <= 8 cm: Crítico / Parada de Emergência (Vermelho, bipe contínuo)
    """
    if distancia is None or distancia < 0 or distancia > 80:
        return {'nivel': 'Fora de Alcance', 'descricao': 'Sem veículo próximo (> 80 cm)', 'sensor': 'Ativo', 'led': 'Nenhum', 'cor': '#94a3b8'}
    if distancia > 50:
        return {'nivel': 'Longe', 'descricao': 'Bipes lentos', 'sensor': 'Ativo', 'led': 'Verde', 'cor': '#22c55e'}
    if distancia >= 20:
        return {'nivel': 'Atenção', 'descricao': 'Bipes moderados', 'sensor': 'Ativo', 'led': 'Amarelo', 'cor': '#eab308'}
    descricao = 'Bipe contínuo (Emergência)' if distancia <= 8 else 'Bipes rápidos'
    return {'nivel': 'Muito Perto', 'descricao': descricao, 'sensor': 'Ativo', 'led': 'Vermelho', 'cor': '#ef4444'}

def salvar_leitura(codigo_vaga, distancia):
    info = classificar_distancia(distancia)
    with conectar_banco() as conexao:
        conexao.execute('''
            INSERT INTO leituras (vaga_codigo, distancia_cm, nivel_alerta, descricao_alerta, sensor_status) VALUES (?, ?, ?, ?, ?)
        ''', (codigo_vaga, distancia, info['nivel'], info['descricao'], info['sensor']))
    return info

def registrar_comando_atuador(atuador, acao, origem='WEB'):
    global porta_serial_ativa
    with conectar_banco() as conexao:
        conexao.execute("INSERT INTO logs_atuadores (atuador, acao, origem) VALUES (?, ?, ?)", (atuador, acao, origem))
    if porta_serial_ativa:
        try:
            porta_serial_ativa.write(f"{atuador[0].upper()}:{acao}\n".encode('utf-8'))
        except Exception:
            pass

def monitorar_leitura_arduino():
    global porta_serial_ativa
    try:
        import serial, serial.tools.list_ports  # type: ignore
        while True:
            try:
                portas = [item.device for item in serial.tools.list_ports.comports()]
                porta = next((p for p in ['/dev/ttyACM0', '/dev/ttyUSB0', 'COM3', 'COM4', 'COM5'] if p in portas), portas[0] if portas else None)
                if porta:
                    conexao = serial.Serial(porta, 9600, timeout=1.0)
                    porta_serial_ativa = conexao
                    time.sleep(2)
                    while True:
                        linha = conexao.readline().decode('utf-8', errors='ignore').strip()
                        if linha:
                            try:
                                v = float(json.loads(linha).get('distancia_cm', linha))
                                if 0 <= v <= 80: salvar_leitura('VAGA-01', v)
                            except (ValueError, json.JSONDecodeError): pass
                        time.sleep(0.04)
            except Exception:
                porta_serial_ativa = None
                time.sleep(3)
    except ImportError:
        pass

# --------------------------------------------------
# ROTAS DA API E INTERFACE WEB
# --------------------------------------------------

@app.get('/', response_class=FileResponse, include_in_schema=False)
def pagina_inicial():
    """Entrega a tela HTML do painel."""
    return FileResponse(os.path.join(PASTA_PROJETO, "templates", "index.html"))

@app.get('/api/vaga/status', summary="Status da Vaga em Tempo Real", tags=["Vaga"])
def obter_status_vaga():
    """Retorna dados ao vivo: distância, alertas, LEDs e status do sensor."""
    with conectar_banco() as conexao:
        leitura = conexao.execute("SELECT * FROM leituras ORDER BY id DESC LIMIT 1").fetchone()

    distancia = leitura['distancia_cm'] if leitura else 35.0
    info = classificar_distancia(distancia)

    return {
        'vaga_codigo': 'VAGA-01',
        'distancia_cm': round(distancia, 1),
        'nivel_alerta': info['nivel'],
        'descricao_alerta': info['descricao'],
        'sensor_status': info['sensor'],
        'status_sensor': info['sensor'],
        'led': info['led'],
        'cor': info['cor'],
        'data_hora': leitura['data_hora'] if leitura else '--:--'
    }

# Suporta POST (envio) e GET (consulta no navegador sem erro 405)
@app.post('/api/leituras', status_code=201, summary="Enviar Nova Leitura de Distância", tags=["Leituras"])
def receber_nova_leitura(dados: DadosLeitura):
    """Recebe nova medição do sensor HC-SR04, leitor serial ou simulador."""
    v = dados.distancia_cm if dados.distancia_cm is not None else dados.distancia
    if v is None: return JSONResponse(status_code=400, content={'erro': 'distancia_cm é obrigatório'})
    try:
        distancia = float(v)
    except ValueError:
        return JSONResponse(status_code=400, content={'erro': 'distancia_cm deve ser número'})

    info = salvar_leitura(dados.vaga_codigo, distancia)
    return {'sucesso': True, 'distancia_cm': distancia, 'nivel_alerta': info['nivel'], 'descricao_alerta': info['descricao'], 'led': info['led'], 'cor': info['cor']}

@app.get('/api/leituras', summary="Consultar Leituras Recentes", tags=["Leituras"])
def listar_leituras_recentes():
    """Abre no navegador sem erro 405 exibindo as últimas medições."""
    with conectar_banco() as conexao:
        linhas = conexao.execute("SELECT * FROM leituras ORDER BY id DESC LIMIT 10").fetchall()
    return {'total': len(linhas), 'leituras': [dict(r) for r in linhas]}

@app.get('/api/leituras/historico', summary="Histórico das Últimas Leituras", tags=["Leituras"])
def obter_historico_leituras():
    """Retorna as últimas 8 medições para montar a tabela no painel."""
    with conectar_banco() as conexao:
        linhas = conexao.execute("SELECT * FROM leituras ORDER BY id DESC LIMIT 8").fetchall()
    return {'historico': [dict(r) for r in linhas]}

# Suporta POST (envio de comando) e GET (consulta sem erro 405)
@app.post('/api/atuadores/comando', summary="Enviar Comando ao Atuador", tags=["Atuadores"])
def executar_comando_atuador(dados: DadosComandoAtuador):
    """Envia comandos para o alarme sonoro (buzzer)."""
    registrar_comando_atuador(dados.atuador, dados.acao, 'WEB')
    return {'sucesso': True, 'atuador': dados.atuador, 'acao': dados.acao}

@app.get('/api/atuadores/comando', summary="Consultar Histórico de Atuadores", tags=["Atuadores"])
def consultar_comandos_atuadores():
    """Abre no navegador sem erro 405 exibindo comandos enviados."""
    with conectar_banco() as conexao:
        linhas = conexao.execute("SELECT * FROM logs_atuadores ORDER BY id DESC LIMIT 10").fetchall()
    return {'logs_atuadores': [dict(r) for r in linhas]}

def abrir_navegador_automatico():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    iniciar_banco()
    print("=" * 65 + "\n   ESTACIONAMENTO IoT - SENAI (Escala Bancada Máx 80 cm)\n   Painel Web:   http://127.0.0.1:5000\n   Docs Swagger: http://127.0.0.1:5000/docs\n" + "=" * 65)
    threading.Thread(target=monitorar_leitura_arduino, daemon=True).start()
    threading.Thread(target=abrir_navegador_automatico, daemon=True).start()
    uvicorn.run(app, host='0.0.0.0', port=5000)
