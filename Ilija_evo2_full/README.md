# 🤖 Ilija – Autonomer KI-Agent v5.0

> **Offenes Leuchten** – Ein selbst-erweiterndes KI-Agent-System mit Langzeitgedächtnis,
> WhatsApp-Integration, Telegram-Fernsteuerung und modernem Web-Interface.

Der Agent **Ilija** denkt selbst, plant seine Schritte und bringt sich neue Fähigkeiten
zur Laufzeit bei – ohne Neustart.

---

## ✨ Features

- **Multi-Provider**: Claude (Anthropic), ChatGPT (OpenAI), Gemini (Google), Ollama (lokal)
- **Auto-Fallback**: wählt automatisch den besten verfügbaren Provider
- **Selbst-Entwicklung**: Ilija erstellt neue Skills on-the-fly – einfach beschreiben, was du brauchst
- **Langzeitgedächtnis**: ChromaDB-basiertes Vektorspeicher-System – dauerhaft, auch nach Neustart
- **Web-Interface**: modernes Browser-Chat mit Mikrofon, Datei-Upload & Skill-Reload
- **Telegram-Interface**: vollständige Fernsteuerung per Telegram – Text, Sprache, Bilder, Dateien
- **WhatsApp-Integration**: Ilija überwacht Chats, schreibt Kontakte an und vereinbart Termine
- **Terminal-Modus**: klassische CLI für Entwickler

---

## 🚀 Schnellstart

### Option A – Automatisch mit install.sh (empfohlen)

```bash
git clone https://github.com/Innobytix-IT/ilija-AI-Agent.git
cd ilija-AI-Agent/Ilija_evo2_full
chmod +x install.sh
./install.sh
```

Das Skript führt dich interaktiv durch alle 7 Schritte:
Ollama, alle Python-Pakete, Google Chrome, Whisper, API-Keys, Telegram-Bot-Einrichtung und Startmodus-Auswahl.

### Option B – Manuell

```bash
git clone https://github.com/Innobytix-IT/ilija-AI-Agent.git
cd ilija-AI-Agent/Ilija_evo2_full

# Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# API Keys konfigurieren
cp .env.example .env
# .env öffnen und mindestens einen Key eintragen

# Starten
python web_server.py   # → http://localhost:5000
```

---

## ▶️ Starten

```bash
cd ilija-AI-Agent/Ilija_evo2_full
source venv/bin/activate
```

| Interface | Befehl | Erreichbar unter |
|-----------|--------|-----------------|
| Web-Interface | `python web_server.py` | http://localhost:5000 |
| Telegram-Bot | `python telegram_bot.py` | Telegram-App |
| Beide gleichzeitig | `python telegram_bot.py & python web_server.py` | Beides parallel |
| Terminal-Modus | `python kernel.py` | Direkt in der Konsole |

---

## 📁 Projektstruktur

```
Ilija_evo2_full/
├── install.sh                  # Interaktives Installationsskript (empfohlen)
├── web_server.py               # Flask Web-Interface
├── telegram_bot.py             # Telegram-Bot
├── kernel.py                   # Zentraler Agent + Terminal-Modus
├── providers.py                # KI-Provider (Claude/GPT/Gemini/Ollama)
├── skill_manager.py            # Dynamisches Skill-Laden & Ausführen
├── agent_state.py              # Zustandsautomat
├── autonomy_loop.py            # Autonomie-Loop
├── skill_policy.py             # Sicherheits-Layer (SAFE/INTERACTIVE/RISKY)
├── skill_scoring.py            # Skill-Bewertung & Statistiken
├── skill_versioning.py         # Versionierung & automatische Backups
├── skill_validator.py          # Skill-Code-Validierung
├── skill_registry.py           # Geschützte Skills & Status-Verwaltung
├── model_registry.py           # Dynamische Modell-Konfiguration
├── models_config.json          # Aktuelle Modell-Einstellungen
├── skills/                     # Skill-Bibliothek (erweiterbar)
│   ├── basis_tools.py
│   ├── gedaechtnis.py          # ChromaDB Langzeitgedächtnis
│   ├── skill_factory_improved.py
│   ├── whatsapp_autonomer_dialog.py
│   ├── webseiten_inhalt_lesen.py
│   └── ...
├── templates/index.html        # Web-UI Template
├── static/                     # CSS, JS
├── memory/                     # ChromaDB Datenbank (lokal, nicht committet)
├── .env.example                # Konfigurations-Vorlage
├── .gitignore
└── requirements.txt
```

