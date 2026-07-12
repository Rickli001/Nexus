/* ============================================================
   J.A.R.V.I.S. Mobile — PWA front-end
   Wake word listening, English speech, chat, content engine UI
   ============================================================ */

// Backend URL. Override without editing code:
//   localStorage.setItem('jarvis_api', 'https://my-server.example.com')
const API_BASE = localStorage.getItem('jarvis_api') || 'http://localhost:8741';

// ---------- DOM ----------
const $ = (id) => document.getElementById(id);
const standbyScreen = $('standby');
const jarvisScreen = $('jarvis');
const micStatus = $('mic-status');
const caption = $('jarvis-caption');
const core = $('reactor-core');
const log = $('log');
const textInput = $('text-input');

// ---------- Wake word patterns ----------
const WAKE_PATTERNS = [
  /\b(hello|hey|hi|ok|okay|yo|good\s*(morning|afternoon|evening))[,\s]*jarvis\b/i,
  /\bjarvis[,\s]*(are\s*you\s*(there|awake)|wake\s*up|hello|hi)\b/i,
  /\b(wake\s*up|time\s*to\s*wake\s*up)[,\s]*jarvis\b/i,
  /\bcome\s*on[,\s]*(time\s*to\s*wake\s*up[,\s]*)?jarvis\b/i,
];
const isWakePhrase = (t) => WAKE_PATTERNS.some((re) => re.test(t));

const GREETINGS = [
  'At your service, sir.',
  'Good day, sir. All systems are online.',
  'For you, sir, always.',
  'Hello, sir. How may I assist you today?',
];

// ---------- Speech synthesis (British male preferred) ----------
let jarvisVoice = null;

function pickVoice() {
  const voices = speechSynthesis.getVoices();
  if (!voices.length) return;
  const male = /daniel|george|arthur|james|brian|male/i;
  jarvisVoice =
    voices.find((v) => v.lang.startsWith('en-GB') && male.test(v.name)) ||
    voices.find((v) => v.lang.startsWith('en-GB')) ||
    voices.find((v) => v.lang.startsWith('en') && male.test(v.name)) ||
    voices.find((v) => v.lang.startsWith('en')) ||
    null;
}
speechSynthesis.onvoiceschanged = pickVoice;
pickVoice();

function speak(text, onDone) {
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  if (jarvisVoice) u.voice = jarvisVoice;
  u.lang = jarvisVoice ? jarvisVoice.lang : 'en-GB';
  u.rate = 1.0;
  u.pitch = 0.85; // slightly lower, calm and composed
  u.onstart = () => core.classList.add('talking');
  u.onend = () => {
    core.classList.remove('talking');
    if (onDone) onDone();
  };
  caption.textContent = text;
  speechSynthesis.speak(u);
}

// ---------- Speech recognition ----------
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let recMode = 'off'; // 'wake' | 'command' | 'off'
let awake = false;

function startRecognition(mode) {
  if (!SR) {
    micStatus.textContent = 'speech recognition not supported in this browser';
    return;
  }
  stopRecognition();
  recognition = new SR();
  recMode = mode;
  recognition.lang = 'en-US';
  recognition.continuous = mode === 'wake';
  recognition.interimResults = mode === 'wake';

  recognition.onresult = (e) => {
    const transcript = Array.from(e.results)
      .map((r) => r[0].transcript)
      .join(' ')
      .toLowerCase();
    if (recMode === 'wake') {
      if (isWakePhrase(transcript)) wakeUp();
    } else {
      const final = e.results[e.results.length - 1];
      if (final.isFinal) handleUserMessage(final[0].transcript.trim());
    }
  };

  recognition.onend = () => {
    $('btn-listen').classList.remove('recording');
    // Keep the wake-word listener alive while on standby
    if (recMode === 'wake' && !awake) {
      try { recognition.start(); } catch (_) { /* already restarting */ }
    } else {
      recMode = 'off';
    }
  };

  recognition.onerror = (e) => {
    if (e.error === 'not-allowed') {
      micStatus.textContent = 'microphone permission denied — tap to wake manually';
      recMode = 'off';
    }
  };

  try {
    recognition.start();
    micStatus.textContent = mode === 'wake' ? 'listening for wake word…' : 'listening…';
  } catch (_) { /* start() called while active */ }
}

function stopRecognition() {
  if (recognition) {
    recMode = 'off';
    try { recognition.onend = null; recognition.stop(); } catch (_) {}
    recognition = null;
  }
}

// ---------- Wake / sleep ----------
function wakeUp() {
  if (awake) return;
  awake = true;
  stopRecognition();
  standbyScreen.classList.remove('active');
  jarvisScreen.classList.add('active');
  speak(GREETINGS[Math.floor(Math.random() * GREETINGS.length)]);
  refreshStatus();
  refreshChannel();
  statusTimer = setInterval(refreshStatus, 10000);
}

function goToSleep() {
  awake = false;
  clearInterval(statusTimer);
  speechSynthesis.cancel();
  core.classList.remove('talking');
  jarvisScreen.classList.remove('active');
  standbyScreen.classList.add('active');
  startRecognition('wake');
}

