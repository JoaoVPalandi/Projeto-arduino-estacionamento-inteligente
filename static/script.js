// ==============================================================================
// PROJETO INTEGRADOR IoT - SENAI "CONDE JOSÉ VICENTE DE AZEVEDO"
// Estacionamento Inteligente • Script do Frontend (JavaScript)
// ==============================================================================
//
// COMO O FRONTEND SE CONECTA AO BACKEND?
// ------------------------------------------------------------------------------
// 1. O navegador carrega o HTML/CSS/JS a partir do servidor FastAPI (`GET /`).
// 2. A comunicação contínua acontece via requisições HTTP assíncronas usando a
//    função nativa `fetch()` do JavaScript.
// 3. A cada 350ms, a função `atualizarPainel()` chama o endpoint:
//       GET /api/vaga/status
//    O backend responde com um JSON contendo a distância atual, cor, LED e alerta.
// 4. O JavaScript processa esse JSON e atualiza os elementos do DOM (HTML) sem
//    recarregar a página (comportamento Single Page Application - SPA).
// 5. Ao clicar no botão "Testar Buzzer" ou mover o slider, o JS envia:
//       POST /api/atuadores/comando  ou  POST /api/leituras
// ==============================================================================

// Variáveis globais de controle de áudio e temporizadores
let somLigado = false;
let contextoAudio = null;
let temporizadorBipe = null;
let intervaloAtual = null;
let temporizadorSimulacao = null;

