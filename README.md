[README.md](https://github.com/user-attachments/files/25473397/README.md)
# 🤖 Projekt Offenes Leuchten -- KI Agent Ilija

Ein selbst-erweiterndes KI-Agent-System mit Langzeitgedächtnis.  
Der Agent **Ilija** kann neue Fähigkeiten (Skills) zur Laufzeit generieren, speichern und direkt nutzen – ohne Neustart.

---

## ✨ Features

- **Multi-Provider**: Claude (Anthropic), ChatGPT (OpenAI), Gemini (Google), Ollama (lokal)
- **Auto-Fallback**: wählt automatisch den besten verfügbaren Provider
- **Selbst-Entwicklung**: Ilija erstellt neue Skills on-the-fly via `skill_erstellen`
- **Langzeitgedächtnis**: ChromaDB-basiertes Vektorspeicher-System
- **Web-Interface**: lokales Flask-Web-UI (v5.0)
- **Terminal-Modus**: klassische CLI (v4.0)
- **Telegram-Interface**: Arbeite mit Ilija über Telegram und nutze Telegram als vollumfängliches Interface
- **WhatsApp-Integration**: Ilija verwaltet WhatsApp - Nachrichten, schreibt mit Kontakten und vereinbart Termine
---

## 🚀 Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/<dein-user>/offenes-leuchten.git
cd offenes-leuchten
```

### 2. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 3. API Keys konfigurieren

```bash
cp .env.example .env
# .env öffnen und mindestens einen API Key eintragen
```

### 4. Starten

**Web-Interface (empfohlen):**
```bash
python web_server.py
# → http://localhost:5000
```

**Terminal-Modus:**
```bash
python main_v4_cloud.py
# Mit bestimmtem Provider: python main_v4_cloud.py --provider claude
```

---

## 📁 Projektstruktur

```
offenes_leuchten/
├── main_v4_cloud.py        # Terminal-Agent (v4.0)
├── web_server.py           # Flask Web-Server (v5.0)
├── skill_manager.py        # Dynamisches Laden & Ausführen von Skills
├── agent_state.py          # Zustandsautomat des Agenten
├── skill_registry.py       # Skill-Status & Schutzmechanismus
├── model_registry.py       # Dynamische Modell-Konfiguration
├── models_config.json      # Aktuelle Modell-Einstellungen
├── skills/                 # Skill-Bibliothek (erweiterbar)
│   ├── basis_tools.py      # Shell, Datei, Zeit
│   ├── gedaechtnis.py      # ChromaDB Langzeitgedächtnis
│   ├── skill_factory_improved.py  # Skill-Erstellung zur Laufzeit
│   └── ...
├── templates/index.html    # Web-UI Template
├── static/                 # CSS, JS, Docs
├── memory/                 # ChromaDB Datenbank (lokal, nicht committet)
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🔧 Provider konfigurieren

| Provider | Env-Variable | Modell |
|----------|-------------|--------|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | gpt-4o |
| Gemini (Google) | `GOOGLE_API_KEY` | gemini-2.5-flash |
| Ollama (lokal) | — | qwen2.5:7b |

Der `auto`-Modus wählt automatisch den ersten verfügbaren Provider (Reihenfolge: Claude → GPT → Gemini → Ollama).

Modelle können zur Laufzeit per Skill geändert werden:
```
Du: Zeige mir die aktuellen Modelle
Du: Ändere das Modell für claude auf claude-opus-4-6
```

---

## 🧠 Skills

Skills sind einfache Python-Dateien im `skills/`-Ordner. Sie werden beim Start und nach jeder Neuerstellung automatisch geladen.

### Eigenen Skill erstellen

Jede Skill-Datei braucht eine `AVAILABLE_SKILLS`-Liste:

```python
def mein_skill(parameter: str) -> str:
    """Beschreibung für die KI."""
    return f"Ergebnis: {parameter}"

AVAILABLE_SKILLS = [mein_skill]
```

Alternativ kann Ilija selbst neue Skills generieren – einfach beschreiben, was du brauchst.

---

## 💬 Terminal-Befehle

| Befehl | Funktion |
|--------|----------|
| `reload` | Skills neu laden |
| `debug` | System-Status anzeigen |
| `clear` | Chat-Verlauf löschen |
| `switch` | Provider wechseln |
| `exit` | Beenden |

---

## 🛡️ Sicherheit

- Kritische Skills (`skill_erstellen`, `wissen_speichern`, etc.) sind durch `PROTECTED_SKILLS` geschützt
- Shell-Befehle werden mit 10s Timeout ausgeführt
- API Keys werden ausschließlich aus `.env` geladen – niemals hardcoded

---

## 📋 Anforderungen

- Python 3.10+
- Mindestens ein API Key oder lokales Ollama

---

## 📄 Lizenz

MIT License – freie Nutzung, Weitergabe und Modifikation.
