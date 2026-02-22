from enum import Enum, auto

class AgentState(Enum):
    IDLE = auto()                       # Wartet auf Input
    PLANNING = auto()                   # Denkt nach
    SKILL_MISSING = auto()              # Hat erkannt: Skill fehlt
    SKILL_CREATING = auto()             # Ist dabei, Skill zu schreiben
    SKILL_CREATED_NEEDS_RELOAD = auto() # Skill da, aber noch nicht geladen
    READY = auto()                      # Bereit zur Ausführung
    ERROR = auto()                      # Fehlerzustand
