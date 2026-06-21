"""
First-run setup: checks for Ollama, helps the user pick a local model,
and writes the initial config. Runs automatically the first time Jem In
is launched (no config file present yet).
"""

from __future__ import annotations

from .config import Config, DEFAULT_MODEL
from .client import ClientFactory, ClientError
from . import ui

RECOMMENDED_CPU_MODELS = [
    "llama3.2:3b",
    "qwen2.5:3b",
    "phi3:mini",
]


def run_setup_wizard() -> Config:
    ui.console.print()
    ui.print_info("First run detected - let's get Jem In set up.")

    config = Config()
    client = ClientFactory(config)

    if not client.is_alive():
        ui.print_error(
            "Ollama doesn't seem to be running.\n\n"
            "Jem In needs Ollama installed and running locally to work.\n"
            "  1. Install it from https://ollama.com\n"
            "  2. Run: ollama serve\n"
            "  3. In another terminal: ollama pull llama3.2:3b\n"
            "  4. Re-launch Jem In\n\n"
            f"Saving default config so you don't see this wizard again "
            f"(model: {config.model}). Jem In will auto-detect models on "
            f"every future launch until Ollama is reachable."
        )
        config.save()
        return config

    ui.print_info(f"Ollama detected at {config.host}.")

    try:
        local_models = client.list_models()
    except ClientError as exc:
        ui.print_error(str(exc))
        local_models = []

    if local_models:
        ui.print_info("Local models found: " + ", ".join(local_models))
        chosen = local_models[0]
        ui.print_info(f"Using '{chosen}' as the default model. Change anytime with /model.")
        config.model = chosen
    else:
        ui.print_error(
            "No models are pulled yet. Recommended for CPU-only machines:\n\n"
            + "\n".join(f"  ollama pull {m}" for m in RECOMMENDED_CPU_MODELS)
            + f"\n\nSaving '{DEFAULT_MODEL}' as the default - pull it, then just start chatting."
        )
        config.model = DEFAULT_MODEL

    config.save()
    ui.print_info("Setup complete. Config saved to ~/.jemin/config.json\n")
    return config
