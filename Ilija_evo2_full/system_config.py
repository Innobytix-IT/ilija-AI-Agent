"""
Skill: System Konfiguration
Beschreibung: Erlaubt das Anzeigen und Ändern der verwendeten KI-Modelle zur Laufzeit.
"""

def system_modelle_anzeigen():
    """
    Zeigt die aktuell konfigurierten KI-Modelle für alle Provider an.
    """
    try:
        from model_registry import ModelRegistry
        registry = ModelRegistry()
        listing = registry.list_models()
        return f"Aktuelle Modell-Konfiguration:\n{listing}\n(Änderungen werden beim nächsten Neustart oder Reload wirksam)"
    except ImportError:
        return "Fehler: ModelRegistry nicht gefunden."

def system_modell_aendern(provider: str, neues_modell: str):
    """
    Ändert das KI-Modell für einen bestimmten Provider.
    
    Args:
        provider (str): Der Name des Providers (openai, anthropic, google, ollama).
        neues_modell (str): Der exakte Name des Modells (z.B. gpt-4-turbo).
    """
    try:
        from model_registry import ModelRegistry
        
        # Mapping für übliche Sprechweisen
        mapping = {
            'gpt': 'openai',
            'chatgpt': 'openai',
            'claude': 'anthropic',
            'gemini': 'google'
        }
        
        clean_provider = provider.lower().strip()
        if clean_provider in mapping:
            clean_provider = mapping[clean_provider]
            
        registry = ModelRegistry()
        registry.update_model(clean_provider, neues_modell)
        
        return f"✅ Erfolg: Modell für '{clean_provider}' wurde auf '{neues_modell}' geändert. Bitte führe 'switch' oder Neustart durch, damit es geladen wird."
        
    except Exception as e:
        return f"Fehler beim Ändern des Modells: {e}"
AVAILABLE_SKILLS = [system_modelle_anzeigen, system_modell_aendern]
