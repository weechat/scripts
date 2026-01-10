# -*- coding: utf-8 -*-
#
# tts_weechat.py - Zero-latency TTS integration with Piper/Speech-Dispatcher support
#
# Copyright (c) 2026 brhacket <https://github.com/brhacket>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# History:
# 2026-01-10, brhacket:
#     version 1.0: initial release
import weechat
import subprocess
import threading
import queue
import time
import os
import shutil
import re

weechat.register("tts_weechat", "brhacket", "1.0", "GPL3", "Zero-latency TTS with Piper/Speech-Dispatcher support", "", "")

# --- PATHS ---
SPD_PATH = shutil.which("spd-say")
SOUNDS = {
    "message": "/usr/share/sounds/freedesktop/stereo/message.oga",
    "bell": "/usr/share/sounds/freedesktop/stereo/bell.oga",
    "chime": "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "alert": "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"
}

# --- DEFAULTS ---
# These are saved in ~/.weechat/plugins.conf
DEFAULT_OPTIONS = {
    "mode": "off",             # off, auto, or [channel_name]
    "mute_level": "none",      # none, voice, all
    "sound_name": "chime",     # bell, chime, alert, message, off
    "ignore_me": "off",        # on/off
    "notify_content": "off",   # on/off
    "manual_nick": "",
    "debug": "off"             # on/off (Default is OFF)
}

# Init Config
for option, default_value in DEFAULT_OPTIONS.items():
    if not weechat.config_is_set_plugin(option):
        weechat.config_set_plugin(option, default_value)

def get_conf(key): return weechat.config_get_plugin(key)
def set_conf(key, value): weechat.config_set_plugin(key, value)

# --- GLOBAL STATE ---
speech_queue = queue.Queue()
CURRENT_BAR_TEXT = ""
UI_NEEDS_UPDATE = False
last_speaker_nick = ""
last_speak_time = 0

# EMOJI MAP
EMOJI_MAP = {
    ":)": "smiles", "(:": "smiles", ":-)": "smiles", "(-:": "smiles",
    ":D": "laughs", "xD": "laughs", "XD": "laughs", "Bd": "laughs",
    ":3": "cute face", "<3": "heart",
    ":(": "frowns", "):": "frowns", ">_<": "frustrated", ">:(": "angry",
    ":O": "surprised", "o_O": "confused", "??": "what?",
    ";)": "winks", ":P": "sticks tongue out", "^^": "happy", "T_T": "crying"
}

def debug_log(msg):
    if get_conf("debug") == "on":
        weechat.prnt("", f"{weechat.color('darkgray')}TTS-DBG: {msg}")

def clean_text_for_tts(text):
    text = re.sub(r'https?://\S+', 'sent a link.', text)
    words = text.split(" ")
    cleaned = []
    for w in words:
        cw = w.strip()
        cleaned.append(EMOJI_MAP.get(cw, w))
    return " ".join(cleaned)

def humanize_nick(nick):
    # MuddyMacey -> Muddy Macey
    nick = re.sub(r'[_|\-\.]', ' ', nick)
    nick = re.sub(r'([a-z])([A-Z])', r'\1 \2', nick)
    nick = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', nick)
    return nick.lower()

def process_smart_message(msg):
    # "Target: message" -> "to Target. message"
    parts = msg.split(':', 1)
    if len(parts) > 1:
        target = parts[0].strip()
        if " " not in target and len(target) > 0:
            rest = parts[1].strip()
            return f"to {humanize_nick(target)}. {rest}"
    return msg

