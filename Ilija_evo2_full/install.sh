#!/bin/bash
# =============================================================================
#  Offenes Leuchten v5.0 – Installationsskript
#  Ilija: Autonomer KI-Agent mit Langzeitgedächtnis, WhatsApp & Telegram
# =============================================================================

set -e

RED='\033[0;31m';  GREEN='\033[0;32m';  YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m';   MAGENTA='\033[0;35m'
BOLD='\033[1m';    RESET='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BLUE}${BOLD}║${RESET}  ${CYAN}${BOLD}$1${RESET}"
    echo -e "${BLUE}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
}
print_step()  { echo -e "${GREEN}${BOLD}▶  $1${RESET}"; }
print_info()  { echo -e "${CYAN}   ℹ  $1${RESET}"; }
print_warn()  { echo -e "${YELLOW}   ⚠  $1${RESET}"; }
print_ok()    { echo -e "${GREEN}   ✅  $1${RESET}"; }
print_error() { echo -e "${RED}   ❌  $1${RESET}"; }
divider()     { echo -e "${BLUE}──────────────────────────────────────────────────────────────${RESET}"; }

# =============================================================================
# Willkommen
# =============================================================================
clear
echo ""
echo -e "${MAGENTA}${BOLD}"
echo "  ██╗██╗     ██╗     ██╗ █████╗ "
echo "  ██║██║     ██║     ██║██╔══██╗"
echo "  ██║██║     ██║     ██║███████║"
echo "  ██║██║     ██║██   ██║██╔══██║"
echo "  ██║███████╗██║╚█████╔╝██║  ██║"
echo "  ╚═╝╚══════╝╚═╝ ╚════╝ ╚═╝  ╚═╝"
echo -e "${RESET}"
echo -e "${CYAN}${BOLD}         Offenes Leuchten v5.0 – Setup${RESET}"
echo -e "${CYAN}         Dein autonomer KI-Agent wartet auf dich...${RESET}"
echo ""; divider; echo ""
echo "  Dieses Skript installiert alle Abhängigkeiten und"
echo "  richtet Ilija Schritt für Schritt vollständig ein."
echo ""; divider
sleep 1

# =============================================================================
# SCHRITT 0: Installationspfad
# =============================================================================
print_header "SCHRITT 0/7 – Installationspfad"

DEFAULT_INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "  ${BOLD}Wo soll Ilija installiert werden?${RESET}"
echo ""
echo -e "  Standard: ${CYAN}${DEFAULT_INSTALL_DIR}${RESET}"
echo "  [1] Standard-Pfad verwenden"
echo "  [2] Eigenen Pfad angeben"
echo ""
read -rp "  Deine Wahl [1/2]: " PATH_CHOICE

INSTALL_DIR="$DEFAULT_INSTALL_DIR"
if [ "$PATH_CHOICE" = "2" ]; then
    echo ""
    read -rp "  Pfad eingeben: " CUSTOM_PATH
    CUSTOM_PATH="${CUSTOM_PATH/#\~/$HOME}"
    if [ -n "$CUSTOM_PATH" ]; then
        INSTALL_DIR="$CUSTOM_PATH"
        mkdir -p "$INSTALL_DIR"
        if [ "$INSTALL_DIR" != "$DEFAULT_INSTALL_DIR" ]; then
            print_step "Kopiere Projektdateien nach $INSTALL_DIR ..."
            cp -r "$DEFAULT_INSTALL_DIR"/. "$INSTALL_DIR/"
            print_ok "Dateien kopiert"
        fi
    fi
fi

print_ok "Installationspfad: ${INSTALL_DIR}"
cd "$INSTALL_DIR"

# =============================================================================
# SCHRITT 1: Python prüfen
# =============================================================================
print_header "SCHRITT 1/7 – Python prüfen"

if ! command -v python3 &> /dev/null; then
    print_error "Python3 nicht gefunden!"
    echo "  → sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    print_error "Python $PYTHON_VERSION gefunden – mindestens 3.10 benötigt!"
    echo "  → sudo apt install python3.10"; exit 1
fi
print_ok "Python $PYTHON_VERSION ✓"

# =============================================================================
# SCHRITT 2: Lokales KI-Modell (Ollama)
# =============================================================================
print_header "SCHRITT 2/7 – Lokales KI-Modell (Ollama)"

