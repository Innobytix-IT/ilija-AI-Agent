"""
Öffnet ein Terminal und ermöglicht die Eingabe von Befehlen.

Auto-generiert durch skill_erstellen
Skill-Name: terminal_oeffnen_und_eintragen
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
def terminal_oeffnen_und_eintragen() -> str:
    import subprocess
    from time import sleep

    # Öffne das Terminal
    terminal = subprocess.Popen(['xterm'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sleep(2)  # Lasse etwas Zeit, bis das Terminal bereit ist

    # Befehl zum Ausführen
    command = 'sudo apt update && sudo apt upgrade -y'
    stdout_data, stderr_data = terminal.communicate(command.encode())
    if terminal.returncode == 0:
        return stdout_data.decode()
    else:
        return stderr_data.decode()

# Registrierung für den SkillManager
AVAILABLE_SKILLS = [terminal_oeffnen_und_eintragen]
