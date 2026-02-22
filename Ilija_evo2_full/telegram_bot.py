"""
Offenes Leuchten – Telegram Interface v1.0
===========================================
Verbindet Ilija mit Telegram als mobiles Interface.

Unterstützte Nachrichtentypen:
  📝  Text        → direkt an Ilija
  🎤  Sprache     → Whisper-Transkription → Ilija
  🖼️   Bilder      → Vision-LLM-Analyse → Ilija
  📄  Dokumente   → Textextraktion → Ilija
  🎯  /goal       → Autonomy Loop

Setup:
  1. @BotFather in Telegram → /newbot → Token kopieren
  2. .env ergänzen:
       TELEGRAM_BOT_TOKEN=dein_token
       TELEGRAM_ALLOWED_USERS=deine_user_id   (optional, aber empfohlen)
  3. Pakete:
       pip install python-telegram-bot openai-whisper PyPDF2 python-docx
  4. Starten:
       python telegram_bot.py
"""

import os
import logging
import asyncio
import tempfile
from pathlib import Path
from typing import Optional

# Telegram
from telegram import Update, Message
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes,
)
from telegram.constants import ChatAction

# Umgebung laden
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Telemetrie vor ChromaDB-Import deaktivieren
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"]     = "False"

# Ilija Kernel
from kernel import Kernel
from agent_state   import AgentState
from autonomy_loop import AutonomyLoop

# ─── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# ─── Konfiguration ────────────────────────────────────────────
BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS = os.getenv("TELEGRAM_ALLOWED_USERS", "")
MAX_MSG_LEN   = 4096

ALLOWED_IDS: set = set()
if ALLOWED_USERS.strip():
    try:
        ALLOWED_IDS = {int(uid.strip()) for uid in ALLOWED_USERS.split(",") if uid.strip()}
    except ValueError:
        logger.warning("TELEGRAM_ALLOWED_USERS enthält ungültige IDs – Filter deaktiviert")

# ─── Kernel-Singleton ─────────────────────────────────────────
_kernel: Optional[Kernel] = None

def get_kernel() -> Kernel:
    global _kernel
    if _kernel is None:
        logger.info("Initialisiere Ilija Kernel...")
        _kernel = Kernel()
        _kernel.load_skills()
        logger.info(f"Kernel bereit – {len(_kernel.manager.loaded_tools)} Skills")
    return _kernel

# ─── Hilfsfunktionen ──────────────────────────────────────────

def is_allowed(user_id: int) -> bool:
    return not ALLOWED_IDS or user_id in ALLOWED_IDS

def split_message(text: str) -> list:
    """Teilt lange Nachrichten auf – erkennt offene Code-Blöcke und repariert sie."""
    if len(text) <= MAX_MSG_LEN:
        return [text]

    parts        = []
    in_code_block = False

    while text:
        if len(text) <= MAX_MSG_LEN:
            if in_code_block:
                text = text.rstrip()
                if not text.endswith("```"):
                    text += "\n```"
            parts.append(text)
            break

        cut = text.rfind("\n", 0, MAX_MSG_LEN)
        if cut == -1:
            cut = text.rfind(" ", 0, MAX_MSG_LEN)
        if cut == -1:
            cut = MAX_MSG_LEN

        chunk = text[:cut]

        # Prüfe ob wir einen Code-Block auf- oder zumachen
        if chunk.count("```") % 2 != 0:
            in_code_block = not in_code_block

        # Code-Block mitten abgeschnitten → provisorisch schließen
        if in_code_block:
            chunk += "\n```"

        parts.append(chunk)
        text = text[cut:].lstrip()

        # Nächsten Chunk mit offenem Code-Block beginnen
        if in_code_block and text:
            text = "```\n" + text

    return parts

async def send_reply(message: Message, text: str):
    if not text or not text.strip():
        text = "(Keine Antwort)"
    for part in split_message(text):
        try:
            await message.reply_text(part, parse_mode="Markdown")
        except Exception:
            await message.reply_text(part)

# ─── Medienverarbeitung (synchron für run_in_executor) ────────

def transcribe_voice_sync(file_path: str) -> str:
    """Spracherkennung via lokalem Whisper oder OpenAI Whisper API."""
    try:
        import whisper, warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
        warnings.filterwarnings("ignore", category=UserWarning, module="torch")
        model = whisper.load_model("base", device="cpu")  # CPU erzwingen
        result = model.transcribe(file_path, language="de")
        return result["text"].strip()
    except ImportError:
        pass
    except Exception as e:
        return f"[Whisper Fehler: {e}]"

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            with open(file_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", file=f, language="de"
                )
            return transcript.text.strip()
        except Exception as e:
            return f"[OpenAI Whisper Fehler: {e}]"

    return "[Spracherkennung nicht verfügbar – pip install openai-whisper]"


