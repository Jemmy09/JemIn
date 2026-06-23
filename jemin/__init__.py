"""
Jem In — a local, offline AI assistant for the terminal.

Supports Ollama (local), OpenAI, and Anthropic providers.
"""

__version__ = "1.0.0"
__author__ = "Jemmy09"

from .app import main  # noqa: F401 — re-exported for `python -m jemin`
