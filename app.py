# ==============================================================================
# PROJETO INTEGRADOR IoT - SENAI "CONDE JOSÉ VICENTE DE AZEVEDO"
# Estacionamento Inteligente • Back-end API REST (FastAPI + SQLite + Serial)
# Autores: João Pradela, João Palandi e Pedro Cesar
# ==============================================================================
#
# PAPEL DESTE ARQUIVO NO SISTEMA:
# ------------------------------------------------------------------------------
# 1. GATEWAY HARDWARE: Abre e escuta a porta Serial USB do Arduino em background,
#    recebendo as distâncias em formato JSON a 9600 bps.
# 2. BANCO DE DADOS: Persiste o histórico de medições e comandos no SQLite local.
# 3. API REST (FASTAPI): Expõe endpoints HTTP para que o Front-end (navegador)
#    consulte o status da vaga em tempo real e envie comandos ao Buzzer.
# ==============================================================================

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, webbrowser, threading, time, json, uvicorn, socket

# ------------------------------------------------------------------------------
# 1. INICIALIZAÇÃO DA APLICAÇÃO FASTAPI
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Estacionamento Inteligente IoT - SENAI",
    description="API REST para monitoramento de vaga com sensor HC-SR04, LEDs e alarme sonoro buzzer (Escala Maquete/Bancada Máx 80 cm).",
    version="1.0.0", docs_url="/docs", redoc_url="/redoc"
)

# CORS: Permite que navegadores em outras máquinas (computador, celular) acessem a API
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# Caminhos do projeto e montagem de arquivos estáticos (/static para CSS e JS)
PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(PASTA_PROJETO, "static")), name="static")
CAMINHO_BANCO_DADOS = os.path.join(PASTA_PROJETO, 'estacionamento.db')

# Referência global
porta_serial_ativa = None

# ------------------------------------------------------------------------------
# 2. MODELOS DE DADOS (PYDANTIC SCHEMAS)
# ------------------------------------------------------------------------------
# Valida os dados enviados nas requisições POST
class DadosLeitura(BaseModel):
    vaga_codigo: str = 'VAGA-01'
    distancia_cm: Optional[float] = None
    distancia: Optional[float] = None

class DadosComandoAtuador(BaseModel):
    atuador: str = 'buzzer'
    acao: str = 'TESTE'

# ------------------------------------------------------------------------------
# 3. CAMADA DE BANCO DE DADOS (SQLITE)
# ------------------------------------------------------------------------------
def conectar_banco():
    """Abre conexão com o banco de dados SQLite e configura retorno em modo dicionário (Row)."""
    conexao = sqlite3.connect(CAMINHO_BANCO_DADOS)
    conexao.row_factory = sqlite3.Row
    return conexao

