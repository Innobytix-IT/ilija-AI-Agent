"""
Offenes Leuchten – Skill Versioning (lokal)
============================================
Lokale Dateiversionierung für Skills – kein Git benötigt.

Funktionsweise:
  Wenn Ilija einen Skill erstellt oder überschreibt, wird
  automatisch eine Kopie im Backup-Ordner gesichert.

Struktur:
  skills/
    wetterdaten_abrufen.py          ← aktuelle Version
    .skill_backups/
      wetterdaten_abrufen.v1.py     ← älteste Version
      wetterdaten_abrufen.v2.py     ← zweite Version
      wetterdaten_abrufen.v3.py     ← vor letzter Änderung

Verwendung:
  from skill_versioning import get_versioning
  sv = get_versioning()

  sv.backup("wetterdaten_abrufen")         # Backup erstellen
  sv.list_versions("wetterdaten_abrufen")  # Alle Versionen anzeigen
  sv.rollback("wetterdaten_abrufen", 1)    # Eine Version zurück
"""

import os
import shutil
import logging
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

BACKUP_DIR_NAME = ".skill_backups"
MAX_VERSIONS    = 10  # Maximale Anzahl Backups pro Skill


class SkillVersioning:
    """Lokale Dateiversionierung für Skills."""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = os.path.abspath(skills_dir)
        self.backup_dir = os.path.join(self.skills_dir, BACKUP_DIR_NAME)
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Erstellt den Backup-Ordner falls er nicht existiert."""
        os.makedirs(self.backup_dir, exist_ok=True)
        # Versteckter Ordner – keine __init__.py damit er nicht als Skill geladen wird
        gitkeep = os.path.join(self.backup_dir, ".gitkeep")
        if not os.path.exists(gitkeep):
            open(gitkeep, "w").close()

    def _skill_path(self, skill_name: str) -> str:
        return os.path.join(self.skills_dir, f"{skill_name}.py")

    def _next_version(self, skill_name: str) -> int:
        """Bestimmt die nächste Versionsnummer."""
        existing = self.list_versions(skill_name)
        if not existing:
            return 1
        return existing[-1]["version"] + 1

    def backup(self, skill_name: str) -> str:
        """
        Sichert die aktuelle Version eines Skills als Backup.
        Wird automatisch vor jedem Überschreiben aufgerufen.

        Returns:
            Statusmeldung
        """
        skill_path = self._skill_path(skill_name)
        if not os.path.exists(skill_path):
            return f"Kein Backup nötig – '{skill_name}' existiert noch nicht"

        version    = self._next_version(skill_name)
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{skill_name}.v{version}_{timestamp}.py"
        backup_path = os.path.join(self.backup_dir, backup_name)

        try:
            shutil.copy2(skill_path, backup_path)
            logger.info(f"Backup erstellt: {backup_name}")

            # Alte Backups bereinigen falls Limit überschritten
            self._cleanup_old_versions(skill_name)

            return f"📦 Version {version} gesichert"
        except Exception as e:
            return f"Backup fehlgeschlagen: {e}"

    def list_versions(self, skill_name: str) -> List[Dict]:
        """
        Gibt alle gesicherten Versionen eines Skills zurück.

        Returns:
            Liste mit Dicts: {version, filename, date, path}
            Sortiert von ältester zu neuester Version.
        """
        if not os.path.exists(self.backup_dir):
            return []

        versions = []
        prefix   = f"{skill_name}.v"

        for filename in os.listdir(self.backup_dir):
            if not filename.startswith(prefix) or not filename.endswith(".py"):
                continue
            # Format: skillname.vN_YYYYMMDD_HHMMSS.py
            try:
                rest    = filename[len(prefix):]          # "N_YYYYMMDD_HHMMSS.py"
                ver_str = rest.split("_")[0]              # "N"
                version = int(ver_str)
                path    = os.path.join(self.backup_dir, filename)
                mtime   = os.path.getmtime(path)
                date    = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                versions.append({
                    "version":  version,
                    "filename": filename,
                    "date":     date,
                    "path":     path,
                })
            except (ValueError, IndexError):
                continue

        return sorted(versions, key=lambda x: x["version"])

    def rollback(self, skill_name: str, steps: int = 1) -> str:
        """
        Stellt eine frühere Version eines Skills wieder her.

        Args:
            skill_name: Name des Skills (ohne .py)
            steps: Wie viele Versionen zurück (1 = letzte gesicherte Version)

        Returns:
            Statusmeldung
        """
        versions = self.list_versions(skill_name)

        if not versions:
            return f"❌ Keine Backups vorhanden für '{skill_name}'"

        if steps > len(versions):
            return (
                f"❌ Nur {len(versions)} Version(en) vorhanden – "
                f"kann nicht {steps} Schritt(e) zurückgehen"
            )

        # Gewünschte Version (von hinten zählen)
        target = versions[-steps]
        skill_path = self._skill_path(skill_name)

        try:
            # Aktuelle Version zuerst sichern
            if os.path.exists(skill_path):
                self.backup(skill_name)

            # Zielversion wiederherstellen
            shutil.copy2(target["path"], skill_path)
            logger.info(f"Rollback '{skill_name}' → Version {target['version']} ({target['date']})")
            return (
                f"✅ Rollback erfolgreich: '{skill_name}' auf "
                f"Version {target['version']} vom {target['date']} zurückgesetzt"
            )
        except Exception as e:
            return f"❌ Rollback fehlgeschlagen: {e}"

    def _cleanup_old_versions(self, skill_name: str):
        """Löscht älteste Backups wenn MAX_VERSIONS überschritten."""
        versions = self.list_versions(skill_name)
        while len(versions) > MAX_VERSIONS:
            oldest = versions.pop(0)
            try:
                os.remove(oldest["path"])
                logger.info(f"Altes Backup gelöscht: {oldest['filename']}")
            except OSError:
                pass

    def format_history(self, skill_name: str) -> str:
        """Gibt die Versionshistorie als lesbaren String zurück."""
        versions = self.list_versions(skill_name)
        if not versions:
            return f"Keine Backups vorhanden für '{skill_name}'"

        lines = [f"📋 Versionshistorie: {skill_name}\n"]
        for v in reversed(versions):
            lines.append(f"  v{v['version']}  {v['date']}  {v['filename']}")
        lines.append(f"\nRollback: rollback('{skill_name}', steps=1) für letzte Version")
        return "\n".join(lines)

    def list_all_backed_up_skills(self) -> List[str]:
        """Gibt alle Skills zurück für die Backups existieren."""
        if not os.path.exists(self.backup_dir):
            return []
        skills = set()
        for filename in os.listdir(self.backup_dir):
            if filename.endswith(".py") and ".v" in filename:
                skill_name = filename.split(".v")[0]
                skills.add(skill_name)
        return sorted(skills)


# ── Singleton ──────────────────────────────────────────────────

_versioning: Optional[SkillVersioning] = None

def get_versioning(skills_dir: str = "skills") -> SkillVersioning:
    global _versioning
    if _versioning is None:
        _versioning = SkillVersioning(skills_dir)
    return _versioning
