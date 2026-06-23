# How to Use JemIn

JemIn is designed to be an intuitive terminal chat interface. Once you start the application by running `jemin` (or `python jemin.py`), you'll be dropped into an interactive chat loop.

## Basic Chatting
Simply type your message and press `Enter`. The assistant will stream its response back to you using rich text rendering, supporting markdown and code blocks natively.

## Slash Commands

JemIn uses slash (`/`) commands to manage the session, configuration, and conversation history. Here is a list of all available commands:

### Session & App Control
*   `/help` - Prints the help menu with all available commands.
*   `/clear` - Clears the terminal screen.
*   `/exit` or `/quit` - Exits the JemIn application.

### Conversation Management
*   `/new` - Starts a brand new conversation, clearing the current context.
*   `/save` - Saves the current conversation to a file for later retrieval.
*   `/history` - Lists all your previously saved conversations (most recent first).
*   `/load <number>` - Loads a specific saved conversation. Use `/history` to find the number.
*   `/delete <number>` - Deletes a specific saved conversation from your history.

### Model, Configuration & Providers
*   `/provider [name]` - Switches your active AI provider (`ollama`, `openai`, `anthropic`).
*   `/apikey [provider] [key]` - Sets the API key for a cloud provider. Keys are saved locally.
*   `/signin` or `/login` - Securely sign in to your cloud AI provider. Prompts you interactively (masking the input) to prevent the API key from leaking in cleartext shell history. Supports `openai` / `chatgpt` and `anthropic` / `claude` aliases.
*   `/models` - Lists all available models across all configured providers (Ollama, OpenAI, Anthropic).
*   `/model [name]` - Switches the active model. **Tip:** If you type `/model` without a name, an interactive numbered menu will appear, allowing you to easily pick any model and automatically switch providers!
*   `/system [prompt]` - Updates the system prompt for the current session and saves it as your new default. If no prompt is provided, it prints the current system prompt.
*   `/temperature [value]` - Sets the creativity level (between 0.0 and 2.0).
*   `/context [limit]` - Sets the maximum token limit for the conversation memory.
*   `/host [url]` - Sets the Ollama host URL (e.g. `http://localhost:11434`).

## Examples

**Signing in securely to a Provider:**
```text
> /signin openai

⚠️ Sign in to ChatGPT / OpenAI
An API key is required to use this provider.
  Get your key at: https://platform.openai.com/api-keys
  Key format: sk-...
Your key is stored locally in ~/.jemin/config.json
It is never sent anywhere except the provider's own API.

Enter API key (hidden, press Enter to cancel): ******
✔ Signed in to openai. API key saved.
```

**Changing the system prompt:**
```text
> /system You are a sarcastic programming expert.
System prompt updated for this session and saved.
```

**Switching models:**
```text
> /models

OLLAMA
  • llama3.2:3b (active)
  • mistral

OPENAI
  No models found.

ANTHROPIC
  No models found.

> /model mistral
Switched model to 'mistral'.
```

**Saving and loading chats:**
```text
> /save
Saved conversation to .../conversations/chat_20231024_153022.json

> /new
Started a new conversation.

> /history
Saved conversations (most recent first):
  [1] chat_20231024_153022
  [2] chat_20231023_091500

> /load 1
Loaded conversation 'chat_20231024_153022' (4 messages).
```
