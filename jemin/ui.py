"""
Terminal UI for Jem In, built on `rich`.

Keeps all presentation logic in one place: banner, message panels,
streaming render, status/error messages, and the slash-command help table.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.box import ROUNDED

console = Console()

USER_COLOR = "bright_cyan"
ASSISTANT_COLOR = "bright_green"
ACCENT_COLOR = "magenta"
ERROR_COLOR = "bright_red"
DIM = "grey58"

BANNER = r"""
   ___                  ____
  |_  |                |_  _|
    | | ___ _ __ ___      | |  _ __
    | |/ _ \ '_ ` _ \     | | | '_ \
/\__/ /  __/ | | | | |   _| |_| | | |
\____/ \___|_| |_| |_|  |_____|_| |_|
"""


def print_banner(provider: str, model: str, host: str, online: bool) -> None:
    if provider == "ollama":
        status = (
            f"[bold green]\u25cf running[/bold green]  [{DIM}]({host})[/{DIM}]"
            if online
            else f"[bold red]\u25cf not detected[/bold red]  [{DIM}]({host})[/{DIM}]"
        )
        tagline = "Local AI assistant \u00b7 100% offline \u00b7 runs on your machine"
    else:
        status = "[bold green]\u25cf active[/bold green]" if online else "[bold red]\u25cf missing api key[/bold red]"
        tagline = "Cloud AI assistant \u00b7 connected to internet"

    body = Text.from_markup(
        f"[bold {ACCENT_COLOR}]{BANNER}[/bold {ACCENT_COLOR}]\n"
        f"[bold]{tagline}[/bold]\n\n"
        f"Provider: [bold]{provider}[/bold]\n"
        f"Model:    [bold]{model}[/bold]\n"
        f"Status:   {status}\n\n"
        f"[{DIM}]Type your message and press Enter. Type /help for commands.[/{DIM}]"
    )
    console.print(Panel(body, border_style=ACCENT_COLOR, box=ROUNDED, padding=(1, 3)))


def print_user_message(text: str) -> None:
    console.print(
        Panel(
            Text(text),
            title="[bold]You[/bold]",
            title_align="left",
            border_style=USER_COLOR,
            box=ROUNDED,
            padding=(0, 2),
        )
    )


class StreamingAssistantPanel:
    """
    Renders the assistant's reply incrementally inside a live-updating
    panel, so the user sees text appear as it's generated rather than
    waiting for the full response.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._buffer = ""
        self._live: Live | None = None

    def __enter__(self) -> "StreamingAssistantPanel":
        self._live = Live(self._render(), console=console, refresh_per_second=12)
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._live:
            self._live.update(self._render(final=True))
            self._live.__exit__(exc_type, exc, tb)

    def update(self, chunk: str) -> None:
        self._buffer += chunk
        if self._live:
            self._live.update(self._render())

    def _render(self, final: bool = False) -> Panel:
        content = Markdown(self._buffer) if self._buffer.strip() else Text(
            "thinking\u2026", style=DIM
        )
        title = f"[bold]Jem In[/bold] [{DIM}]\u00b7 {self.model_name}[/{DIM}]"
        return Panel(
            content,
            title=title,
            title_align="left",
            border_style=ASSISTANT_COLOR,
            box=ROUNDED,
            padding=(0, 2),
        )

    @property
    def text(self) -> str:
        return self._buffer


def print_error(message: str) -> None:
    console.print(Panel(Text(message), title="[bold]Error[/bold]", border_style=ERROR_COLOR, box=ROUNDED))


def print_info(message: str) -> None:
    console.print(f"[{ACCENT_COLOR}]\u203a[/{ACCENT_COLOR}] {message}")


def print_help() -> None:
    table = Table(title="Jem In \u2014 Commands", box=ROUNDED, border_style=ACCENT_COLOR, show_lines=False)
    table.add_column("Command", style="bold cyan", no_wrap=True)
    table.add_column("Description")
    rows = [
        ("/help", "Show this list of commands"),
        ("/new", "Start a new conversation (clears current context)"),
        ("/save", "Save the current conversation to disk"),
        ("/load [number]", "Load a previously saved conversation"),
        ("/history", "List saved conversations"),
        ("/delete [number]", "Delete a saved conversation"),
        ("/provider [name]", "Switch provider (ollama, openai, anthropic)"),
        ("/apikey [provider] [key]", "Set API key for a cloud provider"),
        ("/model [name]", "Show current model, or switch to a different local model"),
        ("/models", "List models available locally via Ollama"),
        ("/system [text]", "Show or change the system prompt for this session"),
        ("/temperature [value]", "Set the creativity level (0.0 to 2.0)"),
        ("/context [limit]", "Set the max context limit in tokens"),
        ("/host [url]", "Set the Ollama host URL"),
        ("/clear", "Clear the screen"),
        ("/exit, /quit", "Exit Jem In"),
    ]
    for cmd, desc in rows:
        table.add_row(cmd, desc)
    console.print(table)


def prompt_user() -> str:
    console.print(f"[bold {USER_COLOR}]you \u203a[/bold {USER_COLOR}] ", end="")
    return input()