OLLAMA_INSTALLED=false
OLLAMA_HAS_MODELS=false
SELECTED_LOCAL_MODEL=""

if command -v ollama &> /dev/null; then
    OLLAMA_INSTALLED=true
    print_ok "Ollama ist bereits installiert"
    MODELS=$(ollama list 2>/dev/null | tail -n +2 | awk '{print $1}' | grep -v "^$" || true)
    if [ -n "$MODELS" ]; then
        OLLAMA_HAS_MODELS=true
        echo ""
        print_ok "Vorhandene lokale Modelle:"
        ollama list 2>/dev/null | tail -n +2 | awk '{printf "      \U0001F916  %s\n", $1}'
        SELECTED_LOCAL_MODEL=$(ollama list 2>/dev/null | tail -n +2 | awk 'NR==1{print $1}')
        print_info "Standardmäßig wird '${SELECTED_LOCAL_MODEL}' als Fallback verwendet."
    else
        print_warn "Ollama installiert, aber kein Modell vorhanden."
    fi
else
    print_warn "Ollama nicht installiert."
fi

select_and_pull_model() {
    echo ""; divider; echo ""
    echo -e "  ${BOLD}Verfügbare lokale Modelle:${RESET}"; echo ""
    echo -e "  ${CYAN}  Normale Hardware (8-16 GB RAM):${RESET}"
    echo "  [1] qwen2.5:7b     ~ 4.7 GB  Empfohlen - schnell & intelligent"
    echo "  [2] llama3.2:3b    ~ 2.0 GB  Sehr schnell, wenig RAM"
    echo "  [3] mistral:7b     ~ 4.1 GB  Stark in Deutsch & Logik"
    echo "  [4] gemma3:4b      ~ 3.3 GB  Google-Modell, effizient"
    echo ""
    echo -e "  ${CYAN}  Leistungsstarke Hardware (32+ GB RAM):${RESET}"
    echo "  [5] llama3.1:8b    ~ 4.7 GB  Meta bestes 8B Modell"
    echo "  [6] qwen2.5:14b    ~ 9.0 GB  Sehr intelligent"
    echo "  [7] deepseek-r1:8b ~ 4.9 GB  Stark in Reasoning"
    echo ""
    echo "  [8] Ueberspringen"; echo ""
    read -rp "  Deine Wahl [1-8]: " MODEL_CHOICE
    case $MODEL_CHOICE in
        1) SELECTED_LOCAL_MODEL="qwen2.5:7b" ;;
        2) SELECTED_LOCAL_MODEL="llama3.2:3b" ;;
        3) SELECTED_LOCAL_MODEL="mistral:7b" ;;
        4) SELECTED_LOCAL_MODEL="gemma3:4b" ;;
        5) SELECTED_LOCAL_MODEL="llama3.1:8b" ;;
        6) SELECTED_LOCAL_MODEL="qwen2.5:14b" ;;
        7) SELECTED_LOCAL_MODEL="deepseek-r1:8b" ;;
        8) print_info "Uebersprungen."; return ;;
        *) print_warn "Ungueltig - ueberspringe."; return ;;
    esac
    echo ""
    print_step "Lade Modell '$SELECTED_LOCAL_MODEL' herunter..."
    print_warn "Das kann einige Minuten dauern..."; echo ""
    ollama pull "$SELECTED_LOCAL_MODEL"
    print_ok "'$SELECTED_LOCAL_MODEL' bereit!"
}

if [ "$OLLAMA_HAS_MODELS" = false ]; then
    echo ""
    echo -e "  ${BOLD}Moechtest du ein lokales KI-Modell installieren?${RESET}"
    echo -e "  ${CYAN}  Vorteil: laeuft offline, kein API-Key noetig, perfekter Fallback${RESET}"; echo ""
    read -rp "  Lokales Modell installieren? [j/N]: " LOCAL_CHOICE
    if [[ "$LOCAL_CHOICE" =~ ^[jJ]$ ]]; then
        if [ "$OLLAMA_INSTALLED" = false ]; then
            print_step "Installiere Ollama..."
            curl -fsSL https://ollama.com/install.sh | sh
            OLLAMA_INSTALLED=true
            print_ok "Ollama installiert"
            sleep 2
        fi
        select_and_pull_model
    else
        print_info "Lokales Modell uebersprungen."
    fi
fi

