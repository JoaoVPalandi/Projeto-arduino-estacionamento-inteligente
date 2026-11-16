"""
==============================================================================
PROJETO INTEGRADOR IoT - SENAI "CONDE JOSÉ VICENTE DE AZEVEDO"
Gateway Serial / MQTT para Raspberry Pi 3B
Autores: João Pradela, João Palandi e Pedro Cesar
==============================================================================

PAPEL DESTE MÓDULO NA ARQUITETURA IoT:
------------------------------------------------------------------------------
1. TELEMETRIA M2M (Máquina para Máquina):
   Lê a distância enviada pelo Arduino Uno via USB Serial (9600 bps).
2. PROTOCOLO MQTT:
   Publica os dados no tópico 'estacionamento/vaga01/distancia' através
   do Broker Mosquitto local, permitindo que outros dispositivos
   ou sistemas externos consumam as leituras de forma leve e desacoplada.
3. PROTOCOLO HTTP:
   Repassa simultaneamente a medição para a API REST local (FastAPI :5000),
   alimentando o banco de dados e a interface web.
==============================================================================
"""

import time, json, urllib.request

# Constantes de configuração de rede e tópicos
ENDERECO_API = "http://127.0.0.1:5000/api/leituras"
SERVIDOR_BROKER_MQTT = "localhost"
TOPICO_DISTANCIA_MQTT = "estacionamento/vaga01/distancia"

# ------------------------------------------------------------------------------
# CONEXÃO COM O BROKER MQTT (MOSQUITTO)
# ------------------------------------------------------------------------------
cliente_mqtt = None
try:
    import paho.mqtt.client as mqtt  # type: ignore
    cliente_mqtt = mqtt.Client()
    cliente_mqtt.connect(SERVIDOR_BROKER_MQTT, 1883, 60)
    print(f"[MQTT] Conectado com sucesso ao Broker Mosquitto em ({SERVIDOR_BROKER_MQTT}:1883)")
except Exception:
    print("[MQTT] Broker Mosquitto não detectado ou paho-mqtt ausente. Operando em modo de contingência (HTTP/Serial).")

def enviar_leitura_sensor(distancia_centimetros):
    """
    Envia a leitura recebida do sensor para os dois destinos:
    1. Broker MQTT (Pub/Sub leve para a rede IoT)
    2. API REST HTTP (Persistência no SQLite e tela web)
    """
    dados_envio = {
        "vaga_codigo": "VAGA-01",
        "distancia_cm": float(distancia_centimetros)
    }
    mensagem_json = json.dumps(dados_envio)

    # 1. Publica no Broker MQTT
    if cliente_mqtt:
        try:
            cliente_mqtt.publish(TOPICO_DISTANCIA_MQTT, mensagem_json)
        except Exception:
            pass

    # 2. Envia para a API REST via POST HTTP
    try:
        requisicao_http = urllib.request.Request(
            ENDERECO_API,
            data=mensagem_json.encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(requisicao_http, timeout=1.0) as resposta_servidor:
            corpo_resposta = json.loads(resposta_servidor.read().decode('utf-8'))
            print(f"[GATEWAY] Distância: {distancia_centimetros:>5.1f} cm | Nível: {corpo_resposta.get('nivel_alerta', '')}")
    except Exception:
        pass

def iniciar_gateway_serial_mqtt():
    """
    Detecta a porta USB do Arduino (/dev/ttyACM0, /dev/ttyUSB0 ou COM),
    conecta a 9600 bps e processa os dados em loop contínuo.
    """
    print("=" * 60 + "\n   GATEWAY SERIAL / MQTT - RASPBERRY PI 3B\n" + "=" * 60)
    try:
        import serial, serial.tools.list_ports  # type: ignore
    except ImportError:
        print("[ERRO] Instale a biblioteca serial com: pip install pyserial")
        return

    # Varre as portas conectadas
    portas_conectadas = [item.device for item in serial.tools.list_ports.comports()]
    porta_alvo = next((p for p in ['/dev/ttyACM0', '/dev/ttyUSB0', 'COM3', 'COM4', 'COM5'] if p in portas_conectadas), portas_conectadas[0] if portas_conectadas else None)

    if not porta_alvo:
        print("[AVISO] Nenhum Arduino detectado. Conecte o cabo USB e tente novamente.")
        return

    print(f"Conectando ao Arduino na porta: {porta_alvo} a 9600 bps...")
    try:
        conexao_serial = serial.Serial(porta_alvo, 9600, timeout=1.0)
    except Exception as erro_abertura:
        print(f"\n[ERRO NA PORTA {porta_alvo}] Não foi possível abrir a porta:")
        print("  -> Certifique-se de fechar o Monitor Serial da IDE do Arduino.")
        print("  -> Se 'app.py' já estiver lendo a serial, a leitura já está ativa!\n")
        return

    try:
        time.sleep(2)
        print("Conectado com sucesso! Monitorando leituras do sensor HC-SR04...\n")

        while True:
            linha_lida = conexao_serial.readline().decode('utf-8', errors='ignore').strip()
            if linha_lida:
                try:
                    dados = json.loads(linha_lida)
                    if isinstance(dados, dict) and 'distancia_cm' in dados:
                        valor = float(dados['distancia_cm'])
                        if 0 <= valor <= 80:
                            enviar_leitura_sensor(valor)
                except Exception:
                    pass
            time.sleep(0.04)
    except KeyboardInterrupt:
        print("\nGateway finalizado pelo usuário.")
    finally:
        conexao_serial.close()

if __name__ == '__main__':
    iniciar_gateway_serial_mqtt()