// ==============================================================================
// BLOCO 1: SÍNTESE DE ÁUDIO NO NAVEGADOR (Web Audio API)
// ==============================================================================
// Gera um som senoidal (bipe) no próprio alto-falante do computador/celular,
// sincronizado com o ritmo do buzzer físico do Arduino.
function emitirBipe(frequencia, duracao = 0.08) {
  if (!somLigado) return;

  try {
    if (!contextoAudio) {
      contextoAudio = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (contextoAudio.state === 'suspended') {
      contextoAudio.resume();
    }

    const oscilador = contextoAudio.createOscillator();
    const controleVolume = contextoAudio.createGain();

    oscilador.frequency.value = frequencia;
    controleVolume.gain.value = 0.08;

    oscilador.connect(controleVolume);
    controleVolume.connect(contextoAudio.destination);

    oscilador.start();
    oscilador.stop(contextoAudio.currentTime + duracao);
  } catch (erro) {
    console.log("Aguardando interação do usuário para áudio:", erro);
  }
}

// Controla o intervalo de repetição dos bipes baseado na proximidade (< 80 cm)
function controlarRitmoBipes(distanciaCentimetros) {
  if (!somLigado || distanciaCentimetros == null || distanciaCentimetros <= 0 || distanciaCentimetros > 80) {
    if (temporizadorBipe) clearInterval(temporizadorBipe);
    temporizadorBipe = null;
    intervaloAtual = null;
    return;
  }

  // Define a velocidade do bipe: quanto mais perto (< 8 cm), mais rápido
  let tempoIntervalo = distanciaCentimetros < 8 ? 90 : (distanciaCentimetros < 20 ? 200 : (distanciaCentimetros <= 50 ? 450 : 850));
  let frequenciaSom = distanciaCentimetros < 8 ? 2400 : (distanciaCentimetros < 20 ? 2200 : (distanciaCentimetros <= 50 ? 1900 : 1600));

  if (intervaloAtual === tempoIntervalo && temporizadorBipe) return;

  if (temporizadorBipe) clearInterval(temporizadorBipe);
  intervaloAtual = tempoIntervalo;
  temporizadorBipe = setInterval(() => emitirBipe(frequenciaSom), tempoIntervalo);
}

// ==============================================================================
// BLOCO 2: CONEXÃO COM O BACKEND (Polling GET /api/vaga/status)
// ==============================================================================
// Esta é a função principal de integração: ela busca os dados no FastAPI
// e atualiza dinamicamente os valores visuais na tela (HTML).
function atualizarPainel() {
  // 1. REQUISIÇÃO HTTP GET: Pergunta ao servidor o estado ao vivo da vaga
  fetch('/api/vaga/status')
    .then(resposta => {
      if (!resposta.ok) throw new Error('Status HTTP ' + resposta.status);
      return resposta.json(); // Converte o texto JSON em objeto JavaScript
    })
    .then(dadosRecebidos => {
      // Extrai os campos devolvidos pelo backend
      const distancia = dadosRecebidos.distancia_cm ?? 0;
      const nivel = dadosRecebidos.nivel_alerta || 'Atenção';
      const corAlerta = dadosRecebidos.cor || '#eab308';

      // Atualiza o texto da distância em cm e a cor
      const elDistancia = document.getElementById('distanciaValor');
      if (elDistancia) {
        elDistancia.textContent = distancia;
        elDistancia.style.color = corAlerta;
      }

      // Atualiza a descrição do nível ("Nível de longe", "Nível de atenção", etc.)
      const elNivel = document.getElementById('distanciaNivel');
      if (elNivel) {
        elNivel.textContent = 'Nível de ' + nivel.toLowerCase();
        elNivel.style.color = corAlerta;
      }

      // Atualiza status do sensor e do alarme sonoro
      const elSensor = document.getElementById('sensorStatus');
      if (elSensor) elSensor.textContent = dadosRecebidos.sensor_status;

      const elAlerta = document.getElementById('alertaTexto');
      if (elAlerta) elAlerta.textContent = dadosRecebidos.descricao_alerta;

      // Atualiza a largura e cor da barra de proximidade proporcional a 80 cm
      const barraProximidade = document.getElementById('barraPreenchimento');
      if (barraProximidade) {
        const percentual = Math.max(5, Math.min(100, ((80 - distancia) / 80) * 100));
        barraProximidade.style.width = percentual + '%';
        barraProximidade.style.backgroundColor = corAlerta;
      }

      // Atualiza os LEDs virtuais da interface (Verde, Amarelo ou Vermelho)
      ['ledVerde', 'ledAmarelo', 'ledVermelho'].forEach(idLed => {
        const led = document.getElementById(idLed);
        if (led) led.className = 'led-bolinha';
      });
      if (dadosRecebidos.led === 'Verde') document.getElementById('ledVerde')?.classList.add('led-verde-ativo');
      if (dadosRecebidos.led === 'Amarelo') document.getElementById('ledAmarelo')?.classList.add('led-amarelo-ativo');
      if (dadosRecebidos.led === 'Vermelho') document.getElementById('ledVermelho')?.classList.add('led-vermelho-ativo');

      // Movimenta o carrinho animado pela vaga conforme a distância medida
      const elCarro = document.getElementById('carroVirtual');
      if (elCarro) {
        const posicaoCarro = Math.max(10, Math.min(78, 78 - ((distancia - 5) / 75) * 65));
        elCarro.style.left = posicaoCarro + '%';
      }

      // Mantém o ritmo sonoro do navegador sincronizado
      controlarRitmoBipes(distancia);
    })
    .catch(() => {
      // Ignora falhas momentâneas se o servidor estiver ocupado
    });

  // 2. REQUISIÇÃO HTTP GET: Busca as últimas 8 leituras gravadas no SQLite
  fetch('/api/leituras/historico')
    .then(resposta => {
      if (!resposta.ok) throw new Error('Status ' + resposta.status);
      return resposta.json();
    })
    .then(dadosHistorico => {
      const tabelaCorpo = document.getElementById('tabelaCorpo');
      if (!tabelaCorpo) return;

      if (!dadosHistorico.historico?.length) {
        tabelaCorpo.innerHTML = '<tr><td colspan="4">Nenhuma leitura cadastrada</td></tr>';
        return;
      }

      // Monta as linhas <tr> da tabela dinamicamente com os dados do banco
      tabelaCorpo.innerHTML = dadosHistorico.historico.map(registro => {
        const classeTag = registro.nivel_alerta === 'Longe' ? 'tag-verde' : (registro.nivel_alerta === 'Muito Perto' ? 'tag-vermelho' : 'tag-amarelo');
        const horario = registro.data_hora ? (registro.data_hora.includes(' ') ? registro.data_hora.split(' ')[1] : registro.data_hora) : '--:--';
        return `<tr><td>${horario}</td><td><strong>${registro.distancia_cm} cm</strong></td><td><span class="${classeTag}">${registro.nivel_alerta}</span></td><td>${registro.descricao_alerta}</td></tr>`;
      }).join('');
    })
    .catch(() => {});
}

// ==============================================================================
// BLOCO 3: ENVIAR DADOS DO FRONTEND PARA O BACKEND (POST HTTP)
// ==============================================================================

// Envia uma nova medição manual (ex: quando o usuário mexe no slider)
function enviarLeituraManual(distanciaCentimetros) {
  fetch('/api/leituras', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vaga_codigo: 'VAGA-01', distancia_cm: parseFloat(distanciaCentimetros) })
  }).then(atualizarPainel).catch(() => {});
}

