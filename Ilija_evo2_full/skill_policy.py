"""
Offenes Leuchten – Skill-Policy Layer
======================================
Entscheidungsschicht zwischen Planner und SkillManager.

Prüft jeden Skill-Aufruf bevor er ausgeführt wird:
  - Im Autonomy-Modus: interaktive Skills blockieren
  - Riskante Skills: Warnung ausgeben
  - Neuen Skills (dynamisch erstellt): als sicher einstufen

Kontext-Modi:
  MANUAL     → User tippt direkt → alle Skills erlaubt
  AUTONOMOUS → Autonomy Loop läuft → nur sichere Skills

Integration:
  autonomy_loop.py  → vor jedem _execute_step()
  main_v4_cloud.py  → optional, für zukünftige Erweiterung
"""

from enum import Enum
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Ausführungs-Kontext
# ──────────────────────────────────────────────────────────────

class ExecutionMode(Enum):
    MANUAL     = "manual"      # User tippt direkt – keine Einschränkungen
    AUTONOMOUS = "autonomous"  # Autonomy Loop – nur sichere Skills


# ──────────────────────────────────────────────────────────────
# Skill-Kategorien
# ──────────────────────────────────────────────────────────────

class SkillCategory(Enum):
    SAFE       = "safe"        # Immer erlaubt
    INTERACTIVE = "interactive" # Braucht User-Interaktion → im Loop blockiert
    RISKY      = "risky"       # Führt externe Aktionen aus → Warnung
    UNKNOWN    = "unknown"     # Nicht klassifiziert → im Zweifel erlaubt


# ──────────────────────────────────────────────────────────────
# Policy-Entscheidung
# ──────────────────────────────────────────────────────────────

class PolicyDecision(Enum):
    ALLOW   = "allow"    # Skill darf ausgeführt werden
    BLOCK   = "block"    # Skill wird blockiert
    WARN    = "warn"     # Skill wird ausgeführt, aber mit Warnung


# ──────────────────────────────────────────────────────────────
# Skill-Klassifizierung
# ──────────────────────────────────────────────────────────────

# INTERACTIVE: Skills die input() aufrufen oder externen User-Input brauchen
INTERACTIVE_SKILLS = {
    "dialog_mit_gemini",        # Öffnet Browser + wartet auf Eingabe
    "browser_oeffnen",          # Öffnet Browser interaktiv
    "terminal_oeffnen_und_eintragen",  # Öffnet Terminal interaktiv
    "outlook_posteingang_pruefen",     # GUI-Interaktion
    "whatsapp_lesen",           # GUI-Interaktion
    "whatsapp_senden",          # GUI-Interaktion mit Bestätigung
    "frage_gemini",             # Interaktiver Browser-Dialog
}

# RISKY: Skills die externe Systeme verändern oder Shell-Befehle ausführen
RISKY_SKILLS = {
    "cmd_ausfuehren",           # Shell-Befehle – potenziell destruktiv
    "terminal_oeffnen_und_eintragen",  # Shell-Zugriff
    "datei_schreiben",          # Dateisystem-Änderungen
}

# SAFE: Explizit sichere Skills (Rest wird als UNKNOWN = erlaubt behandelt)
SAFE_SKILLS = {
    "skill_erstellen",          # Erstellt neue Skills
    "wissen_speichern",         # Gedächtnis schreiben
    "wissen_abrufen",           # Gedächtnis lesen
    "wetterdaten_abrufen",      # API-Abfrage (read-only)
    "webseiten_inhalt_lesen",   # Web-Scraping (read-only)
    "internet_suchen",          # Suche (read-only)
    "muenze_werfen",            # Zufall
    "wuerfeln",                 # Zufall
    "witze_erzaehlen",          # Text
    "bitcoin_preis_abrufen",    # API (read-only)
    "trading",                  # Analyse (read-only, kein echter Trade)
    "direkt",                   # LLM-Direktantwort
}


# ──────────────────────────────────────────────────────────────
# Policy Engine
# ──────────────────────────────────────────────────────────────

