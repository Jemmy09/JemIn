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
                self.convo.messages.pop()
                return

        reply = panel.text.strip()
        if reply:
            self.convo.add("assistant", reply)
        else:
            ui.print_error("No response received from the model.")
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
            path = saved[idx]
        except (ValueError, IndexError):
            ui.print_error("Invalid selection. Use /history to see valid numbers.")
            return
        self.convo = Conversation.load(path, context_limit=self.config.context_limit)
        ui.print_info(f"Loaded conversation '{path.stem}' ({len(self.convo.messages)} messages).")

    def _list_models(self) -> None:
        try:
            models = self.client.list_models()
        except ClientError as exc:
            ui.print_error(str(exc))
            return
        if not models:
            ui.print_info("No models found.")
            return
        ui.print_info(f"Available models ({self.config.provider}):")
        for m in models:
            marker = " (active)" if m == self.config.model else ""
            ui.console.print(f"  \u2022 {m}{marker}")

    def _handle_model_command(self, arg: str) -> None:
        if not arg:
            ui.print_info(f"Current model: {self.config.model}")
            return

        try:
            available = self.client.list_models()
        except ClientError as exc:
            ui.print_error(str(exc))
            return

        if available and arg not in available:
            msg = f"'{arg}' is not available for {self.config.provider}. Available models: {', '.join(available)}\n"
            if self.config.provider == "ollama":
                msg += f"To get it: ollama pull {arg}"
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
            ui.print_error(f"Invalid provider '{arg}'. Options: {', '.join(valid_providers)}")
            return
            
        self.config.provider = arg
        if arg == "openai" and "gpt" not in self.config.model and "o1" not in self.config.model:
            self.config.model = "gpt-4o"
        elif arg == "anthropic" and "claude" not in self.config.model:
            self.config.model = "claude-3-5-sonnet-20240620"
            
        self.config.save()
        self.client = ClientFactory(self.config)
        
        ui.print_info(f"Switched provider to '{arg}'. Model set to '{self.config.model}'.")
        if not self.client.is_alive():
            ui.print_error(f"API key missing for {arg}. Set it with: /apikey {arg} <key>")

    def _handle_apikey_command(self, arg: str) -> None:
        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            ui.print_error("Usage: /apikey <provider> <key>")
            return
            
        provider, key = parts[0].lower(), parts[1].strip()
        if provider == "openai":
            self.config.openai_api_key = key
        elif provider == "anthropic":
            self.config.anthropic_api_key = key
        else:
            ui.print_error("Invalid provider for apikey. Use 'openai' or 'anthropic'.")
            return
            
        self.config.save()
        ui.print_info(f"Saved API key for {provider}.")
        if self.config.provider == provider:
            self.client = ClientFactory(self.config)

    def _handle_system_command(self, arg: str) -> None:
        if not arg:
            ui.print_info(f"Current system prompt:\n{self.config.system_prompt}")
            return
        self.config.system_prompt = arg
        self.convo.system_prompt = arg
        self.config.save()
        ui.print_info("System prompt updated for this session and saved.")


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