# =============================================================================
# SCHRITT 3: Python-Abhaengigkeiten (VOLLSTAENDIG)
# =============================================================================
print_header "SCHRITT 3/7 – Python-Abhaengigkeiten installieren"

if [ ! -d "venv" ]; then
    print_step "Erstelle virtuelle Python-Umgebung..."
    python3 -m venv venv
    print_ok "Virtuelle Umgebung erstellt"
else
    print_ok "Virtuelle Umgebung bereits vorhanden"
fi

source venv/bin/activate
print_ok "Virtuelle Umgebung aktiviert"

print_step "Aktualisiere pip..."
pip install --upgrade pip --quiet
print_ok "pip aktualisiert"

print_step "Installiere Kern-Pakete..."
echo "   flask, flask-cors, python-dotenv, requests"
echo "   anthropic, openai, ollama"
echo "   beautifulsoup4, lxml (Webseiten lesen)"
pip install \
    "flask>=3.0.0" \
    "flask-cors>=4.0.0" \
    "python-dotenv>=1.0.0" \
    "requests>=2.31.0" \
    "anthropic>=0.40.0" \
    "openai>=1.54.0" \
    "ollama>=0.1.0" \
    "beautifulsoup4>=4.12.0" \
    "lxml>=4.9.0" \
    --quiet 2>&1 | grep -E "(Successfully|already|error|ERROR)" || true
print_ok "Kern-Pakete installiert"

print_step "Installiere ChromaDB (Langzeitgedaechtnis)..."
pip install "chromadb>=0.4.0" --quiet
print_ok "ChromaDB installiert"

print_step "Installiere Sentence-Transformer (Gedaechtnis-KI)..."
print_warn "Dauert beim ersten Mal etwas laenger (Modell-Download ~90 MB)..."
pip install "sentence-transformers>=2.2.0" --quiet
print_ok "Sentence-Transformer installiert"

print_step "Installiere Telegram-Bot-Bibliothek..."
pip install "python-telegram-bot>=20.0" --quiet
print_ok "Telegram-Bot installiert"

print_step "Installiere Selenium & WebDriver (fuer WhatsApp Web)..."
pip install "selenium>=4.0.0" "webdriver-manager>=4.0.0" --quiet
print_ok "Selenium & WebDriver installiert"

# Google Chrome pruefen
echo ""
if command -v google-chrome &> /dev/null || command -v google-chrome-stable &> /dev/null; then
    CHROME_VER=$(google-chrome --version 2>/dev/null || google-chrome-stable --version 2>/dev/null || echo "Unbekannte Version")
    print_ok "Google Chrome gefunden: $CHROME_VER"
else
    print_warn "Google Chrome nicht gefunden (wird fuer den WhatsApp-Skill benoetigt)"
    echo ""
    read -rp "  Chrome jetzt automatisch installieren? [j/N]: " CHROME_CHOICE
    if [[ "$CHROME_CHOICE" =~ ^[jJ]$ ]]; then
        print_step "Installiere Google Chrome..."
        wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb
        sudo apt install -y /tmp/chrome.deb
        rm /tmp/chrome.deb
        print_ok "Google Chrome installiert"
    else
        print_info "Chrome kann spaeter manuell installiert werden."
        print_info "WhatsApp-Skill ohne Chrome nicht nutzbar."
    fi
fi

# Whisper – Lokale Spracherkennung (optional)
echo ""
divider
echo ""
echo -e "  ${BOLD}Spracherkennung (Whisper) – optional${RESET}"
echo -e "  ${CYAN}  Transkribiert Sprachnachrichten in WhatsApp, Telegram & Web-Interface.${RESET}"
echo -e "  ${CYAN}  Benoetigt: ~2-3 GB Speicher (PyTorch + Whisper-Modell)${RESET}"
echo -e "  ${CYAN}  Ohne Whisper: OpenAI Whisper-API als Fallback (wenn OPENAI_API_KEY gesetzt)${RESET}"
echo ""
read -rp "  Whisper (lokale Spracherkennung) installieren? [j/N]: " WHISPER_CHOICE
if [[ "$WHISPER_CHOICE" =~ ^[jJ]$ ]]; then
    print_step "Installiere openai-whisper (inkl. PyTorch)..."
    print_warn "Das kann 5-10 Minuten dauern..."
    pip install openai-whisper --quiet
    print_ok "Whisper installiert"
else
    print_info "Whisper uebersprungen."
fi

