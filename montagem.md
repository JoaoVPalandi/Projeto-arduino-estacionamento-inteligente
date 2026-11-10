🔧 Guia de Montagem do Arduino — Estacionamento Inteligente IoT (Versão Bancada Máx 80 cm)

Projeto Integrador SENAI — João Pradela, João Palandi e Pedro Cesar

📦 Lista de Materiais
Qtd	Componente	Observação
1	Arduino Uno R3	Placa principal
1	Protoboard (400 furos)	Para montar o circuito sem solda
1	Sensor Ultrassônico HC-SR04	Calibrado para até 80 cm
1	Buzzer Ativo/Passivo 5V	Alarme sonoro progressivo
1	LED Verde (5mm)	Zona segura (> 50 cm)
1	LED Amarelo (5mm)	Zona de atenção (20–50 cm)
1	LED Vermelho (5mm)	Zona crítica (< 20 cm)
3	Resistor 220Ω (vermelho-vermelho-marrom)	Um para cada LED
~12	Jumpers macho-macho	Fios coloridos para conexões
1	Cabo USB Tipo A/B	Conecta o Arduino ao PC ou Raspberry Pi

📌 Tabela de Pinagem
Componente	Pino do Componente	Pino do Arduino
Sensor HC-SR04	VCC	5V
Sensor HC-SR04	Trig (Gatilho)	Pino Digital 9
Sensor HC-SR04	Echo (Retorno)	Pino Digital 10
Sensor HC-SR04	GND	GND
Buzzer	Positivo (+)	Pino Digital 8
Buzzer	Negativo (−)	GND
LED Verde	Anodo (+) perna longa	Pino Digital 5 (resistor 220Ω)
LED Verde	Catodo (−) perna curta	GND
LED Amarelo	Anodo (+) perna longa	Pino Digital 6 (resistor 220Ω)
LED Amarelo	Catodo (−) perna curta	GND
LED Vermelho	Anodo (+) perna longa	Pino Digital 7 (resistor 220Ω)
LED Vermelho	Catodo (−) perna curta	GND

🪛 Passo a Passo Rápido

Passo 1 — Alimentação
- 5V do Arduino ➔ trilha vermelha (+) da protoboard.
- GND do Arduino ➔ trilha azul (−) da protoboard.

Passo 2 — Sensor Ultrassônico HC-SR04
- VCC ➔ Trilha vermelha (+ 5V)
- Trig ➔ Pino Digital 9
- Echo ➔ Pino Digital 10
- GND ➔ Trilha azul (GND)

Passo 3 — 3 LEDs com resistores de 220Ω
- LED Verde: Perna longa (+) ➔ Resistor 220Ω ➔ Pino Digital 5 | Perna curta (-) ➔ GND
- LED Amarelo: Perna longa (+) ➔ Resistor 220Ω ➔ Pino Digital 6 | Perna curta (-) ➔ GND
- LED Vermelho: Perna longa (+) ➔ Resistor 220Ω ➔ Pino Digital 7 | Perna curta (-) ➔ GND

Passo 4 — Buzzer Sonoro
- Perna longa ou (+) ➔ Pino Digital 8
- Perna curta ou (-) ➔ GND

Passo 5 — Teste de Bancada (Escala 80 cm)
Ao aproximar a mão do sensor:
- > 80 cm: LEDs apagados e silêncio.
- 50 a 80 cm: LED Verde acende, bipes lentos.
- 20 a 50 cm: LED Amarelo acende, bipes moderados.
- 8 a 20 cm: LED Vermelho acende, bipes rápidos.
- < 8 cm: LED Vermelho acende, bipe contínuo (parada emergencial).

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
