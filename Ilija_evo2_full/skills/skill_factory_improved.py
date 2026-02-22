"""
Verbesserte Skill Factory mit besserer Code-Validierung und Templates
"""
import os
import ast
import sys
import re
from typing import Optional

# Pfad-Hack für Registry
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from skill_registry import PROTECTED_SKILLS
except ImportError:
    PROTECTED_SKILLS = []

SKILLS_DIR = "skills"


def validate_python_code(code: str) -> tuple[bool, Optional[str]]:
    """
    Validiert Python-Code auf Syntax-Fehler
    Returns: (is_valid, error_message)
    """
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        error_msg = f"Syntax-Fehler (Zeile {e.lineno}): {e.msg}"
        return False, error_msg
    except Exception as e:
        return False, str(e)


def sanitize_skill_name(skill_name: str) -> str:
    """
    Bereinigt den Skill-Namen für sichere Dateinamen
    """
    # Erlaube nur Buchstaben, Zahlen und Unterstriche
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', skill_name)
    # Stelle sicher, dass es mit einem Buchstaben beginnt
    if sanitized and not sanitized[0].isalpha():
        sanitized = 'skill_' + sanitized
    return sanitized.lower()


def extract_function_names(code: str) -> list[str]:
    """
    Extrahiert alle Funktionsnamen aus dem Code
    """
    try:
        tree = ast.parse(code)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
    except:
        return []


# ── Versionierung + Validierung ───────────────────────────────
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from skill_versioning import get_versioning
    from skill_validator  import get_validator
    _versioning_available = True
except ImportError:
    _versioning_available = False


def skill_erstellen(skill_name: str, beschreibung: str, code: str) -> str:
    """
    Erstellt einen neuen Skill mit verbesserter Validierung und Fehlerbehandlung.
    
    Args:
        skill_name: Name des Skills (wird zu gültigem Python-Identifier normalisiert)
        beschreibung: Beschreibung der Skill-Funktionalität
        code: Python-Code der Hauptfunktion
    
    Returns:
        Status-Nachricht (Erfolg oder Fehler)
    """
    # 1. Name validieren und bereinigen
    original_name = skill_name
    skill_name = sanitize_skill_name(skill_name)
    
    if not skill_name:
        return "❌ FEHLER: Ungültiger Skill-Name. Nutze nur Buchstaben, Zahlen und Unterstriche."
    
    # 2. Schutz-Check
    if skill_name in PROTECTED_SKILLS:
        return f"❌ ABGELEHNT: '{skill_name}' ist ein geschützter System-Skill."
    
    # 3. Code-Validierung
    is_valid, error_msg = validate_python_code(code)
    if not is_valid:
        return f"❌ SYNTAX-FEHLER im generierten Code:\n{error_msg}\n\nBitte korrigiere den Code und versuche es erneut."
    
    # 4. Prüfe ob die Hauptfunktion definiert ist
    functions = extract_function_names(code)
    if skill_name not in functions:
        # Versuche die erste definierte Funktion zu finden
        if functions:
            return f"⚠️  WARNUNG: Die Hauptfunktion sollte '{skill_name}' heißen, aber gefunden wurde: {functions}. Bitte benenne die Funktion korrekt."
        else:
            return "❌ FEHLER: Keine Funktion im Code gefunden. Der Code muss mindestens eine Funktion definieren."
    
    # 5. Datei erstellen
    path = os.path.join(SKILLS_DIR, f"{skill_name}.py")
    
    # Template für die Skill-Datei
    file_content = f'''"""
{beschreibung}

Auto-generiert durch skill_erstellen
Skill-Name: {skill_name}
"""

# Standard-Imports für Skills
import random
import time
import math
import datetime
import os
import subprocess
import json
from typing import Optional, List, Dict, Any

# Haupt-Skill-Code
{code}

# Registrierung für den SkillManager
AVAILABLE_SKILLS = [{skill_name}]
'''
    
    # 6. Finale Validierung des kompletten Files
    is_valid, error_msg = validate_python_code(file_content)
    if not is_valid:
        return f"❌ FEHLER beim Erstellen der Datei:\n{error_msg}"
    
    # 7. Schreibe die Datei
    try:
        # Erstelle Backup falls Datei bereits existiert
        if os.path.exists(path):
            backup_path = path + ".backup"
            import shutil
            shutil.copy2(path, backup_path)
            print(f"   ℹ️  Backup erstellt: {backup_path}")
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(file_content)
        
        success_msg = f"✅ SUCCESS_CREATED: Skill '{skill_name}' wurde erfolgreich erstellt."
        if original_name != skill_name:
            success_msg += f"\n   (Name normalisiert von '{original_name}' zu '{skill_name}')"
        success_msg += "\n   RELOAD REQUIRED - Der Skill wird beim nächsten Reload verfügbar sein."

        # ── Validation + Versioning ───────────────────────────
        if _versioning_available:
            try:
                # Isolierter Testlauf
                validator = get_validator(SKILLS_DIR)
                val_result = validator.validate(skill_name)
                if not val_result["passed"]:
                    success_msg += f"\n   ⚠️  Validierung: {val_result['summary']}"
                else:
                    success_msg += f"\n   {val_result['summary']}"

                # Git-Commit
                versioning = get_versioning()
                ver_result = versioning.backup(skill_name)
                success_msg += f"\n   📦 {ver_result}"
            except Exception as e:
                success_msg += f"\n   (Versionierung/Validierung: {e})"

        return success_msg
        
    except PermissionError:
        return f"❌ FEHLER: Keine Schreibrechte für {path}"
    except Exception as e:
        return f"❌ Schreibfehler: {e}"


# Registrierung
AVAILABLE_SKILLS = [skill_erstellen]
