// =======================================================
// ESTACIONAMENTO INTELIGENTE • JAVASCRIPT EM PORTUGUÊS
// Versão Compacta / Bancada (Escala Máxima: 80 cm)
// =======================================================

let somLigado = false;
let contextoAudio = null;
let temporizadorBipe = null;
let intervaloAtual = null;
let temporizadorSimulacao = null;

// Emite um bipe sonoro sintetizado pelo navegador
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
    console.log("Aguardando interação de áudio:", erro);
  }
}

// Controla o intervalo e o ritmo dos bipes conforme a distância medida (Escala máx 80 cm)
function controlarRitmoBipes(distanciaCentimetros) {
  if (!somLigado || distanciaCentimetros == null || distanciaCentimetros <= 0 || distanciaCentimetros > 80) {
    if (temporizadorBipe) clearInterval(temporizadorBipe);
    temporizadorBipe = null;
    intervaloAtual = null;
    return;
  }

  let tempoIntervalo = distanciaCentimetros < 8 ? 90 : (distanciaCentimetros < 20 ? 200 : (distanciaCentimetros <= 50 ? 450 : 850));
  let frequenciaSom = distanciaCentimetros < 8 ? 2400 : (distanciaCentimetros < 20 ? 2200 : (distanciaCentimetros <= 50 ? 1900 : 1600));

  if (intervaloAtual === tempoIntervalo && temporizadorBipe) return;

  if (temporizadorBipe) clearInterval(temporizadorBipe);
  intervaloAtual = tempoIntervalo;
  temporizadorBipe = setInterval(() => emitirBipe(frequenciaSom), tempoIntervalo);
}

// Atualiza todas as informações da tela com os dados mais recentes da API
function atualizarPainel() {
  // 1. Busca os dados ao vivo da vaga
  fetch('/api/vaga/status')
    .then(resposta => {
      if (!resposta.ok) throw new Error('Status ' + resposta.status);
      return resposta.json();
    })
    .then(dadosRecebidos => {
      const distancia = dadosRecebidos.distancia_cm ?? 0;
      const nivel = dadosRecebidos.nivel_alerta || 'Atenção';
      const corAlerta = dadosRecebidos.cor || '#eab308';

      // Atualiza textos principais
      const elDistancia = document.getElementById('distanciaValor');
      if (elDistancia) {
        elDistancia.textContent = distancia;
        elDistancia.style.color = corAlerta;
      }
      const elNivel = document.getElementById('distanciaNivel');
      if (elNivel) {
        elNivel.textContent = 'Nível de ' + nivel.toLowerCase();
        elNivel.style.color = corAlerta;
      }
      const elSensor = document.getElementById('sensorStatus');
      if (elSensor) elSensor.textContent = dadosRecebidos.sensor_status;

      const elAlerta = document.getElementById('alertaTexto');
      if (elAlerta) elAlerta.textContent = dadosRecebidos.descricao_alerta;

      // Atualiza a barra visual de proximidade (proporcional a 80 cm)
      const barraProximidade = document.getElementById('barraPreenchimento');
      if (barraProximidade) {
        const percentual = Math.max(5, Math.min(100, ((80 - distancia) / 80) * 100));
        barraProximidade.style.width = percentual + '%';
        barraProximidade.style.backgroundColor = corAlerta;
      }

      // Atualiza os LEDs virtuais
      ['ledVerde', 'ledAmarelo', 'ledVermelho'].forEach(idLed => {
        const led = document.getElementById(idLed);
        if (led) led.className = 'led-bolinha';
      });
      if (dadosRecebidos.led === 'Verde') document.getElementById('ledVerde')?.classList.add('led-verde-ativo');
      if (dadosRecebidos.led === 'Amarelo') document.getElementById('ledAmarelo')?.classList.add('led-amarelo-ativo');
      if (dadosRecebidos.led === 'Vermelho') document.getElementById('ledVermelho')?.classList.add('led-vermelho-ativo');

      // Atualiza a posição do carrinho na vaga (escala de 80 cm até 5 cm)
      const elCarro = document.getElementById('carroVirtual');
      if (elCarro) {
        const posicaoCarro = Math.max(10, Math.min(78, 78 - ((distancia - 5) / 75) * 65));
        elCarro.style.left = posicaoCarro + '%';
      }

      // Atualiza o ritmo dos bipes sonoros
      controlarRitmoBipes(distancia);
    })
    .catch(() => {});

  // 2. Busca o histórico de medições para preencher a tabela
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

      tabelaCorpo.innerHTML = dadosHistorico.historico.map(registro => {
        const classeTag = registro.nivel_alerta === 'Longe' ? 'tag-verde' : (registro.nivel_alerta === 'Muito Perto' ? 'tag-vermelho' : 'tag-amarelo');
        const horario = registro.data_hora ? (registro.data_hora.includes(' ') ? registro.data_hora.split(' ')[1] : registro.data_hora) : '--:--';
        return `<tr><td>${horario}</td><td><strong>${registro.distancia_cm} cm</strong></td><td><span class="${classeTag}">${registro.nivel_alerta}</span></td><td>${registro.descricao_alerta}</td></tr>`;
      }).join('');
    })
    .catch(() => {});
}

// Envia uma nova leitura manual para a API
function enviarLeituraManual(distanciaCentimetros) {
  fetch('/api/leituras', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vaga_codigo: 'VAGA-01', distancia_cm: parseFloat(distanciaCentimetros) })
  }).then(atualizarPainel).catch(() => {});
}

// Envia comando para os atuadores remotos (Buzzer)
function enviarComandoAtuador(atuador, acao) {
  fetch('/api/atuadores/comando', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ atuador: atuador, acao: acao })
  }).then(atualizarPainel).catch(() => {});
}

// Executa simulações de manobra em passos sucessivos
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

// Configuração dos eventos quando a página é carregada
window.addEventListener('DOMContentLoaded', () => {
  const controleDeslizante = document.getElementById('sliderDistancia');
  if (controleDeslizante) {
    controleDeslizante.oninput = () => {
      const sliderTxt = document.getElementById('sliderTexto');
      if (sliderTxt) sliderTxt.textContent = controleDeslizante.value + ' cm';
    };
  }

  // Botões de teste e simulação (Escala de 80 cm)
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

  // Controle remoto do Buzzer
  document.getElementById('btnBuzzerRemoto')?.addEventListener('click', () => {
    enviarComandoAtuador('buzzer', 'TESTE');
    emitirBipe(2000, 0.4);
  });

  // Botão para ligar e desligar o som do navegador
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

  // Atualização inicial e periódica a cada 350 milissegundos
  atualizarPainel();
  setInterval(atualizarPainel, 350);
});
