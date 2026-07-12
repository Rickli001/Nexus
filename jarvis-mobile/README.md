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

## Estrutura

```
jarvis-mobile/
├── app/      # PWA — instale na tela inicial do celular (Chrome > "Adicionar à tela inicial")
└── server/   # Backend FastAPI — chat, imagens, pipeline de vídeo, scheduler, YouTube
```

## 1. Backend

```bash
cd jarvis-mobile/server
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
uvicorn main:app --host 0.0.0.0 --port 8741
```

O `ffmpeg` precisa estar instalado no sistema (o moviepy usa ele para renderizar).

### Autorizar o YouTube (uma vez)

1. No [Google Cloud Console](https://console.cloud.google.com/): crie um projeto, ative a **YouTube Data API v3** e crie uma credencial OAuth do tipo **Desktop app**.
2. Baixe o JSON como `server/client_secret.json`.
3. Rode `python authorize_youtube.py` e faça login com a conta dona do canal. Isso gera o `token.json` usado pelo servidor.

### Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | — | obrigatória (GPT, DALL-E, TTS) |
| `ANTHROPIC_API_KEY` | — | obrigatória para o Code Mode (Claude) — crie em console.anthropic.com |
| `CLAUDE_MODEL` | `claude-fable-5` | modelo do Code Mode; com Fable 5 o fallback server-side para `claude-opus-4-8` fica ativo (se um pedido benigno for recusado pelo classificador, o Opus responde) |
| `POST_INTERVAL_HOURS` | `2` | intervalo entre posts no modo AUTO |
| `YT_PRIVACY` | `private` | `private` / `unlisted` / `public` |
| `YT_TOKEN_FILE` | `server/token.json` | caminho do token OAuth |
| `JARVIS_STATE_FILE` | `server/state.json` | estado persistido (modo, histórico) |
| `JARVIS_MEMORY_FILE` | `server/memory.json` | memória persistente (fatos + conversas) |
| `JARVIS_PENDING_DIR` | `server/pending/` | onde vídeos aguardando revisão ficam guardados |

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