# PDF & Word-Dokumente (optional)
echo ""
echo -e "  ${BOLD}PDF & Word-Unterstuetzung – optional${RESET}"
echo -e "  ${CYAN}  Liest .pdf, .docx, .doc Dateien im Web-Interface & Telegram.${RESET}"
echo ""
read -rp "  PDF & Word-Unterstuetzung installieren? [j/N]: " DOCS_CHOICE
if [[ "$DOCS_CHOICE" =~ ^[jJ]$ ]]; then
    print_step "Installiere PyPDF2, pdfplumber, python-docx..."
    pip install PyPDF2 pdfplumber python-docx --quiet
    print_ok "PDF & Word-Unterstuetzung installiert"
else
    print_info "Dokument-Verarbeitung uebersprungen."
fi

# Ordner & .env vorbereiten
mkdir -p memory skills/.skill_backups

if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || echo "ANONYMIZED_TELEMETRY=False" > .env
fi
grep -q "ANONYMIZED_TELEMETRY" .env || echo "ANONYMIZED_TELEMETRY=False" >> .env

# Gedaechtnis-Hilfsmodell vorladen
print_step "Lade Gedaechtnis-Hilfsmodell vor (all-MiniLM-L6-v2, ~90 MB)..."
python3 -c "
from sentence_transformers import SentenceTransformer
import warnings
warnings.filterwarnings('ignore')
SentenceTransformer('all-MiniLM-L6-v2')
" 2>/dev/null
print_ok "Gedaechtnis-Hilfsmodell bereit"

# =============================================================================
# SCHRITT 4: Cloud-Provider & API-Keys
# =============================================================================
print_header "SCHRITT 4/7 – Cloud-Provider & API-Keys"

echo -e "  Ilija nutzt Cloud-KI-Provider zusaetzlich zu Ollama."
echo -e "  Er waehlt automatisch den besten verfuegbaren Provider."
echo ""; divider; echo ""

EXISTING_CLAUDE=$(grep "^ANTHROPIC_API_KEY=" .env 2>/dev/null | cut -d'=' -f2 || echo "")
EXISTING_OPENAI=$(grep "^OPENAI_API_KEY="    .env 2>/dev/null | cut -d'=' -f2 || echo "")
EXISTING_GOOGLE=$(grep "^GOOGLE_API_KEY="    .env 2>/dev/null | cut -d'=' -f2 || echo "")

configure_provider() {
    local NAME="$1" VAR="$2" URL="$3" EXISTING="$4"
    if [ -n "$EXISTING" ]; then
        print_ok "$NAME bereits konfiguriert."
        read -rp "     Neu ueberschreiben? [j/N]: " OW
        [[ "$OW" =~ ^[jJ]$ ]] || return
    fi
    echo ""
    print_info "Key beantragen: $URL"
    echo -n "     $NAME API-Key eingeben (leer = ueberspringen): "
    read -rs KEY; echo ""
    if [ -n "$KEY" ]; then
        grep -q "^${VAR}=" .env 2>/dev/null && sed -i "/^${VAR}=/d" .env
        echo "${VAR}=${KEY}" >> .env
        print_ok "$NAME Key gespeichert"
    else
        print_info "$NAME uebersprungen."
    fi
}

echo -e "  ${BOLD}Cloud-Provider einrichten:${RESET}"; echo ""
echo "  [1] Claude (Anthropic)  – Beste Qualitaet"
echo "      console.anthropic.com  (kostenloser Testkredit)"
echo ""
echo "  [2] ChatGPT (OpenAI)    – Sehr gut & weit verbreitet"
echo "      platform.openai.com/api-keys"
echo ""
echo "  [3] Gemini (Google)     – Gut & guenstig (kostenloses Kontingent!)"
echo "      aistudio.google.com/app/apikey"
echo ""
echo "  [4] Alle drei einrichten"
echo "  [5] Keinen – nur lokales Ollama-Modell nutzen"; echo ""
read -rp "  Deine Wahl [1-5]: " PROV_CHOICE

