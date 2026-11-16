/*
  PROJETO INTEGRADOR IoT - SENAI "CONDE JOSÉ VICENTE DE AZEVEDO"
  Estacionamento Inteligente • Vaga 01 (Versão Bancada: Máx 80 cm)
  Autores: João Pradela, João Palandi e Pedro Cesar

  Pinagem no Arduino Uno R3:
  - Sensor Ultrassônico Gatilho (Trig) -> Pino Digital 9
  - Sensor Ultrassônico Retorno (Echo)  -> Pino Digital 10
  - Buzzer (Alarme Sonoro)              -> Pino Digital 8
  - LED Verde                           -> Pino Digital 5 (resistor 220 ohms)
  - LED Amarelo                         -> Pino Digital 6 (resistor 220 ohms)
  - LED Vermelho                        -> Pino Digital 7 (resistor 220 ohms)
  - GND comum                           -> Pino GND do Arduino
*/

// Definição dos pinos em português
const int pinoGatilho = 9;
const int pinoEco = 10;
const int pinoAlarmeSonoro = 8;
const int pinoLedVerde = 5;
const int pinoLedAmarelo = 6;
const int pinoLedVermelho = 7;

// Variáveis globais
unsigned long tempoUltimoEnvioSerial = 0;
float distanciaAtual = 60.0; // Inicializa em zona livre

// Liga o buzzer com segurança (funciona tanto para buzzer ativo quanto passivo)
void ligarBuzzer(int frequenciaTom) {
  tone(pinoAlarmeSonoro, frequenciaTom);
  digitalWrite(pinoAlarmeSonoro, HIGH);
}

// Desliga o buzzer completamente
void desligarBuzzer() {
  noTone(pinoAlarmeSonoro);
  digitalWrite(pinoAlarmeSonoro, LOW);
}

void setup() {
  Serial.begin(9600);

  pinMode(pinoGatilho, OUTPUT);
  pinMode(pinoEco, INPUT);
  pinMode(pinoAlarmeSonoro, OUTPUT);
  pinMode(pinoLedVerde, OUTPUT);
  pinMode(pinoLedAmarelo, OUTPUT);
  pinMode(pinoLedVermelho, OUTPUT);

  // Inicializa o buzzer desligado
  desligarBuzzer();

  // Pisca os 3 LEDs no início para confirmar funcionamento elétrico
  digitalWrite(pinoLedVerde, HIGH);
  digitalWrite(pinoLedAmarelo, HIGH);
  digitalWrite(pinoLedVermelho, HIGH);
  delay(400);
  digitalWrite(pinoLedVerde, LOW);
  digitalWrite(pinoLedAmarelo, LOW);
  digitalWrite(pinoLedVermelho, LOW);

  Serial.println(F("{\"status\":\"pronto\",\"sistema\":\"Estacionamento IoT SENAI\"}"));
}

// Mede a distância em centímetros através do sensor HC-SR04
// Timeout ajustado para 15000 microssegundos (~2,5 metros) para não perder eco
float medirDistancia() {
  digitalWrite(pinoGatilho, LOW);
  delayMicroseconds(2);
  digitalWrite(pinoGatilho, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinoGatilho, LOW);

  long duracao = pulseIn(pinoEco, HIGH, 15000);
  if (duracao <= 0) {
    return 100.0; // Sem eco ou desaproximou: livre (> 80 cm)
  }

  float distanciaCalculada = (duracao * 0.0343) / 2.0;
  if (distanciaCalculada < 2.0) return 2.0;

  return distanciaCalculada;
}

// Controla os 3 LEDs visuais:
// Verde: > 45 cm (livre / afastado)
// Amarelo: 18 a 45 cm (atenção)
// Vermelho: < 18 cm (muito perto / parada)
void controlarLeds(float dist) {
  if (dist > 45.0) {
    digitalWrite(pinoLedVerde, HIGH);
    digitalWrite(pinoLedAmarelo, LOW);
    digitalWrite(pinoLedVermelho, LOW);
  } else if (dist >= 18.0) {
    digitalWrite(pinoLedVerde, LOW);
    digitalWrite(pinoLedAmarelo, HIGH);
    digitalWrite(pinoLedVermelho, LOW);
  } else {
    digitalWrite(pinoLedVerde, LOW);
    digitalWrite(pinoLedAmarelo, LOW);
    digitalWrite(pinoLedVermelho, HIGH);
  }
}

// Controla os bipes do alarme sonoro
void controlarBuzzer(float dist) {
  // Desaproximou (> 80 cm): silêncio total
  if (dist > 80.0) {
    desligarBuzzer();
    return;
  }

  unsigned long intervaloTotal;
  int frequenciaTom;

  if (dist < 8.0) {
    intervaloTotal = 80;  // Crítico / emergência: bipe contínuo
    frequenciaTom = 2400;
  } else if (dist < 18.0) {
    intervaloTotal = 180; // Muito perto: bipes rápidos
    frequenciaTom = 2200;
  } else if (dist <= 45.0) {
    intervaloTotal = 400; // Atenção: bipes médios
    frequenciaTom = 1900;
  } else {
    intervaloTotal = 800; // Longe (45 a 80 cm): bipes lentos
    frequenciaTom = 1600;
  }

  unsigned long tempoNoCiclo = millis() % intervaloTotal;
  if (tempoNoCiclo < 45) {
    ligarBuzzer(frequenciaTom);
  } else {
    desligarBuzzer();
  }
}

// Processa comandos remotos recebidos via Serial
void processarComandosRemotos() {
  if (Serial.available() > 0) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();

    if (comando.startsWith("B:TESTE")) {
      ligarBuzzer(2000);
      delay(200);
      desligarBuzzer();
    }
  }
}

void loop() {
  distanciaAtual = medirDistancia();

  controlarLeds(distanciaAtual);
  controlarBuzzer(distanciaAtual);
  processarComandosRemotos();

  // Envia JSON pela porta serial a cada 200 milissegundos
  unsigned long agora = millis();
  if (agora - tempoUltimoEnvioSerial >= 200) {
    tempoUltimoEnvioSerial = agora;
    float distEnvio = (distanciaAtual > 80.0) ? 80.0 : distanciaAtual;
    Serial.print(F("{\"distancia_cm\":"));
    Serial.print(distEnvio, 1);
    Serial.println(F("}"));
  }

  delay(25);
}