class SkillPolicy:
    """
    Prüft ob ein Skill im gegebenen Kontext ausgeführt werden darf.

    Beispiel:
        policy = SkillPolicy()
        decision, reason = policy.check("dialog_mit_gemini", ExecutionMode.AUTONOMOUS)
        if decision == PolicyDecision.BLOCK:
            # Skill überspringen oder ersetzen
    """

    def __init__(self):
        self.interactive = set(INTERACTIVE_SKILLS)
        self.risky       = set(RISKY_SKILLS)
        self.safe        = set(SAFE_SKILLS)

    def categorize(self, skill_name: str) -> SkillCategory:
        """Bestimmt die Kategorie eines Skills."""
        if not skill_name:
            return SkillCategory.SAFE
        name = skill_name.lower().strip()
        if name in self.interactive:
            return SkillCategory.INTERACTIVE
        if name in self.risky:
            return SkillCategory.RISKY
        if name in self.safe:
            return SkillCategory.SAFE
        # Dynamisch erstellte Skills (nicht in keiner Liste) → UNKNOWN = erlaubt
        return SkillCategory.UNKNOWN

    def check(self, skill_name: str, mode: ExecutionMode) -> tuple:
        """
        Hauptprüfung: Darf der Skill ausgeführt werden?

        Returns:
            (PolicyDecision, reason: str)
        """
        category = self.categorize(skill_name)

        # INTERACTIVE im Autonomy-Modus → immer blockieren
        if category == SkillCategory.INTERACTIVE and mode == ExecutionMode.AUTONOMOUS:
            reason = (
                f"'{skill_name}' ist ein interaktiver Skill (wartet auf User-Eingabe) "
                f"und kann im Autonomy-Modus nicht ausgeführt werden."
            )
            return PolicyDecision.BLOCK, reason

        # RISKY → immer warnen, aber ausführen
        if category == SkillCategory.RISKY:
            reason = (
                f"'{skill_name}' ist ein riskanter Skill (Systemzugriff). "
                f"Wird ausgeführt, aber mit Vorsicht."
            )
            return PolicyDecision.WARN, reason

        # Alles andere → erlaubt
        return PolicyDecision.ALLOW, ""

    def filter_for_planner(self, all_skills: list, mode: ExecutionMode) -> list:
        """
        Gibt eine gefilterte Skill-Liste für den Planner-Prompt zurück.
        Im Autonomy-Modus werden interaktive Skills ausgeblendet.
        """
        if mode != ExecutionMode.AUTONOMOUS:
            return all_skills

        filtered = []
        blocked  = []
        for skill in all_skills:
            name = skill if isinstance(skill, str) else skill.get("name", "")
            if self.categorize(name) == SkillCategory.INTERACTIVE:
                blocked.append(name)
            else:
                filtered.append(skill)

        if blocked:
            logger.info(f"Policy: {len(blocked)} interaktive Skills aus Planner-Liste entfernt: {blocked}")

        return filtered

    def get_blocked_skills_hint(self) -> str:
        """Gibt einen Hinweis-String für den Planner-Prompt zurück."""
        return (
            "WICHTIG – Folgende Skills sind im Autonomy-Modus NICHT verfügbar "
            "(sie benötigen User-Interaktion und würden den Loop blockieren):\n"
            + ", ".join(sorted(self.interactive))
            + "\nNutze stattdessen 'direkt' für LLM-Antworten oder erstelle einen neuen autonomen Skill."
        )

    def explain(self, skill_name: str) -> str:
        """Erklärt warum ein Skill blockiert/erlaubt ist."""
        category = self.categorize(skill_name)
        if category == SkillCategory.INTERACTIVE:
            return f"'{skill_name}' → INTERAKTIV: Wartet auf User-Eingabe – im Loop nicht verwendbar."
        if category == SkillCategory.RISKY:
            return f"'{skill_name}' → RISKANT: Führt Systemoperationen aus – mit Vorsicht verwenden."
        if category == SkillCategory.SAFE:
            return f"'{skill_name}' → SICHER: Explizit als autonom-sicher klassifiziert."
        return f"'{skill_name}' → UNBEKANNT: Nicht klassifiziert – wird als sicher behandelt."


# ──────────────────────────────────────────────────────────────
# Singleton (wird von autonomy_loop importiert)
# ──────────────────────────────────────────────────────────────

_policy_instance: Optional[SkillPolicy] = None

def get_policy() -> SkillPolicy:
    """Gibt die gemeinsame Policy-Instanz zurück."""
    global _policy_instance
    if _policy_instance is None:
        _policy_instance = SkillPolicy()
    return _policy_instance