case $PROV_CHOICE in
    1) configure_provider "Claude" "ANTHROPIC_API_KEY" "https://console.anthropic.com" "$EXISTING_CLAUDE" ;;
    2) configure_provider "ChatGPT" "OPENAI_API_KEY" "https://platform.openai.com/api-keys" "$EXISTING_OPENAI" ;;
    3) configure_provider "Gemini" "GOOGLE_API_KEY" "https://aistudio.google.com/app/apikey" "$EXISTING_GOOGLE" ;;
    4)
        configure_provider "Claude" "ANTHROPIC_API_KEY" "https://console.anthropic.com" "$EXISTING_CLAUDE"
        configure_provider "ChatGPT" "OPENAI_API_KEY" "https://platform.openai.com/api-keys" "$EXISTING_OPENAI"
        configure_provider "Gemini" "GOOGLE_API_KEY" "https://aistudio.google.com/app/apikey" "$EXISTING_GOOGLE"
        ;;
    5) print_info "Nur Ollama wird verwendet." ;;
    *) print_warn "Ueberspringe Provider." ;;
esac

# =============================================================================
# SCHRITT 5: Telegram-Bot einrichten (mit vollstaendiger Schritt-fuer-Schritt-Anleitung)
# =============================================================================
print_header "SCHRITT 5/7 – Telegram-Bot einrichten (optional)"

echo -e "  ${BOLD}Was kann der Telegram-Bot?${RESET}"; echo ""
echo "   Ilija von ueberall der Welt steuern (nicht nur im Heimnetz)"
echo "   Textnachrichten, Sprachnachrichten, Bilder & Dateien senden"
echo "   WhatsApp-Listener starten und stoppen"
echo "   Skills neu laden mit /reload"
echo "   Kalender und hinterlassene Nachrichten abrufen"
echo ""; divider; echo ""

EXISTING_TG=$(grep "^TELEGRAM_BOT_TOKEN=" .env 2>/dev/null | cut -d'=' -f2 || echo "")
TG_SKIP=false

if [ -n "$EXISTING_TG" ]; then
    print_ok "Telegram-Bot bereits konfiguriert."
    read -rp "  Neu konfigurieren? [j/N]: " TG_RECONFIG
    if [[ ! "$TG_RECONFIG" =~ ^[jJ]$ ]]; then
        print_info "Telegram-Konfiguration beibehalten."
        TG_SKIP=true
    fi
fi

if [ "$TG_SKIP" = false ]; then
    read -rp "  Telegram-Bot einrichten? [j/N]: " TG_CHOICE
    if [[ "$TG_CHOICE" =~ ^[jJ]$ ]]; then

        echo ""
        echo -e "  ${CYAN}${BOLD}── So erstellst du deinen Telegram-Bot (ca. 2 Minuten) ──────────${RESET}"
        echo ""
        echo -e "  ${BOLD}SCHRITT A – Bot bei Telegram erstellen:${RESET}"
        echo "   1. Oeffne Telegram (Handy-App oder telegram.org im Browser)"
        echo "   2. Suche nach dem Kontakt:  @BotFather"
        echo "      (Offizieller Telegram-Bot mit blauem Haken)"
        echo "   3. Tippe oder klicke:  /newbot"
        echo "   4. Gib einen Anzeigenamen ein, z.B.:  Ilija"
        echo "   5. Gib einen eindeutigen Username ein, z.B.:  mein_ilija_bot"
        echo "      WICHTIG: Der Username muss auf 'bot' enden!"
        echo "   6. BotFather schickt dir jetzt einen Token:"
        echo ""
        echo "      Beispiel-Token:"
        echo -e "      ${YELLOW}1234567890:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxX${RESET}"
        echo ""
        echo "      Diesen Token gleich kopieren!"
        echo ""
        echo -e "  ${BOLD}SCHRITT B – Deine persoenliche Telegram-User-ID herausfinden:${RESET}"
        echo "   1. Suche in Telegram nach:  @userinfobot"
        echo "   2. Tippe:  /start"
        echo "   3. Der Bot antwortet mit deiner ID:"
        echo ""
        echo "      Beispiel-Antwort:"
        echo -e "      ${YELLOW}Id: 123456789${RESET}"
        echo ""
        echo "      Diese Zahl notieren!"
        echo ""
        echo -e "  ${YELLOW}  Sicherheitshinweis:${RESET}"
        echo "  Nur deine User-ID darf Ilija steuern."
        echo "  Andere die deinen Bot finden erhalten keine Antwort."
        echo ""
        divider; echo ""
        read -rp "  Hast du Token und User-ID bereit? Dann weiter mit ENTER..." _
        echo ""

        echo -n "  Bot-Token eingeben: "
        read -rs TG_TOKEN; echo ""
        if [ -n "$TG_TOKEN" ]; then
            grep -q "^TELEGRAM_BOT_TOKEN=" .env 2>/dev/null && sed -i "/^TELEGRAM_BOT_TOKEN=/d" .env
            echo "TELEGRAM_BOT_TOKEN=${TG_TOKEN}" >> .env
            print_ok "Bot-Token gespeichert"
        fi

        echo ""
        echo -n "  Deine Telegram User-ID eingeben: "
        read -r TG_UID
        if [ -n "$TG_UID" ]; then
            grep -q "^TELEGRAM_ALLOWED_USERS=" .env 2>/dev/null && sed -i "/^TELEGRAM_ALLOWED_USERS=/d" .env
            echo "TELEGRAM_ALLOWED_USERS=${TG_UID}" >> .env
            print_ok "User-ID gespeichert – nur du kannst Ilija steuern"
        fi

        echo ""
        print_ok "Telegram-Bot eingerichtet! Teste ihn nach dem Start mit /start"
    else
        print_info "Telegram-Bot uebersprungen – jederzeit nachtraeglich einrichtbar."
    fi
