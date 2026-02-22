#!/usr/bin/env python3
"""
Offenes Leuchten – LLM Providers
==================================
Alle LLM-Provider Klassen und Hilfsfunktionen.
Unterstützt: Claude (Anthropic), ChatGPT (OpenAI), Gemini (Google), Ollama (lokal)
"""

import logging
import os
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Allgemeiner Provider-Fehler"""
    pass


class RateLimitError(ProviderError):
    """Rate-Limit überschritten"""
    pass


class LLMProvider:
    """Base class for LLM providers"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.available = False
        self.check_availability()

    def check_availability(self):
        raise NotImplementedError

    def chat(self, messages: List[Dict], force_json: bool = False) -> str:
        raise NotImplementedError


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.model = "claude-sonnet-4-20250514"
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        super().__init__(api_key)

    def check_availability(self):
        try:
            import anthropic
            if self.api_key:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.available = True
                logger.info("✓ Claude (Anthropic) verfügbar")
            else:
                logger.warning("⚠ Claude API Key fehlt")
        except ImportError:
            logger.warning("⚠ anthropic Paket nicht installiert")

    def chat(self, messages: List[Dict], force_json: bool = False) -> str:
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_msg or "Du bist Ilija.",
                messages=user_messages,
                temperature=0.7,
            )
            return response.content[0].text
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise RateLimitError(str(e))
            raise ProviderError(str(e))


class OpenAIProvider(LLMProvider):
    """OpenAI ChatGPT provider"""

    def __init__(self, api_key: Optional[str] = None):
        self.model = "gpt-4o"
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        super().__init__(api_key)

    def check_availability(self):
        try:
            from openai import OpenAI
            if self.api_key:
                self.client = OpenAI(api_key=self.api_key)
                self.available = True
                logger.info("✓ ChatGPT (OpenAI) verfügbar")
            else:
                logger.warning("⚠ OpenAI API Key fehlt")
        except ImportError:
            logger.warning("⚠ openai Paket nicht installiert")

    def chat(self, messages: List[Dict], force_json: bool = False) -> str:
        try:
            kwargs = dict(model=self.model, messages=messages, temperature=0.7)
            if force_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise RateLimitError(str(e))
            raise ProviderError(str(e))


class GeminiProvider(LLMProvider):
    """Google Gemini provider (REST API)"""

    def __init__(self, api_key: Optional[str] = None):
        self.model = "gemini-2.5-flash"
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models"
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        super().__init__(api_key)

    def check_availability(self):
        if self.api_key:
            self.available = True
            logger.info("✓ Gemini (Google) verfügbar")
        else:
            logger.warning("⚠ Google API Key fehlt")

    def chat(self, messages: List[Dict], force_json: bool = False) -> str:
        import requests
        parts = [{"text": f"{m['role'].capitalize()}: {m['content']}"}
                 for m in messages if m["role"] in ("system", "user", "assistant")]
        if force_json:
            parts.append({"text": "\n\nWICHTIG: Antworte NUR mit validem JSON!"})
        url = f"{self.api_url}/{self.model}:generateContent"
        try:
            resp = requests.post(
                url,
                headers={"Content-Type": "application/json", "X-goog-api-key": self.api_key},
                json={"contents": [{"parts": parts}]},
                timeout=30,
            )
            if resp.status_code == 429:
                raise RateLimitError("Gemini Rate-Limit")
            resp.raise_for_status()
            data = resp.json()
            return "".join(
                p.get("text", "")
                for p in data["candidates"][0]["content"]["parts"]
            )
        except RateLimitError:
            raise
        except Exception as e:
            raise ProviderError(str(e))


class OllamaProvider(LLMProvider):
    """Local Ollama provider (fallback)"""

    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        super().__init__(None)

    def check_availability(self):
        try:
            import ollama
            ollama.list()
            self.available = True
            logger.info(f"✓ Ollama ({self.model}) verfügbar")
        except Exception:
            logger.warning("⚠ Ollama nicht verfügbar")

    def chat(self, messages: List[Dict], force_json: bool = False) -> str:
        import ollama
        try:
            kwargs = {"model": self.model, "messages": messages}
            if force_json:
                kwargs["format"] = "json"
            response = ollama.chat(**kwargs)
            return response["message"]["content"]
        except Exception as e:
            raise ProviderError(str(e))


def select_provider(preference: str = "auto") -> Tuple[str, LLMProvider]:
    """
    Wählt den ersten verfügbaren Provider aus.
    preference: "auto" | "claude" | "gpt" | "gemini" | "ollama"
    """
    candidates = {
        "claude":  lambda: ClaudeProvider(),
        "gpt":     lambda: OpenAIProvider(),
        "gemini":  lambda: GeminiProvider(),
        "ollama":  lambda: OllamaProvider(),
    }

    if preference != "auto" and preference in candidates:
        p = candidates[preference]()
        if p.available:
            return preference, p
        raise ProviderError(f"Provider '{preference}' nicht verfügbar")

    # Auto: erste verfügbare
    for name, factory in candidates.items():
        try:
            p = factory()
            if p.available:
                return name, p
        except Exception:
            continue

    raise ProviderError("Kein LLM-Provider verfügbar. Bitte API-Keys in .env setzen.")
