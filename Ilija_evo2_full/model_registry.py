import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ModelRegistry:
    """Verwaltet Provider-Modelle dynamisch über eine JSON-Konfigurationsdatei"""
    
    CONFIG_FILE = "models_config.json"
    
    # Standardwerte (Falls config fehlt oder gelöscht wird)
    DEFAULTS = {
        "openai": {
            "model": "gpt-4o",
            "api_base": "https://api.openai.com/v1"
        },
        "anthropic": {
            "model": "claude-sonnet-4-20250514",
            "api_base": "https://api.anthropic.com"
        },
        "google": {
            "model": "gemini-1.5-flash", 
            "api_base": "https://generativelanguage.googleapis.com/v1beta/models"
        },
        "ollama": {
            "model": "qwen2.5:7b",
            "api_base": "http://localhost:11434"
        }
    }

    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Lädt Config oder erstellt Default"""
        if not os.path.exists(self.CONFIG_FILE):
            logger.info(f"Erstelle Standard-Modellkonfiguration in {self.CONFIG_FILE}")
            self.save_config(self.DEFAULTS)
            return self.DEFAULTS
        
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Modell-Config: {e}")
            return self.DEFAULTS

    def save_config(self, config: Dict[str, Any]) -> None:
        """Speichert die aktuelle Konfiguration"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.error(f"Konnte Modell-Config nicht speichern: {e}")

    def get_model(self, provider: str) -> str:
        """Holt das aktuelle Modell für einen Provider"""
        provider = provider.lower()
        if provider in self.config:
            return self.config[provider].get("model", "unknown")
        # Fallback auf Defaults
        return self.DEFAULTS.get(provider, {}).get("model", "unknown")

    def update_model(self, provider: str, model_name: str) -> bool:
        """Aktualisiert das Modell für einen Provider"""
        provider = provider.lower()
        if provider not in self.config:
            self.config[provider] = {"model": model_name}
        else:
            self.config[provider]["model"] = model_name
        
        self.save_config(self.config)
        logger.info(f"Modell für {provider} geändert auf: {model_name}")
        return True
