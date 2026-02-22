import os

SKILLS_DIR = "skills"

class SkillStatus:
    NOT_PRESENT = "NOT_PRESENT" # Existiert gar nicht
    FILE_EXISTS = "FILE_EXISTS" # Datei da, aber nicht im RAM
    LOADED = "LOADED"           # Bereit zur Nutzung
    PROTECTED = "PROTECTED"     # Darf nicht überschrieben werden

# Diese Skills sind das Immunsystem – Ilija darf sie nie löschen/ändern
PROTECTED_SKILLS = {
    "skill_erstellen",
    "cmd_ausfuehren",
    "wissen_speichern",
    "wissen_abrufen",
    "basis_tools",
    "gedaechtnis"
}

def get_skill_status(skill_name: str, loaded_skills: dict):
    # 1. Schutz prüfen
    if skill_name in PROTECTED_SKILLS:
        # Wenn er geladen ist, ist er ausführbar, aber geschützt vor Änderung
        if skill_name in loaded_skills:
            return SkillStatus.LOADED
        return SkillStatus.PROTECTED

    # 2. Ist er schon im RAM?
    if skill_name in loaded_skills:
        return SkillStatus.LOADED

    # 3. Liegt die Datei auf der Platte?
    path = os.path.join(SKILLS_DIR, f"{skill_name}.py")
    if os.path.exists(path):
        return SkillStatus.FILE_EXISTS

    # 4. Gibt es nicht
    return SkillStatus.NOT_PRESENT
