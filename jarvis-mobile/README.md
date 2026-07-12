# J.A.R.V.I.S. Mobile

Assistente mobile no estilo J.A.R.V.I.S. + motor de conteúdo automático para YouTube.

- **Wake word por voz**: diga **"Hello, Jarvis"**, **"Come on, time to wake up, Jarvis"** (ou variantes: "Hey Jarvis", "Wake up, Jarvis", "Jarvis, are you there?"…) e ele aparece na tela e responde **em inglês**, com voz masculina britânica.
- **Chat por voz e texto** com a persona J.A.R.V.I.S. (GPT-4o) e **geração de imagens** (DALL-E 3) — as funcionalidades da versão de PC (Nexus).
- **Content Engine**: gera roteiro (GPT), cenas (DALL-E), narração em inglês (OpenAI TTS, voz "onyx") e monta o vídeo vertical (moviepy), publicando **1 vídeo a cada 2 horas** no seu canal.
- **Modo AUTO (padrão)**: o Jarvis escolhe o estilo sozinho. **Modo MANUAL**: você escolhe o estilo (Tech News, Curiosities, Motivation, Science, Top 5, Mystery) e pode disparar "Generate & Post Now".
- **Channel Monitor**: inscritos, views e nº de vídeos do canal via YouTube Data API.
- **Comandos de voz totais**: fale naturalmente — "switch to manual mode", "make a mystery video now", "status report", "how is the channel doing?" — e o Jarvis entende a intenção (function calling do GPT) e executa.
- **Daily Briefing por voz**: botão 📋 (ou peça "morning briefing") — ele fala o crescimento do canal, a performance dos últimos vídeos (views/likes) e o status do motor de conteúdo.
- **Modo revisão**: com "Review before posting" ligado, o vídeo é gerado e **espera sua aprovação**: você assiste o preview no app e toca em "Approve & Post" ou "Discard" (também funciona por voz: "approve the video").
- **Memória persistente**: o Jarvis lembra do histórico de conversas e de fatos/preferências que você contar ("remember that my name is…") entre sessões.
- **Code Mode (Claude)**: botão ⌨️ abre o modo de programação, movido pelo modelo **Claude (`claude-fable-5`)** via SDK da Anthropic — descreva o que precisa e receba código completo e funcional.
- **Análise de audiência**: botão 💬 (ou "analyze the comments") — o Jarvis lê os comentários recentes do canal, resume o sentimento, destaca o vídeo que mais gera conversa e sugere temas que a audiência pede.
- **Estilo auto-otimizado**: no modo AUTO ele não sorteia mais o estilo — analisa as views dos últimos vídeos por estilo e favorece o que performa melhor (70% aproveita o campeão, 30% explora os outros).
- **Thumbnails automáticas**: cada vídeo ganha uma thumbnail gerada por IA e enviada via API (requer canal verificado por telefone; se não estiver, é ignorado sem erro).
- **Música de fundo**: solte arquivos `.mp3` royalty-free em `server/music/` (ex.: da YouTube Audio Library) e cada vídeo sai com trilha suave sob a narração (volume via `JARVIS_MUSIC_VOLUME`, default 0.12).

## Estrutura

```
jarvis-mobile/
├── app/      # PWA — instale na tela inicial do celular (Chrome > "Adicionar à tela inicial")
└── server/   # Backend FastAPI — chat, imagens, pipeline de vídeo, scheduler, YouTube
```

## 1. Backend

### 🐳 Jeito recomendado: Docker (um comando)

```bash
cd jarvis-mobile
cp .env.example .env   # edite: JARVIS_API_KEY (senha do app) + chaves de IA
docker compose up -d --build
```

Pronto: API em `http://seu-ip:8741` **e o app já servido em `http://seu-ip:8741/app/`** (um container só). O serviço reinicia sozinho se cair (`restart: unless-stopped`) e todo o estado (memória, histórico, token do YouTube, vídeos em revisão, músicas) fica persistido em `jarvis-mobile/data/` — coloque o `client_secret.json` lá e rode a autorização do YouTube uma vez com `docker compose exec jarvis python authorize_youtube.py`.

### Manual (sem Docker)

