🔧 Guia de Montagem do Arduino — Estacionamento Inteligente IoT

Projeto Integrador SENAI — João Pradela, João Palandi e Pedro Cesar

📦 Lista de Materiais
Qtd	Componente	Observação
1	Arduino Uno R3	Placa principal
1	Protoboard (400 furos)	Para montar o circuito sem solda
1	Sensor Ultrassônico HC-SR04	Mede distância de 2 cm a 400 cm
1	Buzzer Ativo 5V	Alarme sonoro de proximidade
1	LED Verde (5mm)	Indica vaga livre (> 100 cm)
1	LED Amarelo (5mm)	Indica atenção (50–100 cm)
1	LED Vermelho (5mm)	Indica perigo (< 50 cm)
3	Resistor 220Ω (vermelho-vermelho-marrom)	Um para cada LED
~12	Jumpers macho-macho	Fios coloridos para as conexões
1	Cabo USB Tipo A/B	Conecta o Arduino ao computador ou ao Raspberry Pi

📌 Tabela de Pinagem — Resumo Rápido
Componente	Pino do Componente	Pino do Arduino
Sensor HC-SR04	VCC	5V
Sensor HC-SR04	Trig (Gatilho)	Pino Digital 9
Sensor HC-SR04	Echo (Retorno)	Pino Digital 10
Sensor HC-SR04	GND	GND
Buzzer	Positivo (+)	Pino Digital 8
Buzzer	Negativo (−)	GND
LED Verde	Anodo (+) perna longa	Pino Digital 5 (via resistor 220Ω)
LED Verde	Catodo (−) perna curta	GND
LED Amarelo	Anodo (+) perna longa	Pino Digital 6 (via resistor 220Ω)
LED Amarelo	Catodo (−) perna curta	GND
LED Vermelho	Anodo (+) perna longa	Pino Digital 7 (via resistor 220Ω)
LED Vermelho	Catodo (−) perna curta	GND

🪛 Passo a Passo da Montagem

Passo 1 — Preparar a Protoboard
Coloque o Arduino Uno ao lado da Protoboard sobre a mesa.
Conecte um jumper da saída 5V do Arduino até a trilha vermelha (+) da protoboard.
Conecte um jumper da saída GND do Arduino até a trilha azul (−) da protoboard.

IMPORTANT:
A trilha vermelha é a alimentação de 5V e a trilha azul é o terra (GND). Todos os componentes vão compartilhar essas duas trilhas.

Passo 2 — Montar o Sensor Ultrassônico HC-SR04
O sensor tem 4 pinos (da esquerda para direita, olhando de frente):

 ┌───────────────────┐
 │  (●)    HC-SR04  (●) │
 │                       │
 │  VCC  TRIG  ECHO  GND │
 └──┬────┬────┬────┬──┘
    │    │    │    │
VCC → Conecte com jumper à trilha vermelha (+) da protoboard (5V).
Trig → Conecte com jumper ao Pino Digital 9 do Arduino.
Echo → Conecte com jumper ao Pino Digital 10 do Arduino.
GND → Conecte com jumper à trilha azul (−) da protoboard (GND).

TIP:
Posicione o sensor na borda da protoboard, virado para fora, para que ele consiga medir a distância até o obstáculo sem obstruções.

Passo 3 — Montar os 3 LEDs (Verde, Amarelo e Vermelho)
Para cada LED, o esquema é o mesmo:

  Pino Digital do Arduino
         │
    ┌────┤
    │  Resistor 220Ω
    └────┤
         │
    Perna LONGA do LED (Anodo +)
         │
    ─────◄──── LED acende aqui
         │
    Perna CURTA do LED (Catodo −)
         │
    Trilha azul GND (−)

Montagem:
- LED Verde:
  Perna longa (+) → resistor 220Ω → Pino Digital 5
  Perna curta (−) → trilha azul (GND)

- LED Amarelo:
  Perna longa (+) → resistor 220Ω → Pino Digital 6
  Perna curta (−) → trilha azul (GND)

- LED Vermelho:
  Perna longa (+) → resistor 220Ω → Pino Digital 7
  Perna curta (−) → trilha azul (GND)

CAUTION:
Nunca conecte um LED diretamente no Arduino sem o resistor! Sem o resistor de 220Ω, o LED queima em segundos.

Passo 4 — Montar o Buzzer (Alarme Sonoro)
O buzzer tem 2 pernas (uma mais longa que a outra, ou com marcação +):
- Perna positiva (+) (mais longa ou marcada) → Conecte ao Pino Digital 8 do Arduino.
- Perna negativa (−) (mais curta) → Conecte à trilha azul (GND) da protoboard.

NOTE:
Se o buzzer for ativo (já tem um oscilador interno), ele emite o som ao energizar. Se for passivo, o código usa tone() para gerar a frequência sonora — ambos funcionam com o código deste projeto.

Passo 5 — Conectar o Cabo USB e Enviar o Código
Conecte o cabo USB Tipo A/B entre o Arduino e o computador.
Abra o Arduino IDE no computador (ou use a linha de comando).
Selecione Arduino Uno e a porta correspondente.
Abra o arquivo arduino.ino e faça o upload.
Assim que o código subir, os 3 LEDs vão piscar juntos por 0,3 segundo e depois apagar — isso confirma que a inicialização funcionou.

✅ Teste Rápido
Abra o Monitor Serial a 9600 baud.
Aproxime a mão do sensor HC-SR04:
- > 100 cm → LED Verde acende, bipes lentos
- 50–100 cm → LED Amarelo acende, bipes moderados
- 15–50 cm → LED Vermelho acende, bipes rápidos
- < 15 cm → LED Vermelho acende, bipe contínuo (parada de emergência!)

🔌 Diagrama Resumido das Conexões
                    ARDUINO UNO R3
              ┌──────────────────────┐
              │                      │
    HC-SR04   │   D9  ←── Trig       │
              │   D10 ←── Echo       │
              │                      │
    Buzzer    │   D8  ←── (+)        │
              │                      │
    LED Verde │   D5  ──┤220Ω├── (+) │
    LED Amare │   D6  ──┤220Ω├── (+) │
    LED Verm  │   D7  ──┤220Ω├── (+) │
              │                      │
              │   5V  ──── VCC comum │
              │   GND ──── GND comum │
              └──────────────────────┘
                      │ USB │
                      └─────┘
                 Raspberry Pi / PC
