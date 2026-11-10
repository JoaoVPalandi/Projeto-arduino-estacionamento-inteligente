/*
  PROJETO INTEGRADOR IoT - SENAI "CONDE JOSÉ VICENTE DE AZEVEDO"
  Estacionamento Inteligente • Vaga 01 (Versão Bancada Minimalista: Máx 80 cm)
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
float ultimaDistanciaValida = 45.0;

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

  // Pisca os 3 LEDs no início para confirmar inicialização
  digitalWrite(pinoLedVerde, HIGH);
  digitalWrite(pinoLedAmarelo, HIGH);
  digitalWrite(pinoLedVermelho, HIGH);
  delay(300);
  digitalWrite(pinoLedVerde, LOW);
  digitalWrite(pinoLedAmarelo, LOW);
  digitalWrite(pinoLedVermelho, LOW);

  Serial.println(F("{\"status\":\"pronto\",\"sistema\":\"Estacionamento IoT SENAI\"}"));
}

// Mede a distância em centímetros através do sensor ultrassônico HC-SR04
// Otimizado para maquete/bancada: timeout de 6000 microssegundos (~1 metro máx)
float medirDistancia() {
  digitalWrite(pinoGatilho, LOW);
  delayMicroseconds(2);
  digitalWrite(pinoGatilho, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinoGatilho, LOW);

  // Timeout de 6000 microssegundos para resposta rápida de bancada
  long duracao = pulseIn(pinoEco, HIGH, 6000);
  if (duracao <= 0) return -1.0;

  float distanciaCalculada = (duracao * 0.0343) / 2.0;
  if (distanciaCalculada < 2.0 || distanciaCalculada > 80.0) return -1.0;

  return distanciaCalculada;
}

// Controla os 3 LEDs visuais de acordo com a distância (Escala compacta máx 80 cm)
// Verde: > 50 cm | Amarelo: 20 a 50 cm | Vermelho: < 20 cm
void controlarLeds(float distanciaCentimetros) {
  if (distanciaCentimetros <= 0 || distanciaCentimetros > 80) {
    digitalWrite(pinoLedVerde, LOW);
    digitalWrite(pinoLedAmarelo, LOW);
    digitalWrite(pinoLedVermelho, LOW);
    return;
  }
  digitalWrite(pinoLedVerde, distanciaCentimetros > 50 ? HIGH : LOW);
  digitalWrite(pinoLedAmarelo, (distanciaCentimetros >= 20 && distanciaCentimetros <= 50) ? HIGH : LOW);
  digitalWrite(pinoLedVermelho, (distanciaCentimetros > 0 && distanciaCentimetros < 20) ? HIGH : LOW);
}

// Controla os bipes do alarme sonoro para bancada (Escala máx 80 cm)
void controlarBuzzer(float distancia) {
  // Acima de 80 cm ou leitura inválida: silêncio absoluto
  if (distancia <= 0 || distancia > 80) {
    desligarBuzzer();
    return;
  }

  // Intervalos de bipe conforme a zona de aproximação
  unsigned long intervaloTotal;
  int frequenciaTom;

  if (distancia < 8) {
    intervaloTotal = 90;  // Perigo iminente (< 8 cm): bipe contínuo / ultra rápido
    frequenciaTom = 2400;
  } else if (distancia < 20) {
    intervaloTotal = 200; // Muito perto (8 a 20 cm): bipes rápidos
    frequenciaTom = 2200;
  } else if (distancia <= 50) {
    intervaloTotal = 450; // Atenção (20 a 50 cm): bipes moderados
    frequenciaTom = 1900;
  } else {
    intervaloTotal = 850; // Longe (50 a 80 cm): bipes lentos
    frequenciaTom = 1600;
  }

  // O bipe fica ligado por 50 milissegundos dentro de cada ciclo
  unsigned long tempoNoCiclo = millis() % intervaloTotal;
  if (tempoNoCiclo < 50) {
    ligarBuzzer(frequenciaTom);
  } else {
    desligarBuzzer();
  }
}

// Processa comandos remotos recebidos via Serial da tela Web ou Raspberry Pi
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
  float distanciaLida = medirDistancia();

  // Se a leitura for válida dentro de 80 cm, atualiza o valor estável
  if (distanciaLida > 0 && distanciaLida <= 80.0) {
    ultimaDistanciaValida = distanciaLida;
  }

  controlarLeds(distanciaLida > 0 ? distanciaLida : ultimaDistanciaValida);
  controlarBuzzer(distanciaLida);
  processarComandosRemotos();

  // Envia JSON pela porta serial a cada 200 milissegundos
  unsigned long agora = millis();
  if (agora - tempoUltimoEnvioSerial >= 200) {
    tempoUltimoEnvioSerial = agora;
    if (distanciaLida > 0 && distanciaLida <= 80.0) {
      Serial.print(F("{\"distancia_cm\":"));
      Serial.print(distanciaLida, 1);
      Serial.println(F("}"));
    }
  }

  delay(20);
}
