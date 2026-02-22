"""
Offenes Leuchten – Skill Scoring
=====================================
Protokolliert Erfolg und Fehler pro Skill.

Nach jeder Ausführung wird gespeichert:
  - Wie oft ausgeführt
  - Wie oft erfolgreich
  - Wie oft fehlgeschlagen
  - Durchschnittliche Ausführungszeit
  - Letzter Fehler

Der Planner bekommt diese Daten und kann
zuverlässige Skills bevorzugen.

Gespeichert in: skill_scores.json
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

SCORES_FILE = "skill_scores.json"


class SkillScoring:
    """Verfolgt Erfolgsraten aller Skills."""

    def __init__(self, scores_file: str = SCORES_FILE):
        self.scores_file = scores_file
        self.scores: Dict = self._load()

    def _load(self) -> Dict:
        """Lädt Scores aus JSON-Datei."""
        if os.path.exists(self.scores_file):
            try:
                with open(self.scores_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Skill-Scores konnten nicht geladen werden: {e}")
        return {}

    def _save(self):
        """Speichert Scores in JSON-Datei."""
        try:
            with open(self.scores_file, "w", encoding="utf-8") as f:
                json.dump(self.scores, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Skill-Scores konnten nicht gespeichert werden: {e}")

    def _ensure_skill(self, skill_name: str):
        """Erstellt einen leeren Score-Eintrag falls nicht vorhanden."""
        if skill_name not in self.scores:
            self.scores[skill_name] = {
                "executions":   0,
                "successes":    0,
                "failures":     0,
                "total_time_s": 0.0,
                "last_error":   None,
                "last_used":    None,
                "created":      datetime.now().isoformat(),
            }

    def record_success(self, skill_name: str, duration_s: float = 0.0):
        """
        Protokolliert eine erfolgreiche Skill-Ausführung.

        Args:
            skill_name: Name des Skills
            duration_s: Ausführungsdauer in Sekunden
        """
        self._ensure_skill(skill_name)
        s = self.scores[skill_name]
        s["executions"]   += 1
        s["successes"]    += 1
        s["total_time_s"] += duration_s
        s["last_used"]     = datetime.now().isoformat()
        self._save()

    def record_failure(self, skill_name: str, error: str = "", duration_s: float = 0.0):
        """
        Protokolliert eine fehlgeschlagene Skill-Ausführung.

        Args:
            skill_name: Name des Skills
            error: Fehlermeldung
            duration_s: Ausführungsdauer bis zum Fehler
        """
        self._ensure_skill(skill_name)
        s = self.scores[skill_name]
        s["executions"]   += 1
        s["failures"]     += 1
        s["total_time_s"] += duration_s
        s["last_error"]    = error[:200] if error else None
        s["last_used"]     = datetime.now().isoformat()
        self._save()

    def get_score(self, skill_name: str) -> Optional[Dict]:
        """Gibt den Score eines Skills zurück."""
        if skill_name not in self.scores:
            return None
        s = self.scores[skill_name]
        execs = s["executions"]
        return {
            "skill":        skill_name,
            "executions":   execs,
            "successes":    s["successes"],
            "failures":     s["failures"],
            "success_rate": round(s["successes"] / execs * 100) if execs > 0 else None,
            "avg_time_s":   round(s["total_time_s"] / execs, 2) if execs > 0 else None,
            "last_error":   s["last_error"],
            "last_used":    s["last_used"],
        }

    def get_reliability(self, skill_name: str) -> str:
        """
        Gibt eine Zuverlässigkeitsstufe zurück.

        Returns: "unbekannt" | "zuverlässig" | "instabil" | "fehlerhaft"
        """
        score = self.get_score(skill_name)
        if not score or score["executions"] < 2:
            return "unbekannt"

        rate = score["success_rate"]
        if rate is None:
            return "unbekannt"
        if rate >= 80:
            return "zuverlässig"
        if rate >= 50:
            return "instabil"
        return "fehlerhaft"

    def format_for_planner(self, skill_names: List[str]) -> str:
        """
        Gibt Scoring-Daten als Prompt-Zusatz für den Planner zurück.
        Nur Skills mit mindestens 2 Ausführungen werden erwähnt.
        """
        lines = []
        for name in skill_names:
            score = self.get_score(name)
            if not score or score["executions"] < 2:
                continue
            reliability = self.get_reliability(name)
            if reliability == "zuverlässig":
                continue  # Nur auffällige erwähnen
            rate = score["success_rate"]
            lines.append(
                f"  ⚠️  '{name}': {reliability} ({rate}% Erfolgsrate, "
                f"{score['executions']}x ausgeführt)"
            )

        if not lines:
            return ""

        return (
            "\n\nSKILL-ZUVERLÄSSIGKEIT (basierend auf Erfahrung):\n"
            + "\n".join(lines)
            + "\nBitte bevorzuge zuverlässigere Alternativen wo möglich."
        )

    def format_overview(self) -> str:
        """Gibt eine Übersicht aller Skill-Scores zurück."""
        if not self.scores:
            return "Noch keine Skill-Ausführungen protokolliert."

        lines = ["📊 Skill-Zuverlässigkeit:\n"]
        sorted_skills = sorted(
            self.scores.items(),
            key=lambda x: x[1]["executions"],
            reverse=True
        )

        for name, s in sorted_skills:
            execs = s["executions"]
            if execs == 0:
                continue
            rate = round(s["successes"] / execs * 100)
            bar  = "█" * (rate // 10) + "░" * (10 - rate // 10)
            reliability = self.get_reliability(name)
            icon = {"zuverlässig": "✅", "instabil": "⚠️", "fehlerhaft": "❌", "unbekannt": "❓"}[reliability]
            lines.append(
                f"  {icon} {name:<30} {bar} {rate:3}%  ({execs}x)"
            )

        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────

_scoring: Optional[SkillScoring] = None

def get_scoring() -> SkillScoring:
    global _scoring
    if _scoring is None:
        _scoring = SkillScoring()
    return _scoring