```bash
cd jarvis-mobile/server
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
export JARVIS_API_KEY="uma-senha-forte"
uvicorn main:app --host 0.0.0.0 --port 8741
```

O `ffmpeg` precisa estar instalado no sistema (o moviepy usa ele para renderizar).

### 🔐 Segurança

Com `JARVIS_API_KEY` definida, **toda** chamada à API exige o header `X-Jarvis-Key` — sem isso, qualquer pessoa com a URL controlaria seu canal e gastaria seus créditos. Na primeira vez que o app encontrar o servidor protegido, ele pede a senha e a guarda no aparelho. Sem a variável, a API fica aberta (use só para teste local).

### Autorizar o YouTube (uma vez)

1. No [Google Cloud Console](https://console.cloud.google.com/): crie um projeto, ative a **YouTube Data API v3** e crie uma credencial OAuth do tipo **Desktop app**.
2. Baixe o JSON como `server/client_secret.json`.
3. Rode `python authorize_youtube.py` e faça login com a conta dona do canal. Isso gera o `token.json` usado pelo servidor.

### 💸 Modo grátis (custo zero)

Não quer pagar nada? Rode com `JARVIS_PROVIDER=free`:

```bash
export JARVIS_PROVIDER=free
export GEMINI_API_KEY="AIza..."   # grátis: https://aistudio.google.com/apikey (sem cartão)
uvicorn main:app --host 0.0.0.0 --port 8741
```

O que muda por baixo dos panos:

| Função | Modo pago | Modo grátis |
|---|---|---|
| Chat, roteiros, briefing | GPT-4o | **Gemini** (free tier, via endpoint compatível com OpenAI — function calling incluso) |
| Imagens das cenas | DALL-E 3 | **Pollinations.ai** (sem chave) |
| Narração dos vídeos | OpenAI TTS "onyx" | **edge-tts** voz `en-GB-RyanNeural` (britânica, gratuita) |
| Code Mode | Claude (Anthropic) | Gemini (a menos que `ANTHROPIC_API_KEY` esteja setada — aí usa Claude mesmo no modo grátis) |

Limitações honestas: o free tier do Gemini tem cota por minuto/dia (suficiente para chat + 12 roteiros/dia), e o Pollinations dá menos controle fino que o DALL-E. Para hospedar de graça: o PWA vai em Vercel/Netlify/GitHub Pages; o backend roda no seu PC ou numa VM do Oracle Cloud Free Tier.

Extras do modo grátis: `JARVIS_CHAT_MODEL` (default `gemini-2.5-flash`) e `JARVIS_EDGE_VOICE` (default `en-GB-RyanNeural`; veja opções com `edge-tts --list-voices`).

### Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `JARVIS_API_KEY` | — | senha de acesso da API (defina sempre que expor na internet) |
| `JARVIS_PROVIDER` | `paid` | `paid` (OpenAI) ou `free` (Gemini + Pollinations + edge-tts) |
| `OPENAI_API_KEY` | — | obrigatória no modo `paid` (GPT, DALL-E, TTS) |
| `GEMINI_API_KEY` | — | obrigatória no modo `free` (aistudio.google.com/apikey) |
| `ANTHROPIC_API_KEY` | — | obrigatória para o Code Mode (Claude) — crie em console.anthropic.com |
| `CLAUDE_MODEL` | `claude-fable-5` | modelo do Code Mode; com Fable 5 o fallback server-side para `claude-opus-4-8` fica ativo (se um pedido benigno for recusado pelo classificador, o Opus responde) |
| `POST_INTERVAL_HOURS` | `2` | intervalo entre posts no modo AUTO |
| `YT_PRIVACY` | `private` | `private` / `unlisted` / `public` |
| `YT_TOKEN_FILE` | `server/token.json` | caminho do token OAuth |
| `JARVIS_STATE_FILE` | `server/state.json` | estado persistido (modo, histórico) |
| `JARVIS_MEMORY_FILE` | `server/memory.json` | memória persistente (fatos + conversas) |
| `JARVIS_PENDING_DIR` | `server/pending/` | onde vídeos aguardando revisão ficam guardados |
| `JARVIS_MUSIC_DIR` | `server/music/` | pasta de trilhas `.mp3` para o fundo musical (vazia = sem música) |
| `JARVIS_MUSIC_VOLUME` | `0.12` | volume da música sob a narração (0 a 1) |
| `TELEGRAM_BOT_TOKEN` | — | opcional: liga o companheiro no Telegram |
| `TELEGRAM_CHAT_ID` | — | seu chat id (o bot te informa na primeira mensagem) |
| `JARVIS_VAPID_FILE` | `server/vapid_private.pem` | chave das notificações push (gerada sozinha) |
| `JARVIS_PUSH_SUBS_FILE` | `server/push_subs.json` | aparelhos inscritos nas notificações |

### 🔔 Notificações nativas (Web Push)

O app tem notificações push próprias — chegam no celular **mesmo com o app fechado**, sem nenhum serviço de terceiro. Ligue o toggle "🔔 Notifications" no painel (o navegador pede permissão uma vez) e pronto: aviso quando um vídeo é postado, quando há vídeo esperando revisão e quando o pipeline falha. As chaves VAPID são geradas sozinhas no primeiro boot; teste com `POST /push/test`.

> Requisito da plataforma web: push (assim como o microfone) só funciona com o app servido em **HTTPS** (ou localhost). O jeito mais fácil de ter HTTPS apontando para o seu backend em casa é um túnel gratuito do Cloudflare (`cloudflared tunnel --url http://localhost:8741`) — você ganha uma URL https pública e abre `https://sua-url/app/` no celular.

### 📱 Telegram (opcional — segundo controle remoto)

Módulo totalmente opcional (`jarvis/telegram_bot.py`): sem o token, nada muda. Com ele, o Jarvis te **avisa** quando posta um vídeo, quando o pipeline falha e quando há vídeo esperando revisão (mandando o próprio arquivo para você assistir no chat), e **obedece por mensagem** — qualquer texto no chat do bot vai para o mesmo cérebro do app ("switch to manual", "make a science video", "briefing", "approve the video"). Setup: fale com o **@BotFather** no Telegram → `/newbot` → copie o token para `TELEGRAM_BOT_TOKEN`; mande uma mensagem para o seu bot e ele responde com o seu chat id → coloque em `TELEGRAM_CHAT_ID` e reinicie. Só esse chat é obedecido; estranhos são ignorados.

> Nota sobre o Fable 5: exige retenção de dados de 30 dias na conta Anthropic (não funciona com zero data retention) e o custo é acima do tier Opus. Para trocar, basta `CLAUDE_MODEL=claude-opus-4-8`.

## 2. App mobile (PWA)

Sirva a pasta `app/` em HTTPS (Vercel, Netlify, GitHub Pages…). Para testar local:

```bash
cd jarvis-mobile/app && python -m http.server 8080
```

No celular (Chrome/Android):

1. Abra a URL do app e permita o **microfone** (reconhecimento de voz e wake word exigem HTTPS ou localhost).
2. Menu ⋮ → **"Adicionar à tela inicial"** para instalar como app.
3. Aponte o app para o seu backend: no console do navegador,
   `localStorage.setItem('jarvis_api', 'https://seu-servidor:8741')` (default: `http://localhost:8741`).
4. Diga **"Hello, Jarvis"**. 🎙️

> A escuta da wake word funciona com o app aberto na tela (navegadores não permitem microfone contínuo em segundo plano — essa é uma limitação da plataforma web, não do app).

## Avisos importantes (YouTube e voz)

- **Conteúdo de IA**: o upload já marca `containsSyntheticMedia: true` e inclui aviso de conteúdo gerado por IA na descrição, conforme as políticas do YouTube para mídia sintética/alterada.
- **Privacidade inicial**: vídeos enviados por apps OAuth **não verificados pelo YouTube** ficam travados como *private* até o app passar pela auditoria do Google. Comece com `YT_PRIVACY=private`, valide o pipeline e solicite a auditoria quando quiser publicar direto.
- **Quota**: cada upload custa ~1600 unidades da quota diária padrão (10.000/dia) — 12 vídeos/dia cabem, mas monitore no Cloud Console.
- **Voz**: a voz é um TTS britânico genérico (navegador no app, "onyx" nos vídeos) — não é clonagem da voz do ator dos filmes, o que violaria direitos de imagem/voz.
