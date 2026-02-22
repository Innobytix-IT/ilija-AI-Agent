"""
Liest den Textinhalt einer Webseite von einer gegebenen URL.

Auto-generiert durch skill_erstellen
Skill-Name: webseiten_inhalt_lesen
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
import requests
from bs4 import BeautifulSoup

def webseiten_inhalt_lesen(url: str) -> str:
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()

        text = soup.get_text()
        
        # Clean up text by removing extra whitespace and newlines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for phrase in ' '.join(lines).split('  '))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except requests.exceptions.RequestException as e:
        return f"Fehler beim Abrufen der Webseite: {e}"
    except Exception as e:
        return f"Ein unerwarteter Fehler ist aufgetreten: {e}"

# Registrierung für den SkillManager
AVAILABLE_SKILLS = [webseiten_inhalt_lesen]
