"""
Skill Manager – verwaltet das dynamische Laden und Ausführen von Skills.
(Zusammengeführte Version aus skill_manager.py und skill_manager_improved.py)
"""
import os
import importlib.util
import inspect
import sys
import logging
from typing import Dict, List, Callable, Optional

logger = logging.getLogger(__name__)


class SkillManager:
    """Verwaltet das dynamische Laden und Ausführen von Skills."""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self.loaded_tools: Dict[str, Callable] = {}
        self.tool_definitions: List[str] = []
        self.skill_metadata: Dict[str, Dict] = {}

    def load_skills(self) -> int:
        """
        Lädt alle Python-Module aus dem skills/-Ordner neu.
        Returns: Anzahl der erfolgreich registrierten Skill-Funktionen.
        """
        self.loaded_tools.clear()
        self.tool_definitions.clear()
        self.skill_metadata.clear()

        if not os.path.exists(self.skills_dir):
            try:
                os.makedirs(self.skills_dir)
                logger.info(f"Skills-Verzeichnis erstellt: {self.skills_dir}")
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Skills-Verzeichnisses: {e}")
                return 0

        for filename in sorted(os.listdir(self.skills_dir)):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    self._load_module_from_file(filename)
                except Exception as e:
                    logger.error(f"Fehler beim Laden von {filename}: {e}")

        logger.info(f"Skills geladen: {len(self.loaded_tools)}")
        return len(self.loaded_tools)

    def _load_module_from_file(self, filename: str) -> bool:
        """Lädt ein einzelnes Skill-Modul. Returns True bei Erfolg."""
        module_name = filename[:-3]
        file_path = os.path.join(self.skills_dir, filename)

        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                logger.warning(f"Keine gültige Spezifikation für {filename}")
                return False

            module = importlib.util.module_from_spec(spec)

            # Altes Modul entfernen für sauberes Reload
            if module_name in sys.modules:
                del sys.modules[module_name]

            sys.modules[module_name] = module

            # Skills können andere Skills per Name aufrufen
            # (z.B. webseiten_inhalt_lesen() in einem neuen Skill)
            for skill_name, skill_func in self.loaded_tools.items():
                setattr(module, skill_name, skill_func)

            spec.loader.exec_module(module)

            if not hasattr(module, "AVAILABLE_SKILLS"):
                logger.warning(f"⚠️  {filename} hat keine 'AVAILABLE_SKILLS' Liste.")
                return False

            skills_in_module = 0
            for func in module.AVAILABLE_SKILLS:
                if callable(func) and self._register_tool(func, module_name):
                    skills_in_module += 1

            logger.info(f"✓ {filename}: {skills_in_module} Skill(s) geladen")
            return skills_in_module > 0

        except SyntaxError as e:
            logger.error(f"Syntax-Fehler in {filename}: {e}")
            print(f"   ❌ Syntax-Fehler in {filename} (Zeile {e.lineno}): {e.msg}")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Laden von {filename}: {e}")
            print(f"   ❌ Fehler in {filename}: {e}")
            return False

    def _register_tool(self, func: Callable, module_name: str) -> bool:
        """Registriert eine Skill-Funktion. Returns True bei Erfolg."""
        try:
            name = func.__name__
            if name in self.loaded_tools:
                logger.warning(f"Skill '{name}' wird überschrieben")

            doc = inspect.getdoc(func) or "Keine Beschreibung verfügbar."
            sig = inspect.signature(func)

            params_info = []
            for param_name, param in sig.parameters.items():
                param_type = (
                    param.annotation
                    if param.annotation != inspect.Parameter.empty
                    else "Any"
                )
                param_default = (
                    f"={param.default}"
                    if param.default != inspect.Parameter.empty
                    else ""
                )
                params_info.append(f"{param_name}: {param_type}{param_default}")

            params_str = ", ".join(params_info)
            definition = (
                f"- Skill: {name}({params_str})\n  Info: {doc}\n  Modul: {module_name}"
            )

            self.loaded_tools[name] = func
            self.tool_definitions.append(definition)
            self.skill_metadata[name] = {
                "module": module_name,
                "doc": doc,
                "signature": str(sig),
                "params": list(sig.parameters.keys()),
            }
            return True
        except Exception as e:
            logger.error(f"Fehler beim Registrieren von {func.__name__}: {e}")
            return False

    def get_system_prompt_addition(self) -> str:
        """System-Prompt-Block mit allen verfügbaren Skills."""
        if not self.tool_definitions:
            return "\nKeine Skills verfügbar. Nutze 'skill_erstellen' um neue Skills zu erstellen."
        return "\n" + "\n".join(self.tool_definitions)

    def execute_skill(self, skill_name: str, params: Dict) -> str:
        """Führt einen Skill mit den gegebenen Parametern aus."""
        if skill_name not in self.loaded_tools:
            error_msg = f"Skill '{skill_name}' nicht gefunden."
            logger.error(error_msg)
            return error_msg

        import time
        start_time = time.time()

        try:
            func = self.loaded_tools[skill_name]
            sig = inspect.signature(func)

            # Überschüssige Parameter entfernen
            valid_params = {k: v for k, v in params.items() if k in sig.parameters}

            # Fehlende Pflicht-Parameter prüfen
            missing_params = [
                p
                for p, param in sig.parameters.items()
                if param.default == inspect.Parameter.empty and p not in valid_params
            ]
            if missing_params:
                return f"Fehler: Fehlende Parameter: {', '.join(missing_params)}"

            logger.info(f"Führe Skill aus: {skill_name} mit Parametern: {valid_params}")
            result = func(**valid_params)
            duration = time.time() - start_time

            # ── Scoring: Erfolg ──────────────────────────────
            try:
                from skill_scoring import get_scoring
                get_scoring().record_success(skill_name, duration)
            except Exception:
                pass

            return result if result is not None else "✓ Ausgeführt (kein Rückgabewert)"

        except TypeError as e:
            duration = time.time() - start_time
            error_msg = f"Parameter-Fehler bei '{skill_name}': {str(e)}"
            logger.error(error_msg)
            try:
                from skill_scoring import get_scoring
                get_scoring().record_failure(skill_name, str(e), duration)
            except Exception:
                pass
            return error_msg
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Fehler beim Ausführen von '{skill_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            try:
                from skill_scoring import get_scoring
                get_scoring().record_failure(skill_name, str(e), duration)
            except Exception:
                pass
            return error_msg

    def get_skill_info(self, skill_name: str) -> Optional[Dict]:
        """Gibt Metadaten zu einem Skill zurück."""
        return self.skill_metadata.get(skill_name)

    def list_skills(self) -> List[str]:
        """Gibt eine Liste aller geladenen Skill-Namen zurück."""
        return list(self.loaded_tools.keys())

    def skill_exists(self, skill_name: str) -> bool:
        """Prüft ob ein Skill geladen ist."""
        return skill_name in self.loaded_tools
