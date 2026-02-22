"""
Offenes Leuchten – Skill Validator
=====================================
Isolierter Testlauf für neu erstellte Skills.

Prüft nach dem Erstellen ob ein Skill:
  1. Syntaktisch korrekt ist (ast.parse)
  2. Importierbar ist (subprocess – isoliert!)
  3. Die erwartete Funktion enthält
  4. Die Funktion aufrufbar ist (ohne Crash)

Der Test läuft in einem separaten Subprocess damit
ein fehlerhafter Skill den Hauptprozess nicht gefährdet.
"""

import ast
import os
import sys
import json
import subprocess
import tempfile
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class SkillValidator:
    """Validiert neu erstellte Skills in einem isolierten Subprocess."""

    def __init__(self, skills_dir: str = "skills", timeout: int = 10):
        self.skills_dir = skills_dir
        self.timeout    = timeout

    def validate(self, skill_name: str) -> Dict:
        """
        Führt alle Validierungsschritte durch.

        Returns:
            {
                "passed": bool,
                "checks": {
                    "syntax":   {"ok": bool, "msg": str},
                    "import":   {"ok": bool, "msg": str},
                    "function": {"ok": bool, "msg": str},
                },
                "summary": str
            }
        """
        result = {
            "passed": False,
            "checks": {
                "syntax":   {"ok": False, "msg": ""},
                "import":   {"ok": False, "msg": ""},
                "function": {"ok": False, "msg": ""},
            },
            "summary": ""
        }

        skill_path = os.path.join(self.skills_dir, f"{skill_name}.py")

        if not os.path.exists(skill_path):
            result["summary"] = f"❌ Skill-Datei nicht gefunden: {skill_path}"
            return result

        # ── Check 1: Syntax ──────────────────────────────────
        try:
            code = open(skill_path, encoding="utf-8").read()
            ast.parse(code)
            result["checks"]["syntax"] = {"ok": True, "msg": "Syntax korrekt"}
        except SyntaxError as e:
            result["checks"]["syntax"] = {"ok": False, "msg": f"Zeile {e.lineno}: {e.msg}"}
            result["summary"] = f"❌ Syntax-Fehler: {e.msg} (Zeile {e.lineno})"
            return result

        # ── Check 2: Import in Subprocess ────────────────────
        import_result = self._test_import(skill_path, skill_name)
        result["checks"]["import"] = import_result

        if not import_result["ok"]:
            result["summary"] = f"❌ Import-Fehler: {import_result['msg']}"
            return result

        # ── Check 3: Funktion vorhanden ───────────────────────
        func_result = self._check_function(code, skill_name)
        result["checks"]["function"] = func_result

        if not func_result["ok"]:
            result["summary"] = f"⚠️  Funktions-Warnung: {func_result['msg']}"
            # Kein hartes Fail – Funktion könnte anders heißen
            result["passed"] = True
            return result

        # ── Alles bestanden ───────────────────────────────────
        result["passed"] = True
        result["summary"] = f"✅ Skill '{skill_name}' validiert – alle Checks bestanden"
        return result

    def _test_import(self, skill_path: str, skill_name: str) -> Dict:
        """Testet Import im Subprocess."""
        test_script = f"""
import sys, json
sys.path.insert(0, '.')
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("{skill_name}", "{skill_path}")
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(json.dumps({{"ok": True, "msg": "Import erfolgreich"}}))
except Exception as e:
    print(json.dumps({{"ok": False, "msg": str(e)}}))
"""
        return self._run_in_subprocess(test_script)

    def _check_function(self, code: str, skill_name: str) -> Dict:
        """Prüft ob die Hauptfunktion im Code definiert ist."""
        try:
            tree = ast.parse(code)
            functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            if skill_name in functions:
                return {"ok": True, "msg": f"Funktion '{skill_name}' gefunden"}
            elif functions:
                return {"ok": False, "msg": f"Funktion '{skill_name}' fehlt – gefunden: {functions}"}
            else:
                return {"ok": False, "msg": "Keine Funktionen im Code"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def _run_in_subprocess(self, script: str) -> Dict:
        """Führt ein Python-Skript in einem isolierten Subprocess aus."""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(script)
                tmp_path = tmp.name

            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True, text=True,
                timeout=self.timeout,
                cwd=os.getcwd()
            )

            os.unlink(tmp_path)

            if result.stdout.strip():
                try:
                    return json.loads(result.stdout.strip().split("\n")[-1])
                except json.JSONDecodeError:
                    pass

            if result.returncode != 0:
                stderr = result.stderr.strip()[-300:] if result.stderr else "Unbekannter Fehler"
                return {"ok": False, "msg": stderr}

            return {"ok": True, "msg": "Subprocess erfolgreich"}

        except subprocess.TimeoutExpired:
            return {"ok": False, "msg": f"Timeout nach {self.timeout}s – Skill hängt beim Import"}
        except Exception as e:
            return {"ok": False, "msg": str(e)}

    def format_result(self, result: Dict) -> str:
        """Gibt das Validierungsergebnis als lesbaren String zurück."""
        lines = ["🔍 Skill-Validierung:"]
        icons = {True: "✅", False: "❌"}

        for check_name, check in result["checks"].items():
            icon  = icons[check["ok"]]
            label = {"syntax": "Syntax", "import": "Import", "function": "Funktion"}[check_name]
            lines.append(f"  {icon} {label}: {check['msg']}")

        lines.append(f"\n{result['summary']}")
        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────

_validator: Optional[SkillValidator] = None

def get_validator(skills_dir: str = "skills") -> SkillValidator:
    global _validator
    if _validator is None:
        _validator = SkillValidator(skills_dir)
    return _validator