// Envia comando para acionar o Buzzer físico através do backend e porta serial
function enviarComandoAtuador(atuador, acao) {
  fetch('/api/atuadores/comando', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ atuador: atuador, acao: acao })
  }).then(atualizarPainel).catch(() => {});
}

// Simula a animação do carro estacionando passo a passo
function executarSimulacao(passosDistancia) {
  if (temporizadorSimulacao) clearInterval(temporizadorSimulacao);
  let indicePasso = 0;

  temporizadorSimulacao = setInterval(() => {
    if (indicePasso >= passosDistancia.length) {
      clearInterval(temporizadorSimulacao);
      temporizadorSimulacao = null;
      return;
    }
    const distanciaAtual = passosDistancia[indicePasso++];
    const slider = document.getElementById('sliderDistancia');
    const sliderTxt = document.getElementById('sliderTexto');
    if (slider) slider.value = distanciaAtual;
    if (sliderTxt) sliderTxt.textContent = distanciaAtual + ' cm';
    enviarLeituraManual(distanciaAtual);
  }, 600);
}

// ==============================================================================
// BLOCO 4: INICIALIZAÇÃO E EVENTOS DO NAVEGADOR
// ==============================================================================
window.addEventListener('DOMContentLoaded', () => {
  const controleDeslizante = document.getElementById('sliderDistancia');
  if (controleDeslizante) {
    controleDeslizante.oninput = () => {
      const sliderTxt = document.getElementById('sliderTexto');
      if (sliderTxt) sliderTxt.textContent = controleDeslizante.value + ' cm';
    };
  }

  // Botões de teste e manobra
  document.getElementById('btnAplicarSlider')?.addEventListener('click', () => {
    if (controleDeslizante) enviarLeituraManual(controleDeslizante.value);
  });
  document.getElementById('btn35')?.addEventListener('click', () => {
    if (controleDeslizante) {
      controleDeslizante.value = 35;
      controleDeslizante.oninput();
    }
    enviarLeituraManual(35);
  });
  document.getElementById('btnEntrar')?.addEventListener('click', () => executarSimulacao([75, 55, 40, 25, 15, 6]));
  document.getElementById('btnSair')?.addEventListener('click', () => executarSimulacao([6, 18, 32, 48, 65, 78]));

  // Disparo do comando remoto do Buzzer
  document.getElementById('btnBuzzerRemoto')?.addEventListener('click', () => {
    enviarComandoAtuador('buzzer', 'TESTE');
    emitirBipe(2000, 0.4);
  });

  // Botão de ligar/desligar o áudio do navegador
  const botaoAlarmeSonoro = document.getElementById('btnAudio');
  if (botaoAlarmeSonoro) {
    botaoAlarmeSonoro.onclick = () => {
      somLigado = !somLigado;
      botaoAlarmeSonoro.innerHTML = somLigado ? '🔊 Som de Bipes: <strong>Ligado</strong>' : '🔇 Som de Bipes: <strong>Desligado</strong>';
      botaoAlarmeSonoro.classList.toggle('ativo', somLigado);
      if (!somLigado && temporizadorBipe) clearInterval(temporizadorBipe);
      atualizarPainel();
    };
  }

  // Loop de sincronização periódica:
  // Executa uma vez no início e depois a cada 350 milissegundos continuamente
  atualizarPainel();
  setInterval(atualizarPainel, 350);
});
