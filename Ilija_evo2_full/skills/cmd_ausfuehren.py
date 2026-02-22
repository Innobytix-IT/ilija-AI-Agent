
"""
Führt einen Shell-Befehl auf dem Linux-System aus.
"""
import random
import time
import math
import os

def cmd_ausfuehren(befehl: str):
    import subprocess
    return subprocess.run(['bash', '-c', befehl])

# Automatische Registrierung
AVAILABLE_SKILLS = [cmd_ausfuehren]
