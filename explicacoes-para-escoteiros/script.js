// ===== Explicações para Escoteiros =====

// ---------- Navegação por abas ----------
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');

function openTab(id) {
  tabButtons.forEach(function (btn) {
    btn.classList.toggle('active', btn.dataset.tab === id);
  });
  tabPanels.forEach(function (panel) {
    panel.classList.toggle('active', panel.id === id);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

tabButtons.forEach(function (btn) {
  btn.addEventListener('click', function () {
    openTab(btn.dataset.tab);
    history.replaceState(null, '', '#' + btn.dataset.tab);
  });
});

// Abre a aba indicada na URL (ex.: index.html#ajuda)
if (location.hash) {
  const alvo = location.hash.slice(1);
  if (document.getElementById(alvo)) {
    openTab(alvo);
  }
}

// ---------- Linha do tempo interativa ----------
const eventos = [
  {
    ano: '1857',
    icone: '📖',
    titulo: 'Tom Brown’s School Days',
    texto:
      'O escritor inglês Thomas Hughes publica o romance "Tom Brown’s School Days" ' +
      '(Os Tempos de Escola de Tom Brown), que mostra as maldades do valentão Flashman ' +
      'contra alunos mais novos em um internato. É um dos primeiros retratos do bullying ' +
      'escolar na literatura — prova de que o problema é muito mais antigo do que o nome.'
  },
  {
    ano: '1970',
    icone: '🔬',
    titulo: 'Começam as pesquisas de Dan Olweus',
    texto:
      'O psicólogo Dan Olweus (nascido na Suécia e radicado na Noruega) começa a primeira ' +
      'grande pesquisa científica sobre agressões sistemáticas entre estudantes. ' +
      'É dele a definição de bullying usada até hoje: agressão repetida e com ' +
      'desequilíbrio de força entre agressor e vítima.'
  },
  {
    ano: 'Final de 1982',
    icone: '🕯️',
    titulo: 'Tragédia na Noruega',
    texto:
      'Três adolescentes noruegueses tiram a própria vida depois de sofrerem intensa ' +
      'intimidação na escola. O caso choca o país e mostra ao mundo que o bullying ' +
      'não é "coisa de criança": tem consequências graves e reais.'
  },
  {
    ano: 'Set. 1983',
    icone: '📢',
    titulo: '1ª Campanha Nacional antibullying',
    texto:
      'Em resposta à tragédia, a Noruega lança a primeira campanha nacional contra o ' +
      'bullying, base do Programa Olweus de Prevenção ao Bullying. O programa reduziu ' +
      'os casos de intimidação nas escolas norueguesas em cerca de 50%.'
  },
  {
    ano: '20 abr. 1999',
    icone: '🎗️',
    titulo: 'Massacre de Columbine (EUA)',
    texto:
      'Um ataque em uma escola dos Estados Unidos choca o planeta. Os olhares do mundo ' +
      'inteiro se voltam ao estudo do bullying e à falta de segurança nos colégios, ' +
      'intensificando a prevenção ao bullying e as normas de segurança escolar.'
  },
  {
    ano: 'Anos 2000',
    icone: '💻',
    titulo: 'Nasce o cyberbullying',
    texto:
      'Com a massificação da internet — e depois das redes sociais e dos smartphones — ' +
      'o bullying ganha uma versão digital: o cyberbullying, que alcança a vítima em ' +
      'qualquer lugar, a qualquer hora.'
  },
  {
    ano: '2024',
    icone: '⚖️',
    titulo: 'Bullying vira crime no Brasil',
    texto:
      'A Lei Federal nº 14.811/2024 torna crimes a intimidação sistemática (bullying) ' +
      'e a intimidação sistemática virtual (cyberbullying) no Brasil, além de criar ' +
      'outras medidas de proteção a crianças e adolescentes.'
  }
];

const timeline = document.querySelector('.timeline');

// Só monta a linha do tempo nas páginas que têm uma
if (timeline) {

const detailIcon = document.getElementById('timeline-detail-icon');
const detailTitle = document.getElementById('timeline-detail-title');
const detailText = document.getElementById('timeline-detail-text');
const btnPrev = document.getElementById('timeline-prev');
const btnNext = document.getElementById('timeline-next');

let eventoAtual = -1;

// Cria os marcadores na linha
eventos.forEach(function (evento, i) {
  const marker = document.createElement('button');
  marker.className = 'timeline-marker';
  marker.setAttribute('role', 'tab');
  marker.setAttribute('aria-label', evento.ano + ' — ' + evento.titulo);
  marker.innerHTML =
    '<span class="dot">' + evento.icone + '</span>' +
    '<span class="year">' + evento.ano + '</span>';
  marker.addEventListener('click', function () {
    mostrarEvento(i);
  });
  timeline.appendChild(marker);
});

const markers = document.querySelectorAll('.timeline-marker');

function mostrarEvento(i) {
  eventoAtual = i;
  const evento = eventos[i];

  markers.forEach(function (m, j) {
    m.classList.toggle('active', j === i);
    m.setAttribute('aria-selected', j === i ? 'true' : 'false');
  });

  detailIcon.textContent = evento.icone;
  detailTitle.textContent = evento.ano + ' — ' + evento.titulo;
  detailText.textContent = evento.texto;

  btnPrev.disabled = i === 0;
  btnNext.disabled = i === eventos.length - 1;
}

btnPrev.addEventListener('click', function () {
  if (eventoAtual > 0) mostrarEvento(eventoAtual - 1);
});

btnNext.addEventListener('click', function () {
  if (eventoAtual < eventos.length - 1) mostrarEvento(eventoAtual + 1);
});

// Setas do teclado funcionam quando a aba da linha do tempo está aberta
document.addEventListener('keydown', function (e) {
  const abaAberta = document.getElementById('linha-do-tempo').classList.contains('active');
  if (!abaAberta) return;
  if (e.key === 'ArrowRight' && eventoAtual < eventos.length - 1) {
    mostrarEvento(eventoAtual + 1);
  } else if (e.key === 'ArrowLeft' && eventoAtual > 0) {
    mostrarEvento(eventoAtual - 1);
  }
});

// Começa mostrando o primeiro evento
mostrarEvento(0);

}
