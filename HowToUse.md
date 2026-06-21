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
*   `/models` - Lists all available models for your current active provider.
*   `/model [name]` - Switches the active model. **Tip:** If you type `/model` without a name, an interactive numbered menu will appear, allowing you to easily pick any model and automatically switch providers!
*   `/system [prompt]` - Updates the system prompt for the current session and saves it as your new default. If no prompt is provided, it prints the current system prompt.
*   `/temperature [value]` - Sets the creativity level (between 0.0 and 2.0).
*   `/context [limit]` - Sets the maximum token limit for the conversation memory.
*   `/host [url]` - Sets the Ollama host URL (e.g. `http://localhost:11434`).

## Examples

**Changing Providers and API Keys:**
```text
> /provider openai
Switched provider to 'openai'. Model set to 'gpt-4o'.
Error: API key missing for openai. Set it with: /apikey openai <key>

> /apikey openai sk-12345...
Saved API key for openai.
```

**Changing the system prompt:**
```text
> /system You are a sarcastic programming expert.
System prompt updated for this session and saved.
```

**Switching models:**
```text
> /models
Locally available models:
  • llama3 (active)
  • mistral
  • codellama
  
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
