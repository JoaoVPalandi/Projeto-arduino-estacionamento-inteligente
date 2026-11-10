# Estacionamento Inteligente • Vaga IoT (ITCOI)

> **PROJETO INTEGRADOR IoT • SENAI "CONDE JOSÉ VICENTE DE AZEVEDO"**  
> **Curso Técnico em Desenvolvimento de Sistemas | Módulo Específico I**  
> **Equipe:** João Pradela, João Palandi e Pedro Cesar  
> **Versão de Bancada / Maquete:** Alcance calibrado para até **80 cm**

---

## 1. Escopo e Matriz de Requisitos (Etapa 1)
O projeto resolve a dificuldade de visibilidade ao manobrar em vagas apertadas através de medição física contínua de distância com avisos progressivos (bipes e LEDs) e telemetria transmitida em rede local via HTTP/REST para um painel web com monitoramento e comando de teste remoto.

* **Requisitos Funcionais (RF):**
  - **RF01:** Medir distância em centímetros (2 a 80 cm) via sensor ultrassônico HC-SR04 calibrado para bancada/maquete.
  - **RF02:** Emitir bipes no buzzer com frequência e ritmo proporcionais à proximidade.
  - **RF03:** Sinalizar status com 3 LEDs (Verde >50cm, Amarelo 20-50cm, Vermelho <20cm).
  - **RF04:** Enviar telemetria via Serial USB (JSON: `{"distancia_cm": 35.0}`).
  - **RF05:** Dashboard Web em tempo real exibindo centímetros, nível, LEDs virtuais e histórico.
  - **RF06:** Emitir comando remoto de teste ao alarme sonoro (buzzer) via Serial.
* **Requisitos Não Funcionais (RNF):**
  - **RNF01:** Tempo de resposta físico ultrarrápido (timeout reduzido para 6000µs, sem delays bloqueantes).
  - **RNF02:** Operar de forma autônoma via Hotspot Wi-Fi ou rede local do Raspberry Pi 3B.
  - **RNF03:** Armazenar leituras e logs de atuadores no banco SQLite (`estacionamento.db`).
  - **RNF04:** Interface responsiva atualizada via Fetch API assíncrona a cada 350ms.

---

## 2. Pinagem e Montagem do Circuito

| Componente | Terminal | Pino Arduino | Observação / Função |
| :--- | :--- | :--- | :--- |
| **HC-SR04** | VCC / GND | **5V / GND** | Alimentação positiva e terra comum |
| **HC-SR04** | TRIG | **Digital 9** | Disparo do pulso ultrassônico (10µs) |
| **HC-SR04** | ECHO | **Digital 10** | Retorno do eco (leitura dos cm, timeout 6ms) |
| **Buzzer** | (+) / (-) | **Digital 8 / GND** | Alertas sonoros progressivos |
| **LED Verde** | Ânodo (+) | **Digital 5** | Resistor 220 $\Omega$ / Longe (50 a 80 cm) |
| **LED Amarelo**| Ânodo (+) | **Digital 6** | Resistor 220 $\Omega$ / Atenção (20 a 50 cm) |
| **LED Vermelho**| Ânodo (+) | **Digital 7** | Resistor 220 $\Omega$ / Muito Perto (< 20 cm) |

---

## 3. Escala das Zonas de Proximidade (Máximo 80 cm)

| Distância | LED Físico | Alerta na Tela | Ritmo do Buzzer | Significado |
| :--- | :--- | :--- | :--- | :--- |
| **> 80 cm** | ⚪ Desligados | Sem veículo | Silêncio absoluto | Objeto fora da vaga |
| **50 a 80 cm** | 🟢 **LED Verde** | **Longe** | Bipes lentos (850ms) | Entrada segura na vaga |
| **20 a 50 cm** | 🟡 **LED Amarelo** | **Atenção** | Bipes moderados (450ms) | Aproximação intermediária |
| **8 a 20 cm** | 🔴 **LED Vermelho** | **Muito Perto** | Bipes rápidos (200ms) | Perto do obstáculo |
| **< 8 cm** | 🔴 **LED Vermelho** | **Crítico / Parada** | Bipe contínuo (90ms) | Parada imediata / risco de colisão |

---

## 4. Arquitetura de Comunicação

```text
[ Sensor HC-SR04 ]
       │ (2 a 80 cm)
       ▼
[ Arduino Uno R3 ] ──(Controle Local)──► [ 3 LEDs + Buzzer ]
       │
       ▼ (Serial USB / 9600 bps em JSON: {"distancia_cm": 35.0})
[ Raspberry Pi 3B / PC ]
       │
       ├──► FastAPI (`app.py` porta 5000): Processa a serial e salva no SQLite
       └──► Painel Web HTML/JS: Atualiza carrinho, LEDs e bipes em tempo real
```

---

## 5. Como Iniciar e Testar

### No seu PC (Windows):
1. **Iniciar o servidor web:**
   ```powershell
   python app.py
   ```
   *(Abre automaticamente no navegador em `http://127.0.0.1:5000`)*.

2. **Testar com o simulador (sem a placa física):**
   ```powershell
   python simulador.py
   ```

### No Raspberry Pi (com Arduino conectado no USB):
```bash
cd ~/estacionamento
python3 app.py
```
Acesse de qualquer celular ou PC na mesma rede: `http://<IP_DO_RASPBERRY>:5000`
