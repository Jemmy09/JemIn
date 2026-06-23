"""
Jem In - a local, offline AI assistant for the terminal.

Entry point: wires together config, the Ollama client, conversation state,
and the rich-based UI into the interactive chat loop.
"""

from __future__ import annotations

import sys

from .config import Config, CONFIG_PATH, ensure_dirs
from .conversation import Conversation
from .client import ClientFactory, ClientError
from .setup_wizard import run_setup_wizard
from . import ui


class JemIn:
    def __init__(self) -> None:
        ensure_dirs()
        first_run = not CONFIG_PATH.exists()
        self.config = run_setup_wizard() if first_run else Config.load()
        self.client = ClientFactory(self.config)
        if not first_run:
            self._auto_correct_model_if_needed()
        self.convo = Conversation(
            system_prompt=self.config.system_prompt,
            context_limit=self.config.context_limit,
        )

    def _auto_correct_model_if_needed(self) -> None:
        """
        If Ollama is reachable but the configured model was never actually
        pulled, fall back to whatever model IS available rather than
        failing on the first chat message.
        """
        if not self.client.is_alive():
            return
        try:
            available = self.client.list_models()
        except ClientError:
            return
        if available and self.config.model not in available:
            new_model = available[0]
            ui.print_info(
                f"Configured model '{self.config.model}' isn't pulled locally. "
                f"Switching to '{new_model}' for this session. Use /model to change."
            )
            self.config.model = new_model
            self.client.model = new_model
            self.config.save()

    # --- main loop ---------------------------------------------------

    def run(self) -> None:
        online = self.client.is_alive()
        ui.print_banner(self.config.provider, self.config.model, self.config.host, online)

        while True:
            try:
                raw = ui.prompt_user().strip()
            except (EOFError, KeyboardInterrupt):
                ui.console.print()
                ui.print_info("Goodbye.")
                break

            if not raw:
                continue

            if raw.startswith("/"):
                if self._handle_command(raw):
                    break
                continue

            self._handle_chat_turn(raw)

    # --- chat ----------------------------------------------------------

    def _handle_chat_turn(self, user_text: str) -> None:
        self.convo.add("user", user_text)
        messages = self.convo.to_api_messages()
        ui.console.print()  # spacing before the streamed reply

        with ui.StreamingAssistantPanel(self.config.model) as panel:
            try:
                for chunk in self.client.chat_stream(messages):
                    panel.update(chunk)
            except ClientError as exc:
                ui.print_error(str(exc))
                if self.convo.messages:
                    self.convo.messages.pop()
                return

        reply = panel.text.strip()
        if reply:
            self.convo.add("assistant", reply)
        else:
            ui.print_error("No response received from the model.")
            if self.convo.messages:
                self.convo.messages.pop()

    # --- slash commands --------------------------------------------------

    def _handle_command(self, raw: str) -> bool:
        """Returns True if the app should exit."""
        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/exit", "/quit"):
            ui.print_info("Goodbye.")
            return True

        elif cmd == "/help":
            ui.print_help()

        elif cmd == "/clear":
            ui.console.clear()

        elif cmd == "/new":
            self.convo.clear()
            ui.print_info("Started a new conversation.")

        elif cmd == "/save":
            path = self.convo.save()
            ui.print_info(f"Saved conversation to {path}")

        elif cmd == "/history":
            self._list_history()

        elif cmd == "/load":
            self._load_history(arg)

        elif cmd == "/models":
            self._list_models()

        elif cmd == "/model":
            self._handle_model_command(arg)

        elif cmd == "/provider":
            self._handle_provider_command(arg)

        elif cmd == "/apikey":
            self._handle_apikey_command(arg)

        elif cmd in ("/signin", "/login"):
            self._handle_signin_command(arg)

        elif cmd == "/temperature":
            self._handle_temperature_command(arg)

        elif cmd == "/context":
            self._handle_context_command(arg)

        elif cmd == "/host":
            self._handle_host_command(arg)

        elif cmd == "/delete":
            self._handle_delete_command(arg)

        elif cmd == "/system":
            self._handle_system_command(arg)

        else:
            ui.print_error(f"Unknown command: {cmd}. Type /help for the list of commands.")

        return False

    def _list_history(self) -> None:
        saved = Conversation.list_saved()
        if not saved:
            ui.print_info("No saved conversations yet. Use /save to create one.")
            return
        ui.print_info("Saved conversations (most recent first):")
        for i, path in enumerate(saved, start=1):
            ui.console.print(f"  [{i}] {path.stem}")

    def _load_history(self, arg: str) -> None:
        saved = Conversation.list_saved()
        if not saved:
            ui.print_info("No saved conversations to load.")
            return
        if not arg:
            self._list_history()
            ui.print_info("Usage: /load <number>")
            return
        try:
            idx = int(arg) - 1
            if idx < 0:
                raise IndexError
            path = saved[idx]
        except (ValueError, IndexError):
            ui.print_error("Invalid selection. Use /history to see valid numbers.")
            return
        self.convo = Conversation.load(path, context_limit=self.config.context_limit)
        ui.print_info(f"Loaded conversation '{path.stem}' ({len(self.convo.messages)} messages).")

    def _list_models(self) -> None:
        """Show ALL models for every provider, with availability badges."""
        from .client import ClientFactory
        from .config import Config

        ui.console.print()
        providers = [
            ("ollama",    "OLLAMA (local)"),
            ("openai",    "OPENAI (ChatGPT)"),
            ("anthropic", "ANTHROPIC (Claude)"),
        ]

        for p, label in providers:
            temp_config = Config(
                model=self.config.model, host=self.config.host, provider=p,
                openai_api_key=self.config.openai_api_key,
                anthropic_api_key=self.config.anthropic_api_key,
            )
            temp_client = ClientFactory(temp_config)
            alive = temp_client.is_alive()
            models = temp_client.list_models()  # never raises now

            # Section header with live-status badge
            if alive:
                badge = "[bold green]\u25cf[/bold green]"
            else:
                badge = "[bold yellow]\u25cb[/bold yellow]"
            ui.console.print(f"\n {badge} [bold]{label}[/bold]")

            if not alive:
                if p == "ollama":
                    ui.console.print(
                        f"   [{ui.DIM}]Ollama not running — showing common models. "
                        f"Start with: ollama serve[/{ui.DIM}]"
                    )
                else:
                    ui.console.print(
                        f"   [{ui.DIM}]No API key — sign in with: /apikey {p} <key>[/{ui.DIM}]"
                    )

            for m in models:
                is_active = (m == self.config.model and p == self.config.provider)
                if is_active:
                    bullet = "[bold green]\u2022[/bold green]"
                    name_style = "bold green"
                    suffix = " [bold green](active)[/bold green]"
                elif alive:
                    bullet = "[green]\u2022[/green]"
                    name_style = "default"
                    suffix = ""
                else:
                    bullet = "[yellow]\u25e6[/yellow]"
                    name_style = "grey58"
                    suffix = ""
                ui.console.print(
                    f"   {bullet} [{name_style}]{m}[/{name_style}]{suffix}"
                )

        ui.console.print()

    def _prompt_for_api_key(self, provider: str) -> bool:
        """
        Trigger the interactive sign-in panel for a cloud provider.
        Saves the key and rebuilds the client if the user provides one.
        Returns True if a key was successfully saved.
        """
        key = ui.prompt_api_key(provider)
        if not key:
            return False
        if provider == "openai":
            self.config.openai_api_key = key
        elif provider == "anthropic":
            self.config.anthropic_api_key = key
        else:
            return False
        self.config.save()
        self.client = ClientFactory(self.config)
        if self.client.is_alive():
            ui.print_success(f"Signed in to {provider}. API key saved.")
            return True
        else:
            ui.print_error(f"Key saved but could not verify connection to {provider}.")
            return False

    def _handle_model_command(self, arg: str) -> None:
        if not arg:
            from .client import ClientFactory
            from .config import Config

            ui.print_info("Loading all models...")
            providers = [
                "ollama",
                "openai",
                "anthropic",
            ]
            all_models: list[tuple[str, str, bool]] = []  # (provider, model, alive)

            for p in providers:
                temp_config = Config(
                    model=self.config.model, host=self.config.host, provider=p,
                    openai_api_key=self.config.openai_api_key,
                    anthropic_api_key=self.config.anthropic_api_key,
                )
                temp_client = ClientFactory(temp_config)
                alive = temp_client.is_alive()
                models = temp_client.list_models()
                for m in models:
                    all_models.append((p, m, alive))

            ui.console.print("\n[bold cyan]Select a model to switch to:[/bold cyan]")
            for i, (p, m, alive) in enumerate(all_models, start=1):
                is_active = (m == self.config.model and p == self.config.provider)
                if is_active:
                    num_style = "bold green"
                    name_style = "bold green"
                    suffix = " [bold green](active)[/bold green]"
                elif alive:
                    num_style = "bold magenta"
                    name_style = "default"
                    suffix = ""
                else:
                    num_style = "bold yellow"
                    name_style = "grey58"
                    suffix = " [yellow](sign in required)[/yellow]" if p != "ollama" else " [yellow](not running)[/yellow]"
                ui.console.print(
                    f"  [[{num_style}]{i}[/{num_style}]] [{name_style}]{m}[/{name_style}]"
                    f" [{ui.DIM}]({p})[/{ui.DIM}]{suffix}"
                )

            ui.console.print()
            ui.console.print("[bold cyan]Enter a number (or press Enter to cancel):[/bold cyan] ", end="")
            try:
                choice = input().strip()
                if not choice:
                    ui.print_info("Cancelled.")
                    return
                idx = int(choice) - 1
                if not (0 <= idx < len(all_models)):
                    ui.print_error("Invalid selection.")
                    return

                p, m, alive = all_models[idx]

                # Cloud model selected but no key — trigger sign-in
                if not alive and p in ("openai", "anthropic"):
                    ui.print_info(
                        f"'{m}' requires a {p.capitalize()} API key. Starting sign-in..."
                    )
                    if not self._prompt_for_api_key(p):
                        return  # user cancelled sign-in

                # Ollama model selected but not running — just warn, still switch
                if not alive and p == "ollama":
                    ui.print_info(
                        "Ollama is not running. Model saved — start Ollama before chatting."
                    )

                self.config.provider = p
                self.config.model = m
                self.config.save()
                self.client = ClientFactory(self.config)
                ui.print_info(f"Switched to [{p}] {m}.")

            except (ValueError, EOFError, KeyboardInterrupt):
                ui.print_info("Cancelled.")
            return

        # Direct: /model <name>
        try:
            available = self.client.list_models()
        except Exception as exc:
            ui.print_error(str(exc))
            return

        if available and arg not in available:
            msg = (
                f"'{arg}' is not in the known model list for {self.config.provider}.\n"
                f"Available: {', '.join(available)}"
            )
            if self.config.provider == "ollama":
                msg += f"\nTo pull it: ollama pull {arg}"
            ui.print_error(msg)
            return

        self.config.model = arg
        self.client.model = arg
        self.config.save()
        ui.print_info(f"Switched model to '{arg}'.")

    def _handle_provider_command(self, arg: str) -> None:
        if not arg:
            ui.print_info(f"Current provider: {self.config.provider}")
            return

        valid_providers = ("ollama", "openai", "anthropic")
        if arg not in valid_providers:
            ui.print_error(
                f"Invalid provider '{arg}'. Options: {', '.join(valid_providers)}"
            )
            return

        self.config.provider = arg
        if arg == "openai" and not any(
            tag in self.config.model for tag in ("gpt", "o1", "o3", "o4")
        ):
            self.config.model = "gpt-4o"
        elif arg == "anthropic" and "claude" not in self.config.model:
            self.config.model = "claude-3-5-sonnet-20241022"

        self.config.save()
        self.client = ClientFactory(self.config)
        ui.print_info(f"Switched provider to '{arg}'. Model: '{self.config.model}'.")

        # Auto sign-in if cloud provider has no key yet
        if arg in ("openai", "anthropic") and not self.client.is_alive():
            ui.print_info(f"No API key found for {arg}. Starting sign-in...")
            self._prompt_for_api_key(arg)

    def _handle_apikey_command(self, arg: str) -> None:
        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            ui.print_error("Usage: /apikey <provider> <key>")
            return
            
        provider, key = parts[0].lower(), parts[1].strip()
        if provider in ("openai", "chatgpt"):
            self.config.openai_api_key = key
            p = "openai"
        elif provider in ("anthropic", "claude"):
            self.config.anthropic_api_key = key
            p = "anthropic"
        else:
            ui.print_error("Invalid provider for apikey. Use 'openai'/'chatgpt' or 'anthropic'/'claude'.")
            return
            
        self.config.save()
        ui.print_info(f"Saved API key for {p}.")
        if self.config.provider == p:
            self.client = ClientFactory(self.config)

    def _handle_signin_command(self, arg: str) -> None:
        provider = arg.strip().lower()
        if not provider:
            ui.console.print("\n[bold cyan]Select a provider to sign in:[/bold cyan]")
            ui.console.print("  [[bold magenta]1[/bold magenta]] ChatGPT / OpenAI")
            ui.console.print("  [[bold magenta]2[/bold magenta]] Claude / Anthropic")
            ui.console.print()
            ui.console.print("[bold cyan]Enter a number (or press Enter to cancel):[/bold cyan] ", end="")
            try:
                choice = input().strip()
                if choice == "1":
                    provider = "openai"
                elif choice == "2":
                    provider = "anthropic"
                else:
                    ui.print_info("Cancelled.")
                    return
            except (ValueError, EOFError, KeyboardInterrupt):
                ui.print_info("Cancelled.")
                return

        if provider in ("openai", "chatgpt"):
            p = "openai"
        elif provider in ("anthropic", "claude"):
            p = "anthropic"
        else:
            ui.print_error("Invalid provider. Use 'openai'/'chatgpt' or 'anthropic'/'claude'.")
            return

        self._prompt_for_api_key(p)

    def _handle_system_command(self, arg: str) -> None:
        if not arg:
            ui.print_info(f"Current system prompt:\n{self.config.system_prompt}")
            return
        self.config.system_prompt = arg
        self.convo.system_prompt = arg
        self.config.save()
        ui.print_info("System prompt updated for this session and saved.")

    def _handle_temperature_command(self, arg: str) -> None:
        if not arg:
            ui.print_info(f"Current temperature: {self.config.temperature}")
            return
        try:
            val = float(arg)
            if not 0.0 <= val <= 2.0:
                ui.print_error("Temperature should be between 0.0 and 2.0")
                return
            self.config.temperature = val
            self.client.temperature = val
            self.config.save()
            ui.print_info(f"Temperature set to {val}")
        except ValueError:
            ui.print_error("Invalid temperature value. Must be a number (e.g. 0.7)")

    def _handle_context_command(self, arg: str) -> None:
        if not arg:
            ui.print_info(f"Current context limit: {self.config.context_limit} tokens")
            return
        try:
            val = int(arg)
            if val < 100:
                ui.print_error("Context limit must be at least 100")
                return
            self.config.context_limit = val
            self.convo.context_limit = val
            self.config.save()
            ui.print_info(f"Context limit set to {val} tokens")
        except ValueError:
            ui.print_error("Invalid context limit. Must be an integer (e.g. 8000)")

    def _handle_host_command(self, arg: str) -> None:
        if not arg:
            ui.print_info(f"Current Ollama host: {self.config.host}")
            return
        self.config.host = arg
        self.config.save()
        if self.config.provider == "ollama":
            self.client = ClientFactory(self.config)
        ui.print_info(f"Ollama host set to {arg}")

    def _handle_delete_command(self, arg: str) -> None:
        saved = Conversation.list_saved()
        if not saved:
            ui.print_info("No saved conversations to delete.")
            return
        if not arg:
            self._list_history()
            ui.print_info("Usage: /delete <number>")
            return
        try:
            idx = int(arg) - 1
            if idx < 0:
                raise IndexError
            path = saved[idx]
        except (ValueError, IndexError):
            ui.print_error("Invalid selection. Use /history to see valid numbers.")
            return
            
        try:
            path.unlink()
            ui.print_info(f"Deleted conversation '{path.stem}'.")
        except OSError as exc:
            ui.print_error(f"Failed to delete {path.stem}: {exc}")


def main() -> None:
    try:
        app = JemIn()
        app.run()
    except KeyboardInterrupt:
        ui.console.print()
        ui.print_info("Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
