import subprocess
import datetime
import os

def cmd_ausfuehren(befehl: str):
    """
    Führt einen Shell-Befehl auf dem Linux-System aus. 
    VORSICHT: Nur nutzen, wenn vom User explizit verlangt.
    """
    try:
        # Timeout nach 10 Sekunden für Sicherheit
        result = subprocess.run(befehl, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout
        if result.stderr:
            output += f"\nFEHLER: {result.stderr}"
        return output.strip() or "Befehl ausgeführt (keine Ausgabe)."
    except Exception as e:
        return f"Fehler bei Befehlsausführung: {e}"

def aktuelle_zeit_holen():
    """Gibt das aktuelle Datum und die Uhrzeit zurück."""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def datei_schreiben(pfad: str, inhalt: str):
    """Erstellt oder überschreibt eine Datei mit Textinhalt."""
    try:
        with open(pfad, 'w', encoding='utf-8') as f:
            f.write(inhalt)
        return f"Datei '{pfad}' erfolgreich geschrieben."
    except Exception as e:
        return f"Fehler beim Schreiben: {e}"

# WICHTIG: Liste der verfügbaren Funktionen
AVAILABLE_SKILLS = [cmd_ausfuehren, aktuelle_zeit_holen, datei_schreiben]