---

## 🔧 Provider konfigurieren

| Provider | Env-Variable | Modell |
|----------|-------------|--------|
| Claude (Anthropic) | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 |
| ChatGPT (OpenAI) | `OPENAI_API_KEY` | gpt-4o |
| Gemini (Google) | `GOOGLE_API_KEY` | gemini-2.5-flash |
| Ollama (lokal) | — | qwen2.5:7b (kein Key nötig) |

Der `auto`-Modus wählt automatisch den ersten verfügbaren Provider (Claude → GPT → Gemini → Ollama).
Ohne Cloud-Key funktioniert Ilija vollständig offline mit einem lokalen Ollama-Modell.

---

## 📱 Telegram-Bot einrichten

1. Öffne Telegram und suche **@BotFather**
2. Tippe `/newbot` → Name eingeben → Username eingeben (muss auf `bot` enden)
3. Token kopieren und in `.env` eintragen: `TELEGRAM_BOT_TOKEN=...`
4. Deine User-ID über **@userinfobot** herausfinden: `TELEGRAM_ALLOWED_USERS=...`
5. Bot starten: `python telegram_bot.py`

Nur deine User-ID kann Ilija steuern – andere Nutzer erhalten keine Antwort.

---

## 💬 WhatsApp-Integration

Ilija steuert WhatsApp Web automatisch über Google Chrome (Selenium).

**Voraussetzung:** Google Chrome installiert, WhatsApp Web einmalig eingeloggt.

| Modus | Befehl an Ilija |
|-------|----------------|
| Einzelnen Kontakt überwachen | `"Überwache Kontakt: [Name]"` |
| Alle Chats überwachen | `"Überwache alle WhatsApp-Chats"` |
| Anrufbeantworter | `"Starte WhatsApp-Anrufbeantworter"` |
| Termine anzeigen | `"Zeig mir den WhatsApp-Kalender"` |
| Nachrichten abrufen | `"Zeig mir hinterlassene Nachrichten"` |

---

## 🧠 Skill-System

Skills sind Python-Dateien im `skills/`-Ordner. Einfachstes Format:

```python
def mein_skill(parameter: str) -> str:
    """Beschreibung für die KI – wann soll dieser Skill genutzt werden?"""
    return f"Ergebnis: {parameter}"

AVAILABLE_SKILLS = [mein_skill]
```

Nach dem Speichern: Reload-Button im Web-Interface oder `/reload` in Telegram.

Oder direkt Ilija bitten:
```
"Erstelle einen Skill der das Wetter in Berlin abfragt"
```

---

## 💬 Befehle

**Terminal-Modus (`python kernel.py`):**

| Befehl | Funktion |
|--------|----------|
| `reload` | Skills neu laden |
| `debug` | System-Status anzeigen |
| `clear` | Chat-Verlauf löschen |
| `switch` | Provider wechseln |
| `exit` | Beenden |

**Telegram:**

| Befehl | Funktion |
|--------|----------|
| `/start` | Bot starten |
| `/reload` | Skills neu laden |
| `/status` | System-Status |
| `/help` | Alle Befehle anzeigen |

---

## 🛡️ Sicherheit

- **Skill-Policy**: Drei Stufen – SAFE (automatisch), INTERACTIVE (Bestätigung), RISKY (explizite Genehmigung)
- **Telegram-Whitelist**: Nur eingetragene User-IDs können Ilija steuern
- **Geschützte Skills**: `PROTECTED_SKILLS` verhindert Überschreiben kritischer Skills
- **API Keys**: ausschließlich aus `.env` – niemals hardcoded
- **WhatsApp**: Kontakte können keine Kernel-Befehle ausführen – nur Dialog-Modus

---

## 📋 Anforderungen

- Python 3.10+
- Ubuntu / Debian Linux (empfohlen) oder macOS
- Google Chrome (für WhatsApp-Skill)
- Mindestens ein API Key **oder** lokales Ollama-Modell

---

## 🔗 Versionshistorie

| Version | Repository |
|---------|-----------|
| v1.0 (Ursprung) | [offenes-leuchten](https://github.com/Innobytix-IT/offenes-leuchten) |
| v5.0 (aktuell) | [ilija-AI-Agent](https://github.com/Innobytix-IT/ilija-AI-Agent) ← du bist hier |

---

## 📄 Lizenz

MIT License – freie Nutzung, Weitergabe und Modifikation.
