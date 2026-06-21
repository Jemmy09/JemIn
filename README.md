# JemIn

**JemIn** is an AI assistant for the terminal. Initially built for local offline use with [Ollama](https://ollama.com/), it now also seamlessly supports cloud models like OpenAI's ChatGPT and Anthropic's Claude. It provides a rich, interactive chat experience right in your console.

## Features
- **Local & Cloud Providers:** Connect to local Ollama models for 100% privacy, or switch to OpenAI/Anthropic for state-of-the-art reasoning.
- **Rich Terminal UI:** Beautiful markdown rendering, syntax highlighting, and streaming responses using the `rich` library.
- **Conversation Management:** Save your chats, view history, and reload past conversations.
- **Model Switching:** Easily switch between different local models pulled via Ollama on the fly.
- **Custom System Prompts:** Define and update the system prompt dynamically to adjust the AI's behavior.

## Installation

### Prerequisites
1. **Python 3.9+**
2. **Ollama (Optional):** If you want to run local models, you must have [Ollama](https://ollama.com/) installed and running locally.
3. **API Keys (Optional):** If you want to use OpenAI or Anthropic, you'll need their respective API keys.

### Setup
Clone the repository and install the dependencies:

```bash
git clone https://github.com/Jemmy09/JemIn.git
cd JemIn
pip install -e .
```

Alternatively, you can just install the requirements:
```bash
pip install -r requirements.txt
```

## Running JemIn

Once installed, simply run:
```bash
jemin
```
*(If you installed via `requirements.txt` instead of `setup.py`, use `python jemin.py`)*

On your first run, a setup wizard will guide you through connecting to Ollama, selecting a default model, and setting up an optional initial system prompt.

## Uninstallation

If you ever wish to completely remove JemIn and all its saved configuration and chat history, we have provided easy uninstallation scripts.

### Windows
Double-click `uninstall.bat` in the project folder, or run it from your terminal:
```bash
uninstall.bat
```

### Mac / Linux / Android
Run the shell script:
```bash
chmod +x uninstall.sh
./uninstall.sh
```

## Usage

See [HowToUse.md](HowToUse.md) for a detailed list of commands and usage instructions.

## License
MIT