# --- WORKER THREAD ---
def speech_worker():
    global CURRENT_BAR_TEXT, UI_NEEDS_UPDATE, last_speaker_nick, last_speak_time

    while True:
        try:
            # 1. BLOCKING WAIT
            nick, msg, is_background = speech_queue.get()
            if nick is None: break

            debug_log(f"Processing: {nick} -> {msg}")

            mute_level = get_conf("mute_level")
            if mute_level == "all":
                speech_queue.task_done()
                continue

            # 2. SOUND LOGIC
            sound_name = get_conf("sound_name")
            if is_background and sound_name in SOUNDS:
                try:
                    subprocess.run(["paplay", SOUNDS[sound_name]], stderr=subprocess.DEVNULL)
                    time.sleep(0.5)
                except: pass

            if mute_level == "voice":
                speech_queue.task_done()
                continue

            # 3. MEMORY RESET
            if (time.time() - last_speak_time) > 20:
                last_speaker_nick = ""

            # 4. PREPARE TEXT
            speak_nick = humanize_nick(nick)
            clean_msg = clean_text_for_tts(msg)
            processed_msg = process_smart_message(clean_msg)

            final_text = ""
            if nick == "System":
                final_text = msg
                last_speaker_nick = ""
            elif nick == last_speaker_nick:
                final_text = processed_msg
            else:
                if processed_msg.startswith("to "):
                    final_text = f"{speak_nick} says {processed_msg}"
                else:
                    final_text = f"{speak_nick} says. {processed_msg}"
                last_speaker_nick = nick

            last_speak_time = time.time()

            # 5. UI UPDATE
            visual = msg
            if len(visual) > 60: visual = visual[:60] + "..."
            CURRENT_BAR_TEXT = f"{nick}: {visual}"
            UI_NEEDS_UPDATE = True

            # 6. SPEAK
            debug_log(f"Speaking: '{final_text}'")
            if SPD_PATH:
                subprocess.run(
                    [SPD_PATH, "-w", final_text],
                    env=os.environ.copy(),
                    timeout=60
                )

        except Exception as e:
            debug_log(f"Error in worker: {e}")
            last_speaker_nick = ""
        finally:
            speech_queue.task_done()
            CURRENT_BAR_TEXT = ""
            UI_NEEDS_UPDATE = True

worker_thread = threading.Thread(target=speech_worker, daemon=True)
worker_thread.start()

# --- TIMER ---
def ui_updater_cb(data, remaining_calls):
    global UI_NEEDS_UPDATE
    if UI_NEEDS_UPDATE:
        weechat.bar_item_update("tts_now")
        UI_NEEDS_UPDATE = False
    return weechat.WEECHAT_RC_OK

weechat.hook_timer(100, 0, 0, "ui_updater_cb", "")

# --- COMMANDS ---

def cmd_ttsdbg(data, buffer, args):
    args = args.strip().lower()
    prefix = weechat.prefix("network")
    if args == "on":
        set_conf("debug", "on")
        weechat.prnt("", f"{prefix}TTS: 🐞 Debugging ENABLED.")
    elif args == "off":
        set_conf("debug", "off")
        weechat.prnt("", f"{prefix}TTS: 🐞 Debugging DISABLED.")
    else:
        weechat.prnt("", f"{prefix}TTS: Usage: /ttsdbg [on|off]")
    return weechat.WEECHAT_RC_OK

def cmd_listento(data, buffer, args):
    args = args.strip().lower()
    prefix = weechat.prefix("network")

    if args == "":
        current_name = weechat.buffer_get_string(buffer, "short_name")
        set_conf("mode", current_name)
        if get_conf("mute_level") != "none": set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🟢 Listening to '{current_name}' (Locked).")
    elif args == "auto":
        set_conf("mode", "auto")
        if get_conf("mute_level") != "none": set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🟢 Mode set to AUTO (Follows focus).")
    elif args == "off":
        set_conf("mode", "off")
        weechat.prnt("", f"{prefix}TTS: 🔴 Disabled.")
    else:
        set_conf("mode", args)
        if get_conf("mute_level") != "none": set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🟢 Listening to '{args}'.")
    return weechat.WEECHAT_RC_OK

def cmd_shh(data, buffer, args):
    args = args.strip().lower()
    prefix = weechat.prefix("network")
    if args == "all":
        set_conf("mute_level", "all")
        weechat.prnt("", f"{prefix}TTS: 🔇 Muted ALL.")
    elif args == "disable":
        set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🔊 Unmuted.")
    else:
        set_conf("mute_level", "voice")
        weechat.prnt("", f"{prefix}TTS: 🙊 Muted Voice.")
    return weechat.WEECHAT_RC_OK

def cmd_setsound(data, buffer, args):
    args = args.strip().lower()
    prefix = weechat.prefix("network")
    if args in SOUNDS or args == "off":
        set_conf("sound_name", args)
        weechat.prnt("", f"{prefix}TTS: Sound set to '{args}' (Background chats).")
        if args in SOUNDS: subprocess.run(["paplay", SOUNDS[args]], stderr=subprocess.DEVNULL)
    else:
        weechat.prnt("", f"{prefix}TTS: Unknown sound. Options: off, bell, chime, alert, message")
    return weechat.WEECHAT_RC_OK

def cmd_ignoreme(data, buffer, args):
    args = args.strip().lower()
    if args in ["on", "off"]:
        set_conf("ignore_me", args)
        weechat.prnt("", f"{weechat.prefix('network')}TTS: Ignore Me is {args.upper()}.")
    return weechat.WEECHAT_RC_OK