def describe_image_sync(image_path: str, user_question: str = "") -> str:
    """Bildbeschreibung via Claude oder GPT-4o Vision."""
    try:
        import base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        prompt = user_question if user_question else "Beschreibe dieses Bild detailliert auf Deutsch."

        # Claude Vision
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model="claude-opus-4-6", max_tokens=1024,
                    messages=[{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}},
                        {"type": "text", "text": prompt},
                    ]}],
                )
                return response.content[0].text
            except Exception as e:
                logger.warning(f"Claude Vision Fehler: {e}")

        # GPT-4o Vision
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                import openai
                client = openai.OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o", max_tokens=1024,
                    messages=[{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                        {"type": "text", "text": prompt},
                    ]}],
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"GPT-4o Vision Fehler: {e}")

        return "[Bildanalyse nicht verfügbar – ANTHROPIC_API_KEY oder OPENAI_API_KEY benötigt]"
    except Exception as e:
        return f"[Bildanalyse fehlgeschlagen: {e}]"


def extract_document_sync(file_path: str, filename: str) -> str:
    """Textextraktion aus PDF, Word und Textdateien."""
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            try:
                import PyPDF2
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join(page.extract_text() or "" for page in reader.pages)
                return text[:8000] if text.strip() else "[PDF enthält keinen lesbaren Text]"
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                    return text[:8000]
                except ImportError:
                    return "[PDF-Extraktion nicht verfügbar – pip install PyPDF2]"

        elif suffix in (".docx", ".doc"):
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join(p.text for p in doc.paragraphs)[:8000]
            except ImportError:
                return "[Word-Extraktion nicht verfügbar – pip install python-docx]"

        elif suffix in (".txt", ".md", ".py", ".js", ".ts", ".json", ".csv",
                        ".xml", ".html", ".yaml", ".yml", ".sh", ".ini"):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(8000)

        else:
            return f"[Dateityp '{suffix}' nicht unterstützt. Unterstützt: PDF, DOCX, TXT, MD, PY, JSON, CSV, ...]"

    except Exception as e:
        return f"[Extraktion fehlgeschlagen: {e}]"


# ─── Ilija-Verarbeitung ───────────────────────────────────────

def process_with_ilija(user_input: str) -> str:
    """Leitet eine Nachricht an den Ilija-Kernel weiter und gibt die Antwort zurück."""
    k = get_kernel()
    try:
        result = k.chat(user_input)
        return result.get("response") or "(keine Antwort)"
    except Exception as e:
        logger.error(f"Kernel-Fehler: {e}", exc_info=True)
        return f"Fehler: {e}"


# ─── Command-Handler ──────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        await update.message.reply_text("Zugriff verweigert.")
        return
    k = get_kernel()
    await update.message.reply_text(
        f"👋 Hallo {update.effective_user.first_name}! Ich bin Ilija.\n\n"
        f"Dein autonomer KI-Agent ist bereit – {len(k.manager.loaded_tools)} Skills geladen.\n\n"
        "Was ich kann:\n"
        "📝 Textnachrichten – einfach schreiben\n"
        "🎤 Sprachnachrichten – ich transkribiere und antworte\n"
        "🖼️ Bilder – ich analysiere und beschreibe sie\n"
        "📄 Dokumente – PDF, Word, TXT, Code...\n"
        "🎯 /goal [Ziel] – autonomer Aufgaben-Loop\n"
        "🔁 /reload – Skills neu laden\n"
        "📊 /status – System-Status\n"
        "🗑️ /clear – Chat-Verlauf leeren\n\n"
        "Einfach loslegen!"
    )

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    k = get_kernel()
    model = getattr(k.provider, "model", "unbekannt")
    await update.message.reply_text(
        f"📊 Ilija Status\n\n"
        f"Provider: {k.provider_name.upper()}\n"
        f"Modell: {model}\n"
        f"Skills: {len(k.manager.loaded_tools)}\n"
        f"Agent-State: {k.state.name}\n"
        f"Chat-Verlauf: {len(k.chat_history)} Einträge"
    )

