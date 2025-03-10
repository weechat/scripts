import weechat
import requests
import json

"""
Ollama Bot for WeeChat

This script automatically responds to mentions in channels and private messages using an Ollama LLM running locally.

Features:
- Responds to mentions in channels.
- Can respond to private messages if enabled.
- Allows manual queries using the /ollama command.
- Configurable via WeeChat /set commands.

Usage:
- To ask a question manually:
  /ollama What is Python?

- To enable or disable automatic responses in channels:
  /set plugins.var.python.ollama.highlight_response on  # Enable responses in channels
  /set plugins.var.python.ollama.highlight_response off # Disable responses in channels

- To enable or disable automatic responses in private messages:
  /set plugins.var.python.ollama.pm_response on  # Enable PM responses
  /set plugins.var.python.ollama.pm_response off # Disable PM responses

Dependencies:
- Requires an Ollama server running locally at http://localhost:11434/api/generate
"""

# Script metadata
SCRIPT_NAME = "ollama"
SCRIPT_AUTHOR = "teraflops"
SCRIPT_VERSION = "2.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Automatically responds to mentions using Ollama and allows manual queries, including PMs"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Register the script
weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")

# Script configuration in Weechat
def setup_config():
    if not weechat.config_is_set_plugin("highlight_response"):
        weechat.config_set_plugin("highlight_response", "on")  # Enable auto-responses by default
    if not weechat.config_is_set_plugin("pm_response"):
        weechat.config_set_plugin("pm_response", "off")  # Disable PM responses by default
setup_config()

def ask_ollama(message):
    """Send a query to Ollama and return the complete response."""
    try:
        data = {"model": "gemma", "prompt": message, "stream": False}
        headers = {"Content-Type": "application/json"}

        response = requests.post(
            OLLAMA_API_URL,
            json=data,
            headers=headers,
            verify=False  # Change to True if you use a valid certificate
        )

        if response.status_code != 200:
            return f"Error {response.status_code}: {response.text}"

        response_json = response.json()
        return response_json.get("response", "No response received from Ollama.")
    
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Ollama: {str(e)}"

def command_ollama(data, buffer, args):
    """Command /ollama to manually ask Ollama a question."""
    if not args:
        weechat.prnt(buffer, "[Ollama] Usage: /ollama <question>")
        return weechat.WEECHAT_RC_OK
    
    response = ask_ollama(args)
    weechat.prnt(buffer, f"[Ollama] {response}")
    return weechat.WEECHAT_RC_OK

def message_callback(data, buffer, date, tags, displayed, highlight, prefix, message):
    """Detect mentions in channels or private messages and respond automatically with Ollama."""
    
    if weechat.config_get_plugin("highlight_response") == "off":
        return weechat.WEECHAT_RC_OK

    buffer_type = weechat.buffer_get_string(buffer, "localvar_type")
    is_private = buffer_type == "private"
    username = weechat.info_get("irc_nick", "")  # Get the current IRC username
    is_mentioned = f"@{username.lower()}" in message.lower()  # Ensure @username is explicitly mentioned

    # Ignore private messages if pm_response is off
    if is_private and weechat.config_get_plugin("pm_response") == "off":
        return weechat.WEECHAT_RC_OK

    # Only respond in private messages if it's a direct question
    if is_private and not message.strip().endswith("?"):
        return weechat.WEECHAT_RC_OK

    # Only respond in channels if explicitly mentioned or highlighted
    if not is_private and not is_mentioned and not int(highlight):
        return weechat.WEECHAT_RC_OK

    response = ask_ollama(message)
    
    if is_private:
        weechat.command(buffer, f"/msg {prefix} {response}")  # Reply to private message
    else:
        weechat.command(buffer, f"/say {response}")  # Reply in the channel

    return weechat.WEECHAT_RC_OK


def config_callback(data, option, value):
    """Callback for Weechat configuration changes."""
    weechat.prnt("", f"[Ollama] Configuration changed: {option} = {value}")
    return weechat.WEECHAT_RC_OK

# Register configuration with /set
weechat.config_set_desc_plugin("highlight_response", "Automatically respond to mentions in channels (on/off)")
weechat.config_set_desc_plugin("pm_response", "Automatically respond to private messages (on/off)")
weechat.hook_config("plugins.var.python.ollama.highlight_response", "config_callback", "")
weechat.hook_config("plugins.var.python.ollama.pm_response", "config_callback", "")

# Register commands and hooks
weechat.hook_command("ollama", "Ask something to Ollama", "<question>", "Example: /ollama What is Python?", "", "command_ollama", "")
weechat.hook_print("", "notify_highlight", "", 1, "message_callback", "")
weechat.hook_print("", "notify_message", "", 1, "message_callback", "")
weechat.hook_print("", "notify_private", "", 1, "message_callback", "")