def iniciar_banco():
    """Cria as tabelas relacionais do sistema caso ainda não existam."""
    with conectar_banco() as conexao:
        conexao.executescript('''
            -- Tabela de vagas cadastradas no estacionamento
            CREATE TABLE IF NOT EXISTS vagas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE,
                nome TEXT,
                status TEXT DEFAULT 'LIVRE'
            );
            -- Tabela de telemetria histórica de distâncias medidas
            CREATE TABLE IF NOT EXISTS leituras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vaga_codigo TEXT,
                distancia_cm REAL,
                nivel_alerta TEXT,
                descricao_alerta TEXT,
                sensor_status TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            -- Tabela de auditoria para comandos remotos enviados aos atuadores
            CREATE TABLE IF NOT EXISTS logs_atuadores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atuador TEXT,
                acao TEXT,
                origem TEXT,
                data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        # Insere dados padrão se as tabelas estiverem vazias
        if conexao.execute('SELECT COUNT(*) FROM leituras').fetchone()[0] == 0:
            conexao.execute("INSERT INTO leituras (vaga_codigo, distancia_cm, nivel_alerta, descricao_alerta, sensor_status) VALUES ('VAGA-01', 35.0, 'Atenção', 'Bipes moderados', 'Ativo')")
        if conexao.execute('SELECT COUNT(*) FROM logs_atuadores').fetchone()[0] == 0:
            conexao.execute("INSERT INTO logs_atuadores (atuador, acao, origem) VALUES ('buzzer', 'SISTEMA_INICIADO', 'SISTEMA')")

# ------------------------------------------------------------------------------
# 4. REGRAS DE NEGÓCIO: CLASSIFICAÇÃO DA DISTÂNCIA
# ------------------------------------------------------------------------------
def classificar_distancia(distancia):
    """
    Classifica a medição do sensor em zonas de segurança (Escala Máx 80 cm):
      - > 50 cm: Longe / Seguro (LED Verde, bipes lentos)
      - 20 a 50 cm: Atenção (LED Amarelo, bipes moderados)
      - < 20 cm: Muito Perto (LED Vermelho, bipes rápidos)
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
    """Calcula a zona de alerta e persiste a nova leitura no SQLite."""
    info = classificar_distancia(distancia)
    with conectar_banco() as conexao:
        conexao.execute('''
            INSERT INTO leituras (vaga_codigo, distancia_cm, nivel_alerta, descricao_alerta, sensor_status) VALUES (?, ?, ?, ?, ?)
        ''', (codigo_vaga, distancia, info['nivel'], info['descricao'], info['sensor']))
    return info

def registrar_comando_atuador(atuador, acao, origem='WEB'):
    """Registra o comando no banco e envia o pacote via Serial para o Arduino físico."""
    global porta_serial_ativa
    with conectar_banco() as conexao:
        conexao.execute("INSERT INTO logs_atuadores (atuador, acao, origem) VALUES (?, ?, ?)", (atuador, acao, origem))
    # Se o Arduino estiver conectado no USB, transmite o comando (ex: "B:TESTE\n")
    if porta_serial_ativa:
        try:
            porta_serial_ativa.write(f"{atuador[0].upper()}:{acao}\n".encode('utf-8'))
        except Exception:
            pass

# ------------------------------------------------------------------------------
# 5. THREAD DE COMUNICAÇÃO SERIAL COM O ARDUINO (USB)
# ------------------------------------------------------------------------------
def monitorar_leitura_arduino():
    """
    Roda continuamente em segundo plano (background thread).
    Detecta automaticamente se está no Linux (/dev/ttyACM0, /dev/ttyUSB0)
    ou Windows (COM3, COM4, etc.) e consome o JSON serial gerado pelo Arduino.
    """
    global porta_serial_ativa
    try:
        import serial, serial.tools.list_ports  # type: ignore
        while True:
            try:
                # Procura portas disponíveis
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
                                # Converte o JSON enviado pelo Arduino: {"distancia_cm": 35.0}
                                v = float(json.loads(linha).get('distancia_cm', linha))
                                if 0 <= v <= 80: salvar_leitura('VAGA-01', v)
                            except (ValueError, json.JSONDecodeError): pass
                        time.sleep(0.04)
            except Exception:
                porta_serial_ativa = None
                time.sleep(3)
    except ImportError:
        pass

# ------------------------------------------------------------------------------
# 6. ROTAS HTTP DA API REST E VIEWS
# ------------------------------------------------------------------------------

# Rota principal: entrega a interface HTML do painel web
@app.get('/', response_class=FileResponse, include_in_schema=False)
def pagina_inicial():
    """Entrega o arquivo index.html da pasta templates."""
    return FileResponse(os.path.join(PASTA_PROJETO, "templates", "index.html"))

# Rota de telemetria ao vivo: chamada pelo Front-end a cada 350ms
@app.get('/api/vaga/status', summary="Status da Vaga em Tempo Real", tags=["Vaga"])
def obter_status_vaga():
    """Retorna os dados em tempo real: distância, cor, alertas e status do sensor."""
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

# Rota para receber novas leituras (usada pelo simulador ou sensores externos)
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

# Rota para listar medições recentes
@app.get('/api/leituras', summary="Consultar Leituras Recentes", tags=["Leituras"])
def listar_leituras_recentes():
    """Retorna as últimas 10 medições salvas no banco."""
    with conectar_banco() as conexao:
        linhas = conexao.execute("SELECT * FROM leituras ORDER BY id DESC LIMIT 10").fetchall()
    return {'total': len(linhas), 'leituras': [dict(r) for r in linhas]}

# Rota consumida pelo Front-end para preencher a tabela de histórico
@app.get('/api/leituras/historico', summary="Histórico das Últimas Leituras", tags=["Leituras"])
def obter_historico_leituras():
    """Retorna as últimas 8 medições formatadas para montar a tabela no painel."""
    with conectar_banco() as conexao:
        linhas = conexao.execute("SELECT * FROM leituras ORDER BY id DESC LIMIT 8").fetchall()
    return {'historico': [dict(r) for r in linhas]}

# Rota para acionamento remoto de atuadores (Buzzer)
@app.post('/api/atuadores/comando', summary="Enviar Comando ao Atuador", tags=["Atuadores"])
def executar_comando_atuador(dados: DadosComandoAtuador):
    """Envia comandos para o alarme sonoro (buzzer) físico e registra no banco."""
    registrar_comando_atuador(dados.atuador, dados.acao, 'WEB')
    return {'sucesso': True, 'atuador': dados.atuador, 'acao': dados.acao}

# Rota para consultar o histórico de comandos enviados
@app.get('/api/atuadores/comando', summary="Consultar Histórico de Atuadores", tags=["Atuadores"])
def consultar_comandos_atuadores():
    """Exibe comandos enviados anteriormente para auditoria."""
    with conectar_banco() as conexao:
        linhas = conexao.execute("SELECT * FROM logs_atuadores ORDER BY id DESC LIMIT 10").fetchall()
    return {'logs_atuadores': [dict(r) for r in linhas]}

# ------------------------------------------------------------------------------
# 7. FUNÇÕES AUXILIARES DE INICIALIZAÇÃO E REDE
# ------------------------------------------------------------------------------
def obter_ip_local():
    """Descobre o endereço IP real da placa na rede local (ex: 192.168.x.x ou 10.x.x.x)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

def abrir_navegador_automatico():
    """Tenta abrir a interface no navegador caso o sistema tenha interface gráfica ativa."""
    time.sleep(1.5)
    try:
        webbrowser.open('http://127.0.0.1:5000')
    except Exception:
        pass

# ------------------------------------------------------------------------------
# 8. PONTO DE ENTRADA PRINCIPAL
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    # 1. Cria/valida as tabelas do SQLite
    iniciar_banco()
    
    # 2. Descobre o IP na rede para facilitar o acesso
    ip_rede = obter_ip_local()
    
    print("=" * 65)
    print("   ESTACIONAMENTO IoT - SENAI (Escala Bancada Máx 80 cm)")
    print(f"   Acesse pelo seu Computador/Celular:")
    print(f"   👉 http://{ip_rede}:5000")
    print(f"   👉 http://rpi06.local:5000")
    print(f"   Docs Swagger: http://{ip_rede}:5000/docs")
    print("=" * 65)
    
    # 3. Inicia thread da serial e abre navegador
    threading.Thread(target=monitorar_leitura_arduino, daemon=True).start()
    threading.Thread(target=abrir_navegador_automatico, daemon=True).start()
    
    # 4. Inicia o servidor web ASGI Uvicorn na porta 5000
    uvicorn.run(app, host='0.0.0.0', port=5000)
