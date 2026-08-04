import weechat
import json

"""
Ollama Bot for WeeChat (Non-blocking version)

This script automatically responds to mentions in channels and private messages using an Ollama LLM running locally.

Features:
- Responds to mentions in channels.
- Can respond to private messages if enabled.
- Allows manual queries using the /ollama command.
- Configurable via WeeChat /set commands.
- Uses hook_url for non-blocking HTTP requests.

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
SCRIPT_NAME = "ollama"
SCRIPT_AUTHOR = "teraflops"
SCRIPT_VERSION = "2.1"
SCRIPT_LICENSE = "MIT"
SCRIPT_DESC = "Automatically responds to mentions using Ollama and allows manual queries, including PMs"
OLLAMA_API_URL = "http://localhost:11434/api/generate"

weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "")

def setup_config():
    if not weechat.config_is_set_plugin("highlight_response"):
        weechat.config_set_plugin("highlight_response", "on")
    if not weechat.config_is_set_plugin("pm_response"):
        weechat.config_set_plugin("pm_response", "off")
setup_config()

def ask_ollama_async(prompt, buffer, prefix=""):
    payload = json.dumps({
        "model": "gemma2:2b",
        "prompt": prompt,
        "stream": False
    })

    curl_path = "/usr/bin/curl"  # If curl is elsewhere, adjust this path
    escaped_payload = payload.replace('"', '\\"')

    cmd = (
        f"{curl_path} -s -X POST "
        "-H 'Content-Type: application/json' "
        f'--data \"{escaped_payload}\" {OLLAMA_API_URL}'
    )

    user_data = f"{buffer}||{prefix}"
    # This is the non-blocking call that uses hook_process_hashtable:
    weechat.hook_process_hashtable(
        cmd,
        {"timeout": "10000"},  # 10s
        10000,
        "ollama_response_callback",
        user_data
    )

def ollama_response_callback(data, command, return_code, out, err):
    buffer, prefix = data.split("||", 1)

    if return_code is None or return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        response = "[Ollama] Error executing request."
    elif out.strip() == "":
        response = "[Ollama] Empty response from Ollama."
    else:
        try:
            parsed = json.loads(out)
            response = parsed.get("response", "[Ollama] No 'response' field in reply.")
        except Exception:
            response = "[Ollama] Error parsing server response."

    if prefix:
        weechat.command(buffer, f"/msg {prefix} {response}")
    else:
        weechat.command(buffer, f"/say {response}")

    return weechat.WEECHAT_RC_OK

def command_ollama(data, buffer, args):
    if not args:
        weechat.prnt(buffer, "[Ollama] Usage: /ollama <question>")
        return weechat.WEECHAT_RC_OK

    ask_ollama_async(args, buffer)
    return weechat.WEECHAT_RC_OK

def message_callback(data, buffer, date, tags, displayed, highlight, prefix, message):
    if weechat.config_get_plugin("highlight_response") == "off":
        return weechat.WEECHAT_RC_OK

    buffer_type = weechat.buffer_get_string(buffer, "localvar_type")
    is_private = buffer_type == "private"
    username = weechat.info_get("irc_nick", "")
    is_mentioned = f"@{username.lower()}" in message.lower()

    # Skip PM if pm_response=off
    if is_private and weechat.config_get_plugin("pm_response") == "off":
        return weechat.WEECHAT_RC_OK

    # Only respond to PM if ends with '?'
    if is_private and not message.strip().endswith("?"):
        return weechat.WEECHAT_RC_OK

    # In channels, respond only if highlight or explicit mention
    if not is_private and not is_mentioned and not int(highlight):
        return weechat.WEECHAT_RC_OK

    ask_ollama_async(message, buffer, prefix if is_private else "")
    return weechat.WEECHAT_RC_OK

def config_callback(data, option, value):
    weechat.prnt("", f"[Ollama] Configuration changed: {option} = {value}")
    return weechat.WEECHAT_RC_OK

weechat.config_set_desc_plugin("highlight_response", "Automatically respond to mentions in channels (on/off)")
weechat.config_set_desc_plugin("pm_response", "Automatically respond to private messages (on/off)")
weechat.hook_config("plugins.var.python.ollama.highlight_response", "config_callback", "")
weechat.hook_config("plugins.var.python.ollama.pm_response", "config_callback", "")
weechat.hook_command(
    "ollama",
    "Ask something to Ollama",
    "<question>",
    "Example: /ollama What is Python?",
    "",
    "command_ollama",
    ""
)
weechat.hook_print("", "notify_highlight", "", 1, "message_callback", "")
weechat.hook_print("", "notify_message", "", 1, "message_callback", "")
weechat.hook_print("", "notify_private", "", 1, "message_callback", "")