fi

# =============================================================================
# SCHRITT 6: Ilija kennenlernen
# =============================================================================
print_header "SCHRITT 6/7 – Ilija kennenlernen"

echo -e "  ${BOLD}Was ist Ilija?${RESET}"; echo ""
echo "  Ilija ist ein autonomer KI-Agent – kein einfacher Chatbot."
echo "  Er denkt selbst, plant, und bringt sich neue Faehigkeiten bei."
echo ""; divider; echo ""
echo -e "${BOLD}  Langzeitgedaechtnis${RESET}"
echo "  Ilija merkt sich alles – auch nach dem Neustart."
echo "  Beispiel: 'Mein Name ist Manuel' – Ilija weiss das beim naechsten Mal."; echo ""
echo -e "${BOLD}  Skill-System (Selbst-Entwicklung)${RESET}"
echo "  Ilija programmiert sich neue Faehigkeiten on-the-fly."
echo "  Beispiel: 'Erstelle einen Skill der das Wetter abfragt' – sofort nutzbar."; echo ""
echo -e "${BOLD}  WhatsApp-Assistent${RESET}"
echo "  Ueberwacht Chats, vereinbart Termine, nimmt Nachrichten an."; echo ""
echo -e "${BOLD}  Telegram-Fernsteuerung${RESET}"
echo "  Steuere Ilija von ueberall – Sprache, Dateien, Befehle."; echo ""
echo -e "${BOLD}  Web-Interface${RESET}"
echo "  Moderne Chat-Oberflaeche – auch auf dem Handy nutzbar."; echo ""
echo -e "${BOLD}  Multi-Provider: Claude -> GPT -> Gemini -> Ollama${RESET}"
echo "  Ilija waehlt automatisch das beste verfuegbare Modell."; echo ""
divider; echo ""
echo "  Beispiel-Befehle:"
echo "  'Merke dir: Ich heisse Manuel'        -> Langzeitgedaechtnis"
echo "  'Was weisst du ueber mich?'            -> Erinnerungen abrufen"
echo "  'Erstelle einen Skill fuer X'          -> Ilija programmiert ihn"
echo "  'Ueberwache alle WhatsApp-Chats'       -> Listener starten"
echo "  'Zeig mir den WhatsApp-Kalender'       -> Termine anzeigen"
echo "  'Zeig mir hinterlassene Nachrichten'   -> Nachrichten anzeigen"
echo ""

read -rp "  Druecke ENTER um fortzufahren..." _

# =============================================================================
# SCHRITT 7: Startmodus waehlen
# =============================================================================
print_header "SCHRITT 7/7 – Ilija starten"

TG_TOKEN_SET=$(grep "^TELEGRAM_BOT_TOKEN=" .env 2>/dev/null | cut -d'=' -f2 || echo "")

echo -e "  ${BOLD}Wie moechtest du Ilija starten?${RESET}"; echo ""

echo -e "  ${GREEN}[1] Web-Interface${RESET}   (empfohlen fuer Einsteiger)"
echo "         Browser-Chat mit Mikrofon-Aufnahme, Datei-Upload, Skill-Reload"
echo "         http://localhost:5000"; echo ""

