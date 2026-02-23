# 🤖 Ilija – Autonomer KI-Agent v5.0
(The English translation can be found below.)

> **Offenes Leuchten** – Autonomer KI-Agent mit Langzeitgedächtnis, WhatsApp, Telegram & Web-Interface.

---

## 📂 Das Projekt liegt in diesem Ordner:

```
👉 Ilija_evo2_full/
```

### Direkt loslegen:

```bash
git clone https://github.com/Innobytix-IT/ilija-AI-Agent.git
cd ilija-AI-Agent/Ilija_evo2_full
chmod +x install.sh
./install.sh
```

→ Die vollständige Dokumentation und README befindet sich in **[Ilija_evo2_full/README.md](./Ilija_evo2_full/README.md)**

---

## ✨ Kurzübersicht

- 🧠 **Langzeitgedächtnis** – ChromaDB, dauerhaft auch nach Neustart
- ⚡ **Skill-System** – Ilija programmiert sich neue Fähigkeiten selbst
- 💬 **WhatsApp** – überwacht Chats, vereinbart Termine, nimmt Nachrichten an
- 📱 **Telegram** – vollständige Fernsteuerung per App
- 🌐 **Web-Interface** – Browser-Chat mit Mikrofon & Datei-Upload
- 🤖 **Multi-Provider** – Claude → GPT → Gemini → Ollama (automatisch)

---

*Erste Version: [offenes-leuchten (v1.0)](https://github.com/Innobytix-IT/offenes-leuchten)*











---

---

# 🤖 Ilija – Autonomous AI Agent v5.0

> **Offenes Leuchten** ("Open Glow") – A self-expanding AI agent system with long-term memory,
> WhatsApp integration, Telegram remote control and a modern web interface.

The agent **Ilija** thinks independently, plans its own steps and teaches itself new skills
at runtime – no restart required.

---

## ✨ Features

- **Multi-Provider**: Claude (Anthropic), ChatGPT (OpenAI), Gemini (Google), Ollama (local)
- **Auto-Fallback**: automatically selects the best available provider
- **Self-Development**: Ilija writes new skills on-the-fly – just describe what you need
- **Long-Term Memory**: ChromaDB vector storage – persistent across restarts
- **Web Interface**: modern browser chat with microphone, file upload & skill reload
- **Telegram Interface**: full remote control via Telegram – text, voice, images, files
- **WhatsApp Integration**: Ilija monitors chats, messages contacts and schedules appointments
- **Terminal Mode**: classic CLI for developers

---

## 🚀 Quickstart

### Option A – Automatic with install.sh (recommended)

```bash
git clone https://github.com/Innobytix-IT/ilija-AI-Agent.git
cd ilija-AI-Agent/Ilija_evo2_full
chmod +x install.sh
./install.sh
```

The script guides you interactively through all 7 steps:
Ollama, Python packages, Google Chrome, Whisper, API keys, Telegram bot setup and start mode selection.

### Option B – Manual

```bash
git clone https://github.com/Innobytix-IT/ilija-AI-Agent.git
cd ilija-AI-Agent/Ilija_evo2_full

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Open .env and enter at least one key

# Start
python web_server.py   # → http://localhost:5000
```

---

## ▶️ Starting Ilija

```bash
cd ilija-AI-Agent/Ilija_evo2_full
source venv/bin/activate
```

| Interface | Command | Available at |
|-----------|---------|-------------|
| Web Interface | `python web_server.py` | http://localhost:5000 |
| Telegram Bot | `python telegram_bot.py` | Telegram app |
| Both simultaneously | `python telegram_bot.py & python web_server.py` | Both in parallel |
| Terminal Mode | `python kernel.py` | Directly in console |

---

## 🔧 Provider configuration

| Provider | Env variable | Model |
|----------|-------------|-------|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | gpt-4o |
| Gemini (Google) | `GOOGLE_API_KEY` | gemini-2.5-flash |
| Ollama (local) | — | qwen2.5:7b (no key required) |

`auto` mode automatically selects the first available provider (Claude → GPT → Gemini → Ollama).
Without a cloud key, Ilija works fully offline with a local Ollama model.

---

## 📱 Telegram Bot Setup

1. Open Telegram and search for **@BotFather**
2. Type `/newbot` → enter a name → enter a username (must end with `bot`)
3. Copy the token and add it to `.env`: `TELEGRAM_BOT_TOKEN=...`
4. Find your user ID via **@userinfobot**: `TELEGRAM_ALLOWED_USERS=...`
5. Start the bot: `python telegram_bot.py`

Only your user ID can control Ilija – other users receive no response.

---

## 💬 WhatsApp Integration

Ilija controls WhatsApp Web automatically via Google Chrome (Selenium).

**Requirement:** Google Chrome installed, WhatsApp Web logged in once.

| Mode | Command to Ilija |
|------|----------------|
| Monitor single contact | `"Überwache Kontakt: [Name]"` |
| Monitor all chats | `"Überwache alle WhatsApp-Chats"` |
| Answering machine mode | `"Starte WhatsApp-Anrufbeantworter"` |
| Show calendar | `"Zeig mir den WhatsApp-Kalender"` |
| Retrieve messages | `"Zeig mir hinterlassene Nachrichten"` |

---

## 🧠 Skill System

Skills are Python files in the `skills/` folder. Minimal format:

```python
def my_skill(parameter: str) -> str:
    """Description for the AI – when should this skill be used?"""
    return f"Result: {parameter}"

AVAILABLE_SKILLS = [my_skill]
```

After saving: click the reload button in the web interface or type `/reload` in Telegram.

Or simply ask Ilija:
```
"Create a skill that fetches the current weather in Berlin"
```

---

## 💬 Commands

**Terminal Mode (`python kernel.py`):**

| Command | Function |
|---------|----------|
| `reload` | Reload skills |
| `debug` | Show system status |
| `clear` | Clear chat history |
| `switch` | Switch provider |
| `exit` | Quit |

**Telegram:**

| Command | Function |
|---------|----------|
| `/start` | Start the bot |
| `/reload` | Reload skills |
| `/status` | System status |
| `/help` | Show all commands |

---

## 🛡️ Security

- **Skill Policy**: three levels – SAFE (automatic), INTERACTIVE (confirmation required), RISKY (explicit approval)
- **Telegram Whitelist**: only registered user IDs can control Ilija
- **Protected Skills**: `PROTECTED_SKILLS` prevents overwriting critical skills
- **API Keys**: exclusively loaded from `.env` – never hardcoded
- **WhatsApp**: contacts cannot execute kernel commands – dialog mode only

---

## 📋 Requirements

- Python 3.10+
- Ubuntu / Debian Linux (recommended) or macOS
- Google Chrome (for WhatsApp skill)
- At least one API key **or** a local Ollama model

---

## 🔗 Version History

| Version | Repository |
|---------|-----------|
| v1.0 (origin) | [offenes-leuchten](https://github.com/Innobytix-IT/offenes-leuchten) |
| v5.0 (current) | [ilija-AI-Agent](https://github.com/Innobytix-IT/ilija-AI-Agent) ← you are here |

---

## 📄 License

MIT License – free to use, share and modify.
