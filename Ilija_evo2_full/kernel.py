#!/usr/bin/env python3
"""
Offenes Leuchten – Kernel v5.0
Ersetzt: main_v4_cloud.py, main_improved_v3_3_selfaware.py, main_v4_2_production.py

Architektur:
  providers.py   → LLM-Provider (Claude, GPT, Gemini, Ollama)
  skill_manager  → Dynamisches Laden/Ausführen von Skills
  skill_registry → Status-Tracking für Skills
  kernel.py      → Haupt-Loop (dieses File)
"""

import json
import logging
import os
import re
import sys
import time

# ChromaDB Telemetrie deaktivieren (verhindert PostHog-Spam im Terminal)
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")
from collections import deque
from typing import Dict, Optional, Tuple

# .env automatisch laden
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from agent_state    import AgentState
from providers      import LLMProvider, ProviderError, RateLimitError, select_provider
from skill_manager  import SkillManager
from skill_registry import PROTECTED_SKILLS, SkillStatus, get_skill_status

# ------------------------------------------------------------------ #
# Logging (einmalig konfigurieren)                                     #
# ------------------------------------------------------------------ #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
    handlers=[
        logging.FileHandler("offenes_leuchten.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Terminal-Farben                                                      #
# ------------------------------------------------------------------ #

class C:
    GREEN   = "\033[92m"
    BLUE    = "\033[94m"
    YELLOW  = "\033[93m"
    RED     = "\033[91m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

    @staticmethod
    def wrap(color: str, text: str) -> str:
        return f"{color}{text}{C.RESET}"


# ------------------------------------------------------------------ #
# Intent-Erkennung                                                     #
# ------------------------------------------------------------------ #

class IntentDetector:
    """Klassifiziert Nutzer-Eingaben ohne LLM-Aufruf."""

    _SELF_KNOWLEDGE = ["wer bist du", "dein name", "wie heißt du", "was bist du",
                       "was kannst du", "offenes leuchten", "was ist das hier",
                       "dieses projekt", "um was geht es", "who are you"]

    _SKILL_WORDS    = ["speichere", "speichern", "erstelle", "create", "generiere",
                       "nutze", "verwende", "führe aus", "run", "suche", "finde",
                       "berechne", "calculate", "skill"]

    _USER_WORDS     = ["mein", "ich mag", "was weißt du über mich", "what do i like"]

    _SMALLTALK      = ["hallo", "hi", "hey", "servus", "moin", "danke", "ok", "okay",
                       "ja", "nein", "yes", "no", "cool", "super", "gut", "aha"]

    @classmethod
    def detect(cls, text: str) -> str:
        t = text.lower().strip()

        if any(p in t for p in cls._SELF_KNOWLEDGE):
            return "SELF_KNOWLEDGE"

        if len(t) < 12 and any(p in t for p in cls._SMALLTALK):
            return "SMALLTALK"

        if any(k in t for k in cls._SKILL_WORDS):
            return "TASK"

        if any(k in t for k in cls._USER_WORDS):
            return "USER_QUESTION"

        if "?" in t and len(t) < 25:
            return "SMALLTALK"

        return "TASK" if len(t) > 25 else "SMALLTALK"


# ------------------------------------------------------------------ #
# Kernel                                                               #
# ------------------------------------------------------------------ #

class Kernel:
    """
    Herzstück von Offenes Leuchten.
    Verwaltet den Agent-Zustand, kommuniziert mit dem LLM und führt Skills aus.
    """

    IDENTITY = {
        "name":        "Ilija",
        "role":        "Autonomer KI-Agent",
        "project":     "Offenes Leuchten",
        "description": (
            "Ein selbst-erweiterndes KI-Agent-System mit Langzeitgedächtnis, "
            "das neue Fähigkeiten (Skills) zur Laufzeit erstellen kann"
        ),
        "capabilities": [
            "Selbst-Entwicklung (neue Skills zur Laufzeit)",
            "Langzeitgedächtnis (Fakten speichern & abrufen)",
            "Problemlösung & Code-Generierung",
            "Unterstützt Cloud-APIs und lokale Modelle",
        ],
    }

    def __init__(self, provider: str = "auto", auto_load_skills: bool = True) -> None:
        self.provider_name, self.provider = select_provider(provider)
        self.manager             = SkillManager()
        self.state               = AgentState.IDLE
        self.chat_history:       list = []
        self.last_user_input     = ""
        self.max_history         = 10
        self.consecutive_errors  = 0
        self.max_errors          = 3
        self.recent_errors: deque = deque(maxlen=5)
        self.loop_threshold      = 3
        self.reload_counter      = 0

        if auto_load_skills:
            self.load_skills()

    # ---------------------------------------------------------------- #
    # Skills                                                             #
    # ---------------------------------------------------------------- #

    def load_skills(self) -> int:
        try:
            n = self.manager.load_skills()
            logger.info(f"Skills geladen: {n}")
            return n
        except Exception as e:
            logger.error(f"load_skills Fehler: {e}")
            return 0

    # ---------------------------------------------------------------- #
    # Self-Knowledge (kein LLM nötig)                                   #
    # ---------------------------------------------------------------- #

    def self_knowledge_reply(self, text: str) -> str:
        t = text.lower()
        id_ = self.IDENTITY
        if "offenes leuchten" in t or "projekt" in t or "was ist das" in t:
            return f"'{id_['project']}' ist {id_['description']}. Ich bin der Agent in diesem Projekt."
        if "name" in t or "heißt" in t or "wer bist" in t:
            return f"Ich bin {id_['name']}, ein {id_['role']} im Projekt '{id_['project']}'."
        if "was kannst" in t or "what can" in t:
            return "Ich kann: " + ", ".join(id_["capabilities"])
        if "was bist" in t or "what are" in t:
            return f"Ich bin {id_['name']}, ein {id_['role']}. Ich kann mich selbst erweitern und Fakten langfristig speichern."
        return f"Ich bin {id_['name']}, dein KI-Assistent. Wie kann ich dir helfen?"

    # ---------------------------------------------------------------- #
    # System-Prompt                                                      #
    # ---------------------------------------------------------------- #

    def build_system_prompt(self, intent: str) -> str:
        name   = self.IDENTITY["name"]
        skills = self.manager.get_system_prompt_addition()

        if intent == "SMALLTALK":
            return f'Du bist {name}. Antworte freundlich und kurz. Format: {{"antwort": "..."}}'

        if intent == "USER_QUESTION":
            return (
                f"Du bist {name}. Beantworte Fragen über den User anhand des Gedächtnisses.\n\n"
                f"Für Gedächtnis-Suche:\n"
                f'  {{"skill": "wissen_abrufen", "params": {{"suchbegriff": "keyword"}}, "gedanke": "..."}}\n\n'
                f"Für direkte Antwort:\n"
                f'  {{"antwort": "..."}}\n\n'
                f"VERFÜGBARE SKILLS:\n{skills}"
            )

        # TASK
        return (
            f"Du bist {name}. Nutze vorhandene Skills oder erstelle neue.\n\n"
            f"FORMAT (immer JSON):\n"
            f"  Skill nutzen:   {{\"skill\": \"name\", \"params\": {{...}}, \"gedanke\": \"...\"}}\n"
            f"  Skill erstellen:{{\"skill\": \"skill_erstellen\", \"params\": {{\"skill_name\": \"...\", \"code\": \"...\"}}, \"gedanke\": \"...\"}}\n"
            f"  Direkte Antwort:{{\"antwort\": \"...\"}}\n\n"
            f"WICHTIG: Prüfe zuerst ob ein passender Skill existiert!\n\n"
            f"VERFÜGBARE SKILLS:\n{skills}"
        )

    # ---------------------------------------------------------------- #
    # Response-Parsing                                                   #
    # ---------------------------------------------------------------- #

    def parse_response(self, text: str) -> Optional[Dict]:
        # Markdown-Code-Blöcke bereinigen
        text = re.sub(r"^```(?:json)?\s*", "", text.strip())
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None

    def extract_skill_call(self, decision: Dict) -> Tuple[Optional[str], Dict]:
        """Extrahiert Skill-Name und Parameter aus dem geparsten LLM-Output."""
        skill  = decision.get("skill")
        params = decision.get("params", {})

        if not skill:
            # Fallback: Suche nach Skill-Namen als Top-Level-Key
            for key in decision:
                if key in self.manager.loaded_tools or key == "skill_erstellen":
                    skill  = key
                    params = decision[key] if isinstance(decision[key], dict) else {}
                    break

        return skill, params

    # ---------------------------------------------------------------- #
    # Loop-Detection                                                     #
    # ---------------------------------------------------------------- #

    def is_looping(self, error_msg: str) -> bool:
        self.recent_errors.append(error_msg)
        recent = list(self.recent_errors)[-self.loop_threshold:]
        return len(recent) >= self.loop_threshold and len(set(recent)) == 1

    # ---------------------------------------------------------------- #
    # Skill-Ausführung                                                   #
    # ---------------------------------------------------------------- #

    def run_skill(self, skill_name: str, params: Dict, thought: str) -> bool:
        """
        Führt einen Skill aus.
        Gibt True zurück wenn die Hauptschleife fortgesetzt werden soll (continue).
        """
        print(C.wrap(C.YELLOW, f"💭 {thought}"))

        status = get_skill_status(skill_name, self.manager.loaded_tools)

        # Skill existiert überhaupt nicht
        if status == SkillStatus.NOT_PRESENT and skill_name != "skill_erstellen":
            err = f"Skill '{skill_name}' nicht vorhanden"
            if self.is_looping(err):
                print(C.wrap(C.RED, "🔁 Endlosschleife erkannt! Erzwinge skill_erstellen."))
                self.chat_history.append({"role": "system", "content": f"KRITISCH: Nutze skill_erstellen für '{skill_name}'!"})
                self.state = AgentState.IDLE
                return True
            print(C.wrap(C.RED, f"⛔ Skill '{skill_name}' fehlt"))
            self.chat_history.append({"role": "system", "content": f"FEHLER: '{skill_name}' existiert nicht. Nutze skill_erstellen!"})
            self.state = AgentState.SKILL_MISSING
            return True

        # Datei vorhanden aber noch nicht geladen
        if status == SkillStatus.FILE_EXISTS:
            print(C.wrap(C.CYAN, f"⚠️  '{skill_name}' nicht geladen – starte Reload…"))
            self.state = AgentState.SKILL_CREATED_NEEDS_RELOAD
            return True

        # Geschützte Skills dürfen nicht überschrieben werden
        if skill_name == "skill_erstellen":
            target = params.get("skill_name", "")
            if target in PROTECTED_SKILLS:
                print(C.wrap(C.RED, f"⛔ '{target}' ist geschützt und kann nicht überschrieben werden"))
                self.state = AgentState.ERROR
                return True

        # Skill ausführen
        if status == SkillStatus.LOADED or skill_name == "skill_erstellen":
            print(C.wrap(C.GREEN, f"▶  Führe '{skill_name}' aus…"))
            try:
                result = self.manager.execute_skill(skill_name, params)

                if "SUCCESS_CREATED" in str(result):
                    print(C.wrap(C.CYAN, "✨ Skill erstellt! Lade Skills neu…"))
                    self.state = AgentState.SKILL_CREATED_NEEDS_RELOAD
                    self.recent_errors.clear()
                    return True

                print(C.wrap(C.BLUE, f"📤 {result}"))
                self.chat_history.append({"role": "assistant", "content": f"Ergebnis: {result}"})
                self.state = AgentState.IDLE
                self.consecutive_errors = 0
                self.recent_errors.clear()
                return False

            except Exception as e:
                msg = f"Fehler bei '{skill_name}': {e}"
                logger.error(msg, exc_info=True)
                print(C.wrap(C.RED, f"❌ {msg}"))
                self.chat_history.append({"role": "system", "content": f"FEHLER: {msg}"})
                self.state = AgentState.ERROR
                self.consecutive_errors += 1
                return True

        return False

    # ---------------------------------------------------------------- #
    # Reload-Zyklus                                                      #
    # ---------------------------------------------------------------- #

    def _do_reload(self) -> None:
        print(C.wrap(C.CYAN, "🔄 Lade Skills neu…"))
        time.sleep(0.3)
        n = self.load_skills()
        self.reload_counter += 1
        self.state = AgentState.IDLE
        print(C.wrap(C.CYAN, f"✅ Reload #{self.reload_counter} abgeschlossen – {n} Skills verfügbar"))
        self.chat_history.append({"role": "system", "content": "Neuer Skill wurde geladen."})

    # ---------------------------------------------------------------- #
    # Chat-Schnittstelle (für web_server.py)                            #
    # ---------------------------------------------------------------- #

    def chat(self, user_message: str) -> Dict:
        """
        Verarbeitet eine Nachricht und gibt ein Ergebnis-Dict zurück.
        Wird von web_server.py genutzt.
        Rückgabe: {"response": str, "intent": str, "skill": str|None, "thought": str|None, "error": bool}
        """
        self.last_user_input = user_message
        self.chat_history.append({"role": "user", "content": user_message})

        intent = "TASK" if self.state == AgentState.SKILL_MISSING else IntentDetector.detect(user_message)

        if intent == "SELF_KNOWLEDGE":
            answer = self.self_knowledge_reply(user_message)
            self.chat_history.append({"role": "assistant", "content": answer})
            return {"response": answer, "intent": intent, "skill": None, "thought": None, "error": False}

        messages = [{"role": "system", "content": self.build_system_prompt(intent)}]
        messages += self.chat_history[-self.max_history:]

        force_json = intent in ("TASK", "USER_QUESTION")

        try:
            raw = self.provider.chat(messages, force_json=force_json)
        except Exception as e:
            return {"response": f"API-Fehler: {e}", "intent": intent, "skill": None, "thought": None, "error": True}

        if force_json or "{" in raw:
            decision = self.parse_response(raw)
            if not decision:
                return {"response": "Fehler: Ungültiges JSON vom LLM", "intent": intent, "skill": None, "thought": None, "error": True}

            if "antwort" in decision:
                answer = decision["antwort"]
                self.chat_history.append({"role": "assistant", "content": answer})
                return {"response": answer, "intent": intent, "skill": None, "thought": decision.get("gedanke"), "error": False}

            skill_name, params = self.extract_skill_call(decision)
            thought = decision.get("gedanke", "Ausführung")

            if skill_name:
                status = get_skill_status(skill_name, self.manager.loaded_tools)
                if status == SkillStatus.NOT_PRESENT and skill_name != "skill_erstellen":
                    available = sorted(self.manager.loaded_tools)
                    msg = f"❌ Skill '{skill_name}' nicht gefunden.\n✅ Verfügbar: {', '.join(available[:10])}"
                    return {"response": msg, "intent": intent, "skill": skill_name, "thought": thought, "error": True}

                result = self.manager.execute_skill(skill_name, params)

                if "SUCCESS_CREATED" in str(result):
                    self.load_skills()
                    result = f"{result}\n✨ Skills neu geladen"

                self.chat_history.append({"role": "assistant", "content": f"Skill-Ergebnis: {result}"})
                return {"response": str(result), "intent": intent, "skill": skill_name, "thought": thought, "error": False}

        # Freie Antwort (kein JSON)
        self.chat_history.append({"role": "assistant", "content": raw})
        return {"response": raw, "intent": intent, "skill": None, "thought": None, "error": False}

    # ---------------------------------------------------------------- #
    # CLI-Hauptschleife                                                  #
    # ---------------------------------------------------------------- #

    def run(self) -> None:
        print(C.wrap(C.BOLD + C.BLUE, "\n╔══════════════════════════════════════════╗"))
        print(C.wrap(C.BOLD + C.BLUE,   "║  Offenes Leuchten  v5.0                 ║"))
        print(C.wrap(C.BOLD + C.BLUE,   "╚══════════════════════════════════════════╝"))
        print(C.wrap(C.CYAN, f"Provider: {self.provider_name.upper()} | Modell: {self.provider.model}"))
        print(C.wrap(C.CYAN, "Befehle:  exit · reload · debug · clear · switch\n"))

        while True:
            try:
                # Fehler-Reset
                if self.consecutive_errors >= self.max_errors:
                    print(C.wrap(C.RED, "⚠️  Zu viele Fehler – Reset"))
                    self.state = AgentState.IDLE
                    self.consecutive_errors = 0
                    self.chat_history.clear()
                    continue

                # Reload wenn nötig
                if self.state == AgentState.SKILL_CREATED_NEEDS_RELOAD:
                    self._do_reload()

                # User-Eingabe nur wenn IDLE
                if self.state == AgentState.IDLE:
                    try:
                        user_input = input(C.wrap(C.BLUE, "\nDu: ")).strip()
                    except EOFError:
                        break

                    if not user_input:
                        continue

                    cmd = user_input.lower()
                    if cmd in ("exit", "quit"):
                        print(C.wrap(C.YELLOW, "Auf Wiedersehen!"))
                        break
                    if cmd == "reload":
                        n = self.load_skills()
                        print(C.wrap(C.YELLOW, f"✓ {n} Skills geladen"))
                        continue
                    if cmd == "clear":
                        self.chat_history.clear()
                        self.recent_errors.clear()
                        print(C.wrap(C.YELLOW, "✓ Verlauf gelöscht"))
                        continue
                    if cmd == "debug":
                        print(C.wrap(C.MAGENTA,
                            f"  Provider: {self.provider_name}\n"
                            f"  Modell:   {self.provider.model}\n"
                            f"  State:    {self.state.name}\n"
                            f"  Skills:   {len(self.manager.loaded_tools)}\n"
                            f"  History:  {len(self.chat_history)} Nachrichten"
                        ))
                        continue
                    if cmd == "switch":
                        print(C.wrap(C.CYAN, "Wähle Provider: claude · gpt · gemini · ollama"))
                        new = input("Provider: ").strip().lower()
                        try:
                            self.provider_name, self.provider = select_provider(new)
                            print(C.wrap(C.GREEN, f"✓ Gewechselt zu {self.provider_name}"))
                        except Exception as e:
                            print(C.wrap(C.RED, f"✗ {e}"))
                        continue

                    self.last_user_input = user_input
                    self.chat_history.append({"role": "user", "content": user_input})

                # Intent bestimmen
                intent = "TASK" if self.state == AgentState.SKILL_MISSING else IntentDetector.detect(self.last_user_input)
                logger.info(f"Intent: {intent} | State: {self.state.name}")

                # Self-Knowledge: kein LLM nötig
                if intent == "SELF_KNOWLEDGE":
                    answer = self.self_knowledge_reply(self.last_user_input)
                    print(C.wrap(C.BLUE, f"Ilija: {answer}"))
                    self.chat_history.append({"role": "assistant", "content": answer})
                    self.state = AgentState.IDLE
                    continue

                # LLM-Aufruf
                messages   = [{"role": "system", "content": self.build_system_prompt(intent)}]
                messages  += self.chat_history[-self.max_history:]
                force_json = intent in ("TASK", "USER_QUESTION")

                print(C.wrap(C.YELLOW, f"🤔 Ilija denkt… ({intent})"))
                self.state = AgentState.PLANNING

                try:
                    raw = self.provider.chat(messages, force_json=force_json)
                except RateLimitError as e:
                    print(C.wrap(C.RED, f"⏳ Rate-Limit: {e}"))
                    self.state = AgentState.IDLE
                    continue
                except Exception as e:
                    print(C.wrap(C.RED, f"❌ API-Fehler: {e}"))
                    self.state = AgentState.IDLE
                    self.consecutive_errors += 1
                    continue

                # Antwort verarbeiten
                if force_json or "{" in raw:
                    decision = self.parse_response(raw)
                    if not decision:
                        print(C.wrap(C.RED, "❌ Ungültiges JSON vom LLM"))
                        self.state = AgentState.IDLE
                        self.consecutive_errors += 1
                        continue

                    if "antwort" in decision:
                        print(C.wrap(C.BLUE, f"Ilija: {decision['antwort']}"))
                        self.chat_history.append({"role": "assistant", "content": decision["antwort"]})
                        self.state = AgentState.IDLE
                        self.consecutive_errors = 0
                        continue

                    skill_name, params = self.extract_skill_call(decision)
                    if skill_name:
                        thought = decision.get("gedanke", "Ausführung")
                        needs_continue = self.run_skill(skill_name, params, thought)
                        if needs_continue:
                            continue
                    else:
                        print(C.wrap(C.RED, "⚠️  Unverständliche LLM-Antwort"))
                        self.state = AgentState.IDLE
                        self.consecutive_errors += 1
                else:
                    # Freie Textantwort (Smalltalk)
                    print(C.wrap(C.BLUE, f"Ilija: {raw}"))
                    self.chat_history.append({"role": "assistant", "content": raw})
                    self.state = AgentState.IDLE

            except KeyboardInterrupt:
                print(C.wrap(C.YELLOW, "\nBeendet."))
                break
            except Exception as e:
                logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
                print(C.wrap(C.RED, f"❌ Unerwarteter Fehler: {e}"))
                self.state = AgentState.IDLE
                self.consecutive_errors += 1


# ------------------------------------------------------------------ #
# Einstiegspunkt                                                       #
# ------------------------------------------------------------------ #

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Offenes Leuchten v5.0")
    parser.add_argument(
        "--provider", default="auto",
        choices=["auto", "claude", "gpt", "gemini", "ollama"],
        help="LLM-Provider (Standard: auto – wählt den ersten verfügbaren)",
    )
    args = parser.parse_args()
    Kernel(provider=args.provider).run()


if __name__ == "__main__":
    main()