if [ -n "$TG_TOKEN_SET" ]; then
    echo -e "  ${CYAN}[2] Telegram-Bot${RESET}"
    echo "         Fernsteuerung per Telegram-App"
    echo "         Ideal fuer unterwegs oder dauerhaften Server-Betrieb"; echo ""

    echo -e "  ${YELLOW}[3] Web-Interface + Telegram gleichzeitig${RESET}   (empfohlen fuer Dauerbetrieb)"
    echo "         Beide Interfaces parallel aktiv"; echo ""
fi

echo -e "  ${BLUE}[4] Terminal-Modus${RESET}   (fuer Entwickler)"
echo "         Klassische Kommandozeile direkt im Terminal"
echo "         Befehle: reload | debug | clear | switch | exit"; echo ""

if [ -n "$TG_TOKEN_SET" ]; then
    read -rp "  Deine Wahl [1/2/3/4]: " START_CHOICE
else
    read -rp "  Deine Wahl [1/4]: " START_CHOICE
fi

# =============================================================================
# Abschluss & Start
# =============================================================================
clear; echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════════════════╗"
echo "  ║                                                              ║"
echo "  ║      Installation abgeschlossen!                            ║"
echo "  ║      Ilija ist bereit. Viel Spass!                          ║"
echo "  ║                                                              ║"
echo "  ╚══════════════════════════════════════════════════════════════╝"
echo -e "${RESET}"; sleep 1

echo -e "${CYAN}  Konfigurierte Provider:${RESET}"
[ -n "$(grep '^ANTHROPIC_API_KEY=' .env 2>/dev/null | cut -d'=' -f2)" ] \
    && echo "     OK  Claude (Anthropic)"   || echo "     --  Claude (nicht konfiguriert)"
[ -n "$(grep '^OPENAI_API_KEY='    .env 2>/dev/null | cut -d'=' -f2)" ] \
    && echo "     OK  ChatGPT (OpenAI)"     || echo "     --  ChatGPT (nicht konfiguriert)"
[ -n "$(grep '^GOOGLE_API_KEY='    .env 2>/dev/null | cut -d'=' -f2)" ] \
    && echo "     OK  Gemini (Google)"      || echo "     --  Gemini (nicht konfiguriert)"
[ -n "$SELECTED_LOCAL_MODEL" ] \
    && echo "     OK  Ollama ($SELECTED_LOCAL_MODEL)" || echo "     --  Ollama (kein Modell gewaehlt)"
[ -n "$(grep '^TELEGRAM_BOT_TOKEN=' .env 2>/dev/null | cut -d'=' -f2)" ] \
    && echo "     OK  Telegram-Bot"         || echo "     --  Telegram-Bot (nicht eingerichtet)"
echo ""

case "$START_CHOICE" in
    2)
        echo -e "${CYAN}${BOLD}  Starte Telegram-Bot...${RESET}"; echo ""
        echo "  Schreibe deinem Bot in Telegram!"
        echo "  Zum Beenden: Ctrl+C"; echo ""; sleep 2
        python3 telegram_bot.py
        ;;
    3)
        echo -e "${YELLOW}${BOLD}  Starte Web-Interface + Telegram-Bot...${RESET}"; echo ""
        echo "  Browser: http://localhost:5000"
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "?")
        echo "  Im Netzwerk: http://${LOCAL_IP}:5000"
        echo "  Telegram: Schreibe deinem Bot"
        echo "  Zum Beenden: Ctrl+C"; echo ""; sleep 2
        python3 telegram_bot.py &
        TG_PID=$!
        trap "kill $TG_PID 2>/dev/null || true" EXIT
        python3 web_server.py
        ;;
    4)
        echo -e "${BLUE}${BOLD}  Starte Terminal-Modus...${RESET}"; echo ""
        echo "  Befehle: reload | debug | clear | switch | exit"
        echo "  Zum Beenden: 'exit' eingeben oder Ctrl+C"; echo ""; sleep 1
        python3 kernel.py
        ;;
    *)
        echo -e "${GREEN}${BOLD}  Starte Web-Interface...${RESET}"; echo ""
        echo "  Browser oeffnen: http://localhost:5000"
        LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "?")
        echo "  Im lokalen Netzwerk: http://${LOCAL_IP}:5000"
        echo "  Zum Beenden: Ctrl+C"; echo ""; sleep 2
        python3 web_server.py
        ;;
esac