def cmd_iam(data, buffer, args):
    if args:
        set_conf("manual_nick", args.strip())
        weechat.prnt("", f"{weechat.prefix('network')}TTS: Identity set to '{args.strip()}'")
    return weechat.WEECHAT_RC_OK

def cmd_ttshelp(data, buffer, args):
    weechat.prnt("", "")
    weechat.prnt("", "--- TTS COMMANDS ---")
    weechat.prnt("", "/listento         -> Listen to CURRENT chat.")
    weechat.prnt("", "/listento auto    -> Auto-follow your focus.")
    weechat.prnt("", "/listento off     -> Disable TTS.")
    weechat.prnt("", "---")
    weechat.prnt("", "/shh              -> Mute Voice.")
    weechat.prnt("", "/shh all          -> Mute Everything.")
    weechat.prnt("", "/shh disable      -> Unmute.")
    weechat.prnt("", "---")
    weechat.prnt("", "/setsound chime   -> Set BG alert sound.")
    weechat.prnt("", "/ignoreme on/off  -> Ignore your own messages.")
    weechat.prnt("", "/ttsdbg on/off    -> View logs.")
    weechat.prnt("", "")
    return weechat.WEECHAT_RC_OK

weechat.hook_command("listento", "Set mode", "", "", "", "cmd_listento", "")
weechat.hook_command("shh", "Quick mute", "", "", "", "cmd_shh", "")
weechat.hook_command("setsound", "Bg Sound", "", "", "", "cmd_setsound", "")
weechat.hook_command("ignoreme", "Ignore self", "", "", "", "cmd_ignoreme", "")
weechat.hook_command("iam", "Set nick", "", "", "", "cmd_iam", "")
weechat.hook_command("ttsdbg", "Debug logs", "", "", "", "cmd_ttsdbg", "")
weechat.hook_command("ttshelp", "Show help", "", "", "", "cmd_ttshelp", "")

# --- BAR & HOOK ---
def update_tts_bar(data, item, window):
    if CURRENT_BAR_TEXT: return f"{weechat.color('yellow')}🔊 {CURRENT_BAR_TEXT}"
    return ""
weechat.bar_item_new("tts_now", "update_tts_bar", "")

def tts_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    if displayed == "0": return weechat.WEECHAT_RC_OK

    mute_level = get_conf("mute_level")
    if mute_level == "all": return weechat.WEECHAT_RC_OK

    listen_mode = get_conf("mode")
    if listen_mode == "off": return weechat.WEECHAT_RC_OK

    has_valid_tag = "notify_message" in tags or "irc_privmsg" in tags
    if not has_valid_tag: return weechat.WEECHAT_RC_OK

    if "irc_server" in tags or "irc_quit" in tags or "irc_join" in tags or "irc_mode" in tags:
        return weechat.WEECHAT_RC_OK

    clean_nick = prefix.lstrip('@+~%&')
    if clean_nick in ["root", "admin", "*", "--"] or "@chat" in prefix:
        return weechat.WEECHAT_RC_OK

    buf_name = weechat.buffer_get_string(buffer, "short_name")
    is_highlight = (int(highlight) == 1)

    is_active_read = False
    if listen_mode == "auto":
        if buffer == weechat.current_buffer(): is_active_read = True
    elif listen_mode == buf_name:
        is_active_read = True

    final_message = ""
    target_nick = clean_nick
    is_bg_event = False

    if is_active_read:
        final_message = message
        is_bg_event = False
    else:
        if not is_highlight: return weechat.WEECHAT_RC_OK
        is_bg_event = True
        notify_content = get_conf("notify_content")
        if notify_content == "on":
            final_message = f"In {buf_name}. {message}"
        else:
            target_nick = "System"
            final_message = f"New message in {buf_name}."

    my_current_nick = weechat.buffer_get_string(buffer, "localvar_nick")
    is_me = False
    if clean_nick == my_current_nick: is_me = True
    manual_nick = get_conf("manual_nick")
    if manual_nick and clean_nick == manual_nick: is_me = True

    if is_me and get_conf("ignore_me") == "on": return weechat.WEECHAT_RC_OK

    # Add to Queue
    speech_queue.put((target_nick, final_message, is_bg_event))
    return weechat.WEECHAT_RC_OK

weechat.hook_print("", "", "", 1, "tts_cb", "")
