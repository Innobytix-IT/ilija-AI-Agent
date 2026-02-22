#!/usr/bin/env python3
"""
Offenes Leuchten v5.0 - Web Edition
Flask Server für Web-Interface im lokalen Netzwerk
"""

from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
import logging
import secrets

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import Kernel (v5.0)
from kernel import Kernel
from autonomy_loop import AutonomyLoop

# Flask App Setup
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
CORS(app)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('web_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global Kernel Instance (eine Instanz pro Session)
kernels = {}


def get_kernel(session_id: str, provider: str = "auto") -> Kernel:
    """Holt oder erstellt Kernel für Session"""
    if session_id not in kernels or kernels[session_id].provider_name != provider:
        kernel = Kernel(provider=provider)
        # WICHTIG: Skills laden!
        kernel.load_skills()
        logger.info(f"Kernel erstellt für Session {session_id}: {kernel.provider_name}, {len(kernel.manager.loaded_tools)} Skills")
        kernels[session_id] = kernel
    return kernels[session_id]


@app.route('/')
def index():
    """Haupt-Chat-Interface"""
    # Erstelle Session ID falls nicht vorhanden
    if 'session_id' not in session:
        session['session_id'] = secrets.token_hex(8)
    
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat-Endpoint"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        provider = data.get('provider', 'auto')
        
        if not message:
            return jsonify({'error': 'Keine Nachricht'}), 400
        
        # Session ID
        session_id = session.get('session_id', secrets.token_hex(8))
        session['session_id'] = session_id
        
        # Kernel holen
        kernel = get_kernel(session_id, provider)
        
        # 🚀 ALLES AN DEN KERNEL DELEGIEREN!
        # Der Kernel übernimmt Intent-Erkennung, Prompt-Bau, Skill-Ausführung & LLM-Aufruf.
        result = kernel.chat(message)
        
        # Das Ergebnis-Dict vom Kernel direkt an das Frontend senden
        return jsonify({
            'response': result.get('response', '(keine Antwort)'),
            'intent': result.get('intent', 'UNKNOWN'),
            'provider': kernel.provider_name,
            'thought': result.get('thought'),
            'skill': result.get('skill'),
            'error': result.get('error', False)
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Liste verfügbarer Provider"""
    claude_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    
    providers = {
        'claude': {
            'name': 'Claude (Anthropic)',
            'available': bool(claude_key),
            'model': 'claude-sonnet-4-20250514'
        },
        'gpt': {
            'name': 'ChatGPT (OpenAI)',
            'available': bool(openai_key),
            'model': 'gpt-4o'
        },
        'gemini': {
            'name': 'Gemini (Google)',
            'available': bool(google_key),
            'model': 'gemini-2.0-flash-exp'
        },
        'ollama': {
            'name': 'Ollama (Lokal)',
            'available': True,
            'model': 'qwen2.5:7b'
        }
    }
    
    return jsonify(providers)


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Lösche Chat-Historie"""
    try:
        session_id = session.get('session_id')
        if session_id and session_id in kernels:
            kernels[session_id].chat_history.clear()
            kernels[session_id].recent_errors.clear()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Clear error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Hole System-Statistiken"""
    try:
        session_id = session.get('session_id')
        kernel = kernels.get(session_id)
        
        if kernel:
            skills_list = list(kernel.manager.loaded_tools.keys())
            return jsonify({
                'provider': kernel.provider_name,
                'skills': len(kernel.manager.loaded_tools),
                'skills_list': sorted(skills_list),  # Liste aller Skills
                'history': len(kernel.chat_history),
                'state': kernel.state.name  # GEFIXED: state statt agent_state
            })
        
        return jsonify({
            'provider': 'none',
            'skills': 0,
            'skills_list': [],
            'history': 0,
            'state': 'IDLE'
        })
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/debug/skills', methods=['GET'])
def debug_skills():
    """Debug: Zeige alle geladenen Skills"""
    try:
        session_id = session.get('session_id')
        kernel = kernels.get(session_id)
        
        if kernel:
            skills = {}
            for name, func in kernel.manager.loaded_tools.items():
                skills[name] = {
                    'name': name,
                    'doc': func.__doc__ or 'Keine Beschreibung',
                    'file': func.__code__.co_filename if hasattr(func, '__code__') else 'unknown'
                }
            
            return jsonify({
                'total': len(skills),
                'skills': skills,
                'skills_directory': os.path.abspath('skills')
            })
        
        return jsonify({'error': 'Kein Kernel gefunden'}), 404
    except Exception as e:
        logger.error(f"Debug error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/goal', methods=['POST'])
def run_goal():
    """
    Autonomy Loop Endpoint.
    Startet einen vollständigen Goal→Plan→Execute→Evaluate-Zyklus.
    POST body: { "goal": "Erstelle eine Python-Datei mit den ersten 10 Primzahlen" }
    """
    try:
        data    = request.json
        goal    = data.get('goal', '').strip()
        provider = data.get('provider', 'auto')

        if not goal:
            return jsonify({'error': 'Kein Ziel angegeben'}), 400

        session_id = session.get('session_id', secrets.token_hex(8))
        session['session_id'] = session_id
        kernel = get_kernel(session_id, provider)

        logger.info(f"Autonomy Loop gestartet – Ziel: {goal}")

        loop = AutonomyLoop(kernel, max_iterations=10, verbose=False)
        goal_session = loop.run(goal)

        # Ergebnis in Chat-History übernehmen
        kernel.chat_history.append({'role': 'user',      'content': f"[Autonomy Loop] {goal}"})
        kernel.chat_history.append({'role': 'assistant', 'content': goal_session.final_summary or ""})

        return jsonify({
            'status':      goal_session.status.value,
            'goal':        goal_session.goal,
            'summary':     goal_session.final_summary,
            'iterations':  goal_session.iteration,
            'steps_total': len(goal_session.plan),
            'steps_done':  sum(1 for s in goal_session.plan
                               if s.status.value == 'done'),
            'history':     goal_session.history,
            'provider':    kernel.provider_name,
        })

    except Exception as e:
        logger.error(f"Goal endpoint error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/goal/status', methods=['GET'])
def goal_status():
    """Gibt den aktuellen Loop-Status zurück (für Polling im Frontend)."""
    try:
        session_id = session.get('session_id')
        kernel = kernels.get(session_id)
        if kernel and hasattr(kernel, 'autonomy_loop'):
            return jsonify(kernel.autonomy_loop.get_status_dict())
        return jsonify({'status': 'idle', 'goal': None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ─── Neue Endpoints: Reload, Audio-Upload, Datei-Upload ───────

@app.route('/api/reload', methods=['POST'])
def reload_skills():
    """Skills neu laden"""
    try:
        session_id = session.get('session_id')
        kernel = kernels.get(session_id)
        if not kernel:
            return jsonify({'error': 'Kein aktiver Kernel'}), 400
        count = kernel.load_skills()
        skills = list(kernel.manager.loaded_tools.keys())
        logger.info(f"Skills neu geladen: {count}")
        return jsonify({'success': True, 'count': count, 'skills': skills})
    except Exception as e:
        logger.error(f"Reload error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/audio', methods=['POST'])
def upload_audio():
    """Sprachnachricht transkribieren und an Kernel senden"""
    import tempfile, os, warnings
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei'}), 400
        file = request.files['file']
        suffix = os.path.splitext(file.filename)[1] or '.ogg'

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        # Transkribieren
        transcript = ""
        try:
            import whisper
            warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
            warnings.filterwarnings("ignore", category=UserWarning, module="torch")
            model = whisper.load_model("base", device="cpu")
            result = model.transcribe(tmp_path, language="de")
            transcript = result["text"].strip()
        except ImportError:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                import openai
                client = openai.OpenAI(api_key=openai_key)
                with open(tmp_path, "rb") as f:
                    result = client.audio.transcriptions.create(
                        model="whisper-1", file=f, language="de"
                    )
                transcript = result.text.strip()
            else:
                return jsonify({'error': 'Whisper nicht verfügbar – pip install openai-whisper'}), 500
        finally:
            try: os.unlink(tmp_path)
            except: pass

        if not transcript:
            return jsonify({'error': 'Transkription leer'}), 400

        # An Kernel senden
        session_id = session.get('session_id', secrets.token_hex(8))
        session['session_id'] = session_id
        kernel = get_kernel(session_id)
        result = kernel.chat(f"[Sprachnachricht transkribiert]: {transcript}")

        return jsonify({
            'transcript': transcript,
            'response': result.get('response', ''),
            'intent': result.get('intent', 'UNKNOWN'),
            'skill': result.get('skill'),
            'thought': result.get('thought'),
            'provider': kernel.provider_name
        })

    except Exception as e:
        logger.error(f"Audio upload error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload/file', methods=['POST'])
def upload_file():
    """Datei hochladen, Inhalt extrahieren, an Kernel senden"""
    import tempfile, os
    from pathlib import Path
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Keine Datei'}), 400
        file = request.files['file']
        filename = file.filename or 'upload'
        caption = request.form.get('caption', '').strip()
        suffix = Path(filename).suffix.lower()

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            content = _extract_file_content(tmp_path, filename)
        finally:
            try: os.unlink(tmp_path)
            except: pass

        if content.startswith('[') and 'nicht verfügbar' in content:
            return jsonify({'error': content}), 400

        # An Kernel senden
        session_id = session.get('session_id', secrets.token_hex(8))
        session['session_id'] = session_id
        kernel = get_kernel(session_id)

        msg = (f"[Datei: {filename}]\n{content}\n\nAufgabe: {caption}"
               if caption else f"[Datei: {filename}]\nBitte analysiere:\n\n{content}")

        result = kernel.chat(msg)

        return jsonify({
            'filename': filename,
            'content_preview': content[:200] + '...' if len(content) > 200 else content,
            'response': result.get('response', ''),
            'intent': result.get('intent', 'UNKNOWN'),
            'skill': result.get('skill'),
            'thought': result.get('thought'),
            'provider': kernel.provider_name
        })

    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _extract_file_content(file_path: str, filename: str) -> str:
    """Textextraktion aus PDF, Word, Text und Codedateien."""
    from pathlib import Path
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = '\n'.join(page.extract_text() or '' for page in reader.pages)
                return text[:8000] if text.strip() else '[PDF enthält keinen lesbaren Text]'
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                    return text[:8000]
                except ImportError:
                    return '[PDF-Extraktion nicht verfügbar – pip install PyPDF2]'
        elif suffix in ('.docx', '.doc'):
            try:
                import docx
                doc = docx.Document(file_path)
                return '\n'.join(p.text for p in doc.paragraphs)[:8000]
            except ImportError:
                return '[Word-Extraktion nicht verfügbar – pip install python-docx]'
        elif suffix in ('.txt', '.md', '.py', '.js', '.ts', '.json', '.csv',
                        '.xml', '.html', '.yaml', '.yml', '.sh', '.ini'):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read(8000)
        else:
            return f"[Dateityp '{suffix}' nicht direkt lesbar – unterstützt: PDF, DOCX, TXT, MD, PY, JSON, CSV]"
    except Exception as e:
        return f'[Extraktion fehlgeschlagen: {e}]'


if __name__ == '__main__':
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   Offenes Leuchten v5.0 - Web Edition               ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()
    
    # Startup Checks
    print("🔍 Startup Checks...")
    
    # Check 1: Skills Verzeichnis
    skills_dir = os.path.abspath('skills')
    if os.path.exists(skills_dir):
        skill_count = len([f for f in os.listdir(skills_dir) if f.endswith('.py') and f != '__init__.py'])
        print(f"✅ Skills Verzeichnis: {skills_dir} ({skill_count} Skills)")
    else:
        print(f"⚠️  Skills Verzeichnis nicht gefunden: {skills_dir}")
        print(f"   Starte trotzdem, aber Skills werden fehlen!")
    
    # Check 2: Dependencies
    required_modules = ['skill_manager', 'agent_state', 'kernel']
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ Modul: {module}")
        except ImportError as e:
            print(f"❌ Modul fehlt: {module} - {e}")
            missing_modules.append(module)
    
    if missing_modules:
        print()
        print(f"⚠️  WARNUNG: {len(missing_modules)} Module fehlen!")
        print(f"   Stelle sicher dass du im richtigen Verzeichnis bist")
        print()
    
    # Check 3: Working Directory
    cwd = os.getcwd()
    print(f"📁 Working Directory: {cwd}")
    
    print()
    print("🌐 Server startet...")
    print()
    
    # Finde lokale IP
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "unknown"
    
    print("Lokal:              http://localhost:5000")
    if local_ip != "unknown":
        print(f"Im Netzwerk:        http://{local_ip}:5000")
    print()
    print("Zum Beenden: Ctrl+C")
    print()
    
    # Starte Server (erreichbar im Netzwerk)
    app.run(
        host='0.0.0.0',  # Erreichbar im Netzwerk
        port=5000,
        debug=False,
        threaded=True
    )