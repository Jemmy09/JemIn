"""
First-run setup: checks for Ollama, helps the user pick a local model,
and writes the initial config. Runs automatically the first time Jem In
is launched (no config file present yet).

For cloud providers (OpenAI, Anthropic), the user is prompted for API keys
via the interactive sign-in flow in ui.prompt_api_key().
"""

from __future__ import annotations

from .config import Config, DEFAULT_MODEL
from .client import ClientFactory
from . import ui

RECOMMENDED_CPU_MODELS = [
    "llama3.2:3b",
    "qwen2.5:3b",
    "phi3:mini",
]


def run_setup_wizard() -> Config:
    ui.console.print()
    ui.print_info("First run detected - let's get Jem In set up.")

    ui.console.print("\n[bold cyan]Please choose your AI provider:[/bold cyan]")
    ui.console.print("  [[bold magenta]1[/bold magenta]] Ollama (local AI - 100% offline, free, runs on your machine)")
    ui.console.print("  [[bold magenta]2[/bold magenta]] ChatGPT / OpenAI (cloud AI, requires API key)")
    ui.console.print("  [[bold magenta]3[/bold magenta]] Claude / Anthropic (cloud AI, requires API key)")
    ui.console.print()
    ui.console.print("[bold cyan]Enter a number (default: 1):[/bold cyan] ", end="")
    
    provider_choice = "1"
    try:
        choice = input().strip()
        if choice in ("1", "2", "3"):
            provider_choice = choice
    except (KeyboardInterrupt, EOFError):
        pass

    config = Config()

    if provider_choice == "1":
        # Ollama Setup
        config.provider = "ollama"
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
        local_models = client.list_models()

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

    elif provider_choice == "2":
        # OpenAI / ChatGPT Setup
        config.provider = "openai"
        config.model = "gpt-4o-mini"
        ui.print_info("Setting up ChatGPT / OpenAI...")
        key = ui.prompt_api_key("openai")
        if key:
            config.openai_api_key = key
            # Rebuild client to test
            test_client = ClientFactory(config)
            if test_client.is_alive():
                ui.print_success("Signed in to OpenAI. Connection verified.")
            else:
                ui.print_error("Key saved but could not verify connection to OpenAI.")
        else:
            ui.print_info("No key provided. You will need to sign in later with /signin.")

    elif provider_choice == "3":
        # Anthropic / Claude Setup
        config.provider = "anthropic"
        config.model = "claude-3-5-sonnet-20241022"
        ui.print_info("Setting up Claude / Anthropic...")
        key = ui.prompt_api_key("anthropic")
        if key:
            config.anthropic_api_key = key
            # Rebuild client to test
            test_client = ClientFactory(config)
            if test_client.is_alive():
                ui.print_success("Signed in to Anthropic. Connection verified.")
            else:
                ui.print_error("Key saved but could not verify connection to Anthropic.")
        else:
            ui.print_info("No key provided. You will need to sign in later with /signin.")

    config.save()
    ui.print_info("Setup complete. Config saved to ~/.jemin/config.json\n")
    return config