// ---------- Chat ----------
function addMsg(text, who) {
  const div = document.createElement('div');
  div.className = `msg ${who}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function handleUserMessage(message) {
  if (!message) return;
  addMsg(message, 'user');
  caption.textContent = '…';
  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    const reply = data.reply || data.detail || 'I seem to be having trouble reaching my servers, sir.';
    addMsg(reply, 'jarvis');
    speak(reply);
    refreshStatus(); // voice commands may have changed mode/pipeline
  } catch (_) {
    const reply = 'I cannot reach the backend at the moment, sir. Do check the server address.';
    addMsg(reply, 'jarvis');
    speak(reply);
  }
}

// ---------- Content engine panel ----------
let statusTimer = null;
let currentMode = 'auto';
let reviewMode = false;
let pendingShownTitle = null;

async function api(path, opts) {
  const res = await fetch(`${API_BASE}${path}`, opts);
  return res.json();
}

function renderMode(mode) {
  currentMode = mode;
  $('mode-auto').classList.toggle('active', mode === 'auto');
  $('mode-manual').classList.toggle('active', mode === 'manual');
  $('style-picker').classList.toggle('hidden', mode !== 'manual');
}

async function setMode(mode) {
  renderMode(mode);
  try {
    await api('/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, style: $('style-select').value }),
    });
  } catch (_) {}
}

function renderReview(s) {
  reviewMode = !!s.review_mode;
  const toggle = $('review-toggle');
  toggle.textContent = reviewMode ? 'ON' : 'OFF';
  toggle.classList.toggle('active', reviewMode);

  const box = $('review-box');
  if (s.pending_video) {
    box.classList.remove('hidden');
    $('review-title').textContent = s.pending_video.title;
    if (pendingShownTitle !== s.pending_video.title) {
      pendingShownTitle = s.pending_video.title;
      $('review-video').src = `${API_BASE}/pending/video?t=${Date.now()}`;
      speak('Sir, a new video is ready for your review.');
    }
  } else {
    box.classList.add('hidden');
    if (pendingShownTitle) {
      pendingShownTitle = null;
      $('review-video').removeAttribute('src');
    }
  }
}

async function refreshStatus() {
  try {
    const s = await api('/status');
    renderMode(s.mode);
    renderReview(s);
    if (s.style && s.mode === 'manual') $('style-select').value = s.style;
    $('ps-state').textContent = s.pipeline_stage || 'idle';
    $('ps-next').textContent = s.next_post_at
      ? new Date(s.next_post_at).toLocaleTimeString()
      : (s.mode === 'manual' ? 'manual only' : '—');
    $('ps-last').textContent = s.last_video ? s.last_video.title : 'none yet';
  } catch (_) {
    $('ps-state').textContent = 'backend offline';
  }
}

async function setReview(on) {
  try {
    const s = await api('/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: currentMode, review: on }),
    });
    renderReview(s);
  } catch (_) {}
}

async function reviewAction(action) {
  try {
    const r = await api('/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    if (r.posted) {
      speak('Very good, sir. The video has been posted.');
      addMsg(`Posted: ${r.video.title} — ${r.video.url}`, 'jarvis');
    } else if (r.discarded) {
      speak('As you wish, sir. The video has been discarded.');
    } else if (r.detail) {
      addMsg(r.detail, 'jarvis');
    }
  } catch (_) {
    addMsg('The review action failed, sir.', 'jarvis');
  }
  refreshStatus();
}

// ---------- Daily briefing ----------
async function dailyBriefing() {
  caption.textContent = 'Compiling your briefing, sir…';
  try {
    const r = await api('/briefing');
    const text = r.briefing || r.detail || 'The briefing is unavailable, sir.';
    addMsg(text, 'jarvis');
    speak(text);
  } catch (_) {
    speak('I could not compile the briefing, sir.');
  }
}

// ---------- Code mode (Claude) ----------
async function runCode() {
  const prompt = $('code-input').value.trim();
  if (!prompt) return;
  const out = $('code-output');
  out.classList.remove('hidden');
  out.textContent = 'Working on it, sir…';
  try {
    const r = await api('/code', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
    out.textContent = r.reply || r.detail || 'No response from the coding engine, sir.';
    if (r.reply) speak('The code is ready, sir.');
  } catch (_) {
    out.textContent = 'The coding engine did not respond, sir.';
  }
}

async function refreshChannel() {
  try {
    const c = await api('/channel');
    $('cs-subs').textContent = c.subscribers ?? '—';
    $('cs-views').textContent = c.views ?? '—';
    $('cs-videos').textContent = c.videos ?? '—';
  } catch (_) {}
}

async function generateNow() {
  const style = $('style-select').value;
  speak(`Very well, sir. Producing a ${style.replace('_', ' ')} video right away.`);
  try {
    const r = await api('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ style }),
    });
    if (r.detail) addMsg(r.detail, 'jarvis');
  } catch (_) {
    addMsg('The content engine did not respond, sir.', 'jarvis');
  }
  refreshStatus();
}

// ---------- Event wiring ----------
$('btn-manual-wake').addEventListener('click', wakeUp);
$('btn-sleep').addEventListener('click', goToSleep);
$('mode-auto').addEventListener('click', () => setMode('auto'));
$('mode-manual').addEventListener('click', () => setMode('manual'));
$('btn-generate-now').addEventListener('click', generateNow);
$('review-toggle').addEventListener('click', () => setReview(!reviewMode));
$('btn-approve').addEventListener('click', () => reviewAction('approve'));
$('btn-discard').addEventListener('click', () => reviewAction('discard'));
$('btn-briefing').addEventListener('click', dailyBriefing);
$('btn-code').addEventListener('click', () => {
  const panel = $('code-panel');
  panel.classList.toggle('hidden');
  $('btn-code').classList.toggle('active', !panel.classList.contains('hidden'));
});
$('btn-run-code').addEventListener('click', runCode);

$('btn-send').addEventListener('click', () => {
  handleUserMessage(textInput.value.trim());
  textInput.value = '';
});
textInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    handleUserMessage(textInput.value.trim());
    textInput.value = '';
  }
});
$('btn-listen').addEventListener('click', () => {
  $('btn-listen').classList.add('recording');
  startRecognition('command');
});

// ---------- Boot ----------
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}
startRecognition('wake');