async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    k = get_kernel()
    loop = asyncio.get_event_loop()
    count = await loop.run_in_executor(None, k.load_skills)
    await update.message.reply_text(f"🔄 {count} Skills neu geladen.")

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    get_kernel().chat_history.clear()
    await update.message.reply_text("🗑️ Chat-Verlauf geleert.")

async def cmd_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Bitte gib ein Ziel an:\n/goal Erstelle einen Skill der...")
        return

    goal_text = " ".join(context.args)
    await update.message.reply_text(
        f"⚡ Autonomy Loop gestartet\n🎯 {goal_text}\n\nIlija arbeitet..."
    )
    await update.message.chat.send_action(ChatAction.TYPING)

    k = get_kernel()
    loop_runner = AutonomyLoop(k, max_iterations=10, verbose=True)
    loop = asyncio.get_event_loop()
    session = await loop.run_in_executor(None, loop_runner.run, goal_text)

    summary = session.final_summary or "Loop abgeschlossen."
    emoji   = "✅" if "goal_reached" in session.status.value else "⚠️"
    await send_reply(update.message,
        f"{emoji} Loop beendet\n\n{summary}\n\n"
        f"Iterationen: {session.iteration} | Schritte: {len(session.plan)}"
    )

# ─── Message-Handler ──────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    user_input = (update.message.text or "").strip()
    if not user_input:
        return
    await update.message.chat.send_action(ChatAction.TYPING)
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, process_with_ilija, user_input)
    await send_reply(update.message, response)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text("🎤 Transkribiere...")
    voice_file = await context.bot.get_file(update.message.voice.file_id)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await voice_file.download_to_drive(tmp_path)
        loop       = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(None, transcribe_voice_sync, tmp_path)

        if transcript.startswith("["):
            await send_reply(update.message, f"⚠️ {transcript}")
            return

        await update.message.reply_text(f"Erkannt: {transcript}")
        await update.message.chat.send_action(ChatAction.TYPING)
        response = await loop.run_in_executor(None, process_with_ilija, transcript)
        await send_reply(update.message, response)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text("🖼️ Analysiere Bild...")
    photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
    caption    = update.message.caption or ""

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await photo_file.download_to_drive(tmp_path)
        loop        = asyncio.get_event_loop()
        description = await loop.run_in_executor(None, describe_image_sync, tmp_path, caption)
        combined    = (
            f"[Bild] {description}\nFrage: {caption}" if caption
            else f"[Bild erhalten] {description}"
        )
        response = await loop.run_in_executor(None, process_with_ilija, combined)
        await send_reply(update.message, response)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    filename = update.message.document.file_name or "dokument"
    await update.message.reply_text(f"📄 Lese {filename}...")
    doc_file = await context.bot.get_file(update.message.document.file_id)
    suffix   = Path(filename).suffix.lower() or ".bin"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
    try:
        await doc_file.download_to_drive(tmp_path)
        loop    = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, extract_document_sync, tmp_path, filename)

        if content.startswith("["):
            await update.message.reply_text(f"⚠️ {content}")
            return

        caption  = update.message.caption or ""
        combined = (
            f"[Dokument: {filename}]\n{content}\n\nAufgabe: {caption}" if caption
            else f"[Dokument: {filename}]\nBitte analysiere:\n\n{content}"
        )
        response = await loop.run_in_executor(None, process_with_ilija, combined)
        await send_reply(update.message, response)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        "Dieser Nachrichtentyp wird nicht unterstützt.\n"
        "Unterstützt: Text, Sprache, Bilder, Dokumente"
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Telegram-Fehler: {context.error}", exc_info=True)


# ─── Start ────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN nicht gesetzt!")
        print("1. @BotFather → /newbot → Token kopieren")
        print("2. .env: TELEGRAM_BOT_TOKEN=dein_token")
        return

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║       Offenes Leuchten – Telegram Interface v1.0        ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    k = get_kernel()
    print(f"✅ Ilija bereit: {len(k.manager.loaded_tools)} Skills | Provider: {k.provider_name.upper()}")
    print(f"🔒 Zugriff: {'Nur ' + str(ALLOWED_IDS) if ALLOWED_IDS else 'Offen (alle User)'}\n")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("clear",  cmd_clear))
    app.add_handler(CommandHandler("goal",   cmd_goal))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO,   handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO,                   handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL,            handle_document))
    app.add_handler(MessageHandler(filters.ALL,                     handle_unsupported))

    app.add_error_handler(error_handler)

    print("🤖 Bot läuft – warte auf Nachrichten...")
    print("Zum Beenden: Ctrl+C\n")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
