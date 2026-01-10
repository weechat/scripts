# -*- coding: utf-8 -*-
#
# smarter_tts.py - Zero-latency TTS with Auto-Discovery Sounds
#
# Copyright (c) 2025 brhacket <https://github.com/brhacket>
#
# This file is part of WeeChat, the extensible chat client.
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
# SPDX-License-Identifier: GPL-3.0-or-later
#
# History:
# 2025-01-10, brhacket:
#     version 1.0: initial release
#     version 1.6: added /ttsblock helper, auto-discovery, improved help

import weechat
import subprocess
import threading
import queue
import time
import os
import shutil
import re

weechat.register("smarter_tts", "brhacket", "1.6", "GPL3", "Zero-latency TTS with Auto-Discovery", "", "")

# --- PATHS ---
SPD_PATH = shutil.which("spd-say")

# --- DEFAULTS ---
DEFAULT_OPTIONS = {
    "mode": "off",             
    "mute_level": "none",      
    "ignore_me": "off",        
    "notify_content": "off",   
    "debug": "off",
    "ignore_nicks": "root,admin,system,*", 
    "ignore_channels": "",
    "sound_player": "paplay",
    "sound_notification": "off",
    "path_chime": "",
    "path_bell": "",
    "path_alert": "",
    "path_message": ""
}

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
    text = re.sub(r'\x03(?:\d{1,2}(?:,\d{1,2})?)?|\x02|\x1F|\x16|\x0F', '', text)
    text = re.sub(r'[\u2500-\u257F\u2580-\u259F]+', '', text)
    words = text.split(" ")
    cleaned = []
    for w in words:
        cw = w.strip()
        cleaned.append(EMOJI_MAP.get(cw, w))
    return " ".join(cleaned)

def humanize_nick(nick):
    nick = re.sub(r'[_|\-\.]', ' ', nick)
    nick = re.sub(r'([a-z])([A-Z])', r'\1 \2', nick)
    nick = re.sub(r'([a-zA-Z])([0-9])', r'\1 \2', nick)
    return nick.lower()

def process_smart_message(msg):
    parts = msg.split(':', 1)
    if len(parts) > 1:
        target = parts[0].strip()
        if " " not in target and len(target) > 0:
            rest = parts[1].strip()
            return f"to {humanize_nick(target)}. {rest}"
    return msg

# --- AUTO DISCOVERY ---
def find_best_sound(keywords):
    base_dir = "/usr/share/sounds"
    best_match = ""
    if not os.path.exists(base_dir): return ""
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            for key in keywords:
                if key in file.lower():
                    full_path = os.path.join(root, file)
                    if not best_match: best_match = full_path
                    elif ".oga" in file and ".oga" not in best_match: best_match = full_path 
                    elif "stereo" in root and "stereo" not in best_match: best_match = full_path
    return best_match

def run_auto_discovery(silent=False):
    if not silent: weechat.prnt("", f"{weechat.prefix('network')}TTS: 🔍 Scanning system for sound files...")
    targets = {
        "path_bell": ["bell", "glass"],
        "path_chime": ["complete", "service-login", "ready", "startup"],
        "path_alert": ["alarm", "alert", "error", "warning"],
        "path_message": ["message", "click", "notification"]
    }
    count = 0
    for key, kws in targets.items():
        if get_conf(key) == "":
            path = find_best_sound(kws)
            if path:
                set_conf(key, path)
                count += 1
    if not silent and count > 0:
        weechat.prnt("", f"{weechat.prefix('network')}TTS: ✅ Configured {count} sounds.")

# --- WORKER THREAD ---
def speech_worker():
    global CURRENT_BAR_TEXT, UI_NEEDS_UPDATE, last_speaker_nick, last_speak_time
    
    while True:
        try:
            nick, msg, is_background = speech_queue.get()
            if nick is None: break 

            debug_log(f"Processing: {nick} -> {msg}")

            mute_level = get_conf("mute_level")
            if mute_level == "all":
                speech_queue.task_done()
                continue

            selected_sound = get_conf("sound_notification")
            if is_background and selected_sound != "off":
                player = get_conf("sound_player")
                sound_path = get_conf(f"path_{selected_sound}")
                if sound_path and os.path.exists(sound_path) and shutil.which(player):
                    try:
                        subprocess.run([player, sound_path], stderr=subprocess.DEVNULL)
                        time.sleep(0.5)
                    except: pass

            if mute_level == "voice":
                speech_queue.task_done()
                continue

            if (time.time() - last_speak_time) > 20: last_speaker_nick = ""

            speak_nick = humanize_nick(nick)
            clean_msg = clean_text_for_tts(msg)
            
            if not clean_msg.strip():
                debug_log("Skipping empty/ASCII message")
                speech_queue.task_done()
                continue

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

            visual = msg 
            if len(visual) > 60: visual = visual[:60] + "..."
            CURRENT_BAR_TEXT = f"{nick}: {visual}"
            UI_NEEDS_UPDATE = True

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

def ui_updater_cb(data, remaining_calls):
    global UI_NEEDS_UPDATE
    if UI_NEEDS_UPDATE:
        weechat.bar_item_update("tts_now")
        UI_NEEDS_UPDATE = False
    return weechat.WEECHAT_RC_OK

weechat.hook_timer(100, 0, 0, "ui_updater_cb", "")

if get_conf("path_chime") == "":
    t = threading.Thread(target=run_auto_discovery, args=(False,), daemon=True)
    t.start()

# --- COMMANDS ---

def cmd_ttshelp(data, buffer, args):
    weechat.prnt("", "")
    weechat.prnt("", f"{weechat.color('yellow')}--- SMARTER TTS HELP (v1.6) ---")
    
    weechat.prnt("", f"\n{weechat.color('bold')}🎧 ACTIVATION MODES{weechat.color('reset')}")
    weechat.prnt("", "  /listento          -> Locks TTS to the CURRENT window.")
    weechat.prnt("", "  /listento auto     -> Reads whatever window you look at.")
    weechat.prnt("", "  /listento all      -> Reads EVERY message from EVERY channel.")
    weechat.prnt("", "  /listento off      -> Disable TTS.")

    weechat.prnt("", f"\n{weechat.color('bold')}🔇 SILENCE & PRIVACY{weechat.color('reset')}")
    weechat.prnt("", "  /shh               -> Mutes Voice only. (Sounds stay on).")
    weechat.prnt("", "  /shh all           -> Total Silence.")
    weechat.prnt("", "  /ignoreme on       -> Don't read messages I type.")

    weechat.prnt("", f"\n{weechat.color('bold')}🔔 NOTIFICATIONS{weechat.color('reset')}")
    weechat.prnt("", "  /setsound [type]   -> chime, bell, alert, off")
    weechat.prnt("", "  /ttsdetect         -> Re-scan system for sound files.")

    weechat.prnt("", f"\n{weechat.color('bold')}⚙️ BLOCKING{weechat.color('reset')}")
    weechat.prnt("", "  /ttsblock nick [name]    -> Block a specific user/bot.")
    weechat.prnt("", "  /ttsblock chan [name]    -> Block a specific channel.")
    weechat.prnt("", "  /ttsdbg on               -> Show debug logs.")
    weechat.prnt("", "")
    return weechat.WEECHAT_RC_OK

def cmd_ttsblock(data, buffer, args):
    parts = args.strip().split(" ")
    if len(parts) < 2:
        weechat.prnt("", f"{weechat.prefix('network')}Usage: /ttsblock [nick|chan] [name]")
        return weechat.WEECHAT_RC_OK
    
    target_type = parts[0].lower()
    target_name = parts[1]
    
    if target_type.startswith("n"):
        current = get_conf("ignore_nicks")
        if target_name not in current.split(","):
            set_conf("ignore_nicks", f"{current},{target_name}".strip(","))
            weechat.prnt("", f"{weechat.prefix('network')}TTS: Blocked nick '{target_name}'")
    elif target_type.startswith("c"):
        current = get_conf("ignore_channels")
        if target_name not in current.split(","):
            set_conf("ignore_channels", f"{current},{target_name}".strip(","))
            weechat.prnt("", f"{weechat.prefix('network')}TTS: Blocked channel '{target_name}'")
            
    return weechat.WEECHAT_RC_OK

def cmd_ttsdetect(data, buffer, args):
    t = threading.Thread(target=run_auto_discovery, args=(False,), daemon=True)
    t.start()
    return weechat.WEECHAT_RC_OK

def cmd_ttsdbg(data, buffer, args):
    if args == "on": set_conf("debug", "on"); weechat.prnt("", "TTS: Debug ON")
    elif args == "off": set_conf("debug", "off"); weechat.prnt("", "TTS: Debug OFF")
    return weechat.WEECHAT_RC_OK

def cmd_listento(data, buffer, args):
    args = args.strip().lower()
    prefix = weechat.prefix("network")
    if args == "":
        current = weechat.buffer_get_string(buffer, "short_name")
        set_conf("mode", current)
        if get_conf("mute_level") != "none": set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🟢 Listening to '{current}'")
    elif args == "auto":
        set_conf("mode", "auto")
        if get_conf("mute_level") != "none": set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🟢 Mode AUTO")
    elif args == "all":
        set_conf("mode", "all")
        if get_conf("mute_level") != "none": set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🟣 Mode ALL")
    elif args == "off":
        set_conf("mode", "off")
        weechat.prnt("", f"{prefix}TTS: 🔴 Disabled")
    else:
        set_conf("mode", args)
        if get_conf("mute_level") != "none": set_conf("mute_level", "none")
        weechat.prnt("", f"{prefix}TTS: 🟢 Listening to '{args}'")
    return weechat.WEECHAT_RC_OK

def cmd_shh(data, buffer, args):
    if args == "all": set_conf("mute_level", "all"); weechat.prnt("", "TTS: Mute ALL")
    elif args == "disable": set_conf("mute_level", "none"); weechat.prnt("", "TTS: Unmuted")
    else: set_conf("mute_level", "voice"); weechat.prnt("", "TTS: Mute Voice")
    return weechat.WEECHAT_RC_OK

def cmd_setsound(data, buffer, args):
    if args in ["chime", "bell", "alert", "message", "off"]:
        set_conf("sound_notification", args)
        weechat.prnt("", f"TTS: Sound '{args}'")
        player = get_conf("sound_player")
        path = get_conf(f"path_{args}")
        if path and os.path.exists(path): subprocess.run([player, path], stderr=subprocess.DEVNULL)
    return weechat.WEECHAT_RC_OK

def cmd_ignoreme(data, buffer, args):
    if args in ["on", "off"]: set_conf("ignore_me", args); weechat.prnt("", f"TTS: IgnoreMe {args.upper()}")
    return weechat.WEECHAT_RC_OK

weechat.hook_command("listento", "Set mode", "", "", "", "cmd_listento", "")
weechat.hook_command("shh", "Quick mute", "", "", "", "cmd_shh", "")
weechat.hook_command("setsound", "Bg Sound", "", "", "", "cmd_setsound", "")
weechat.hook_command("ttsdetect", "Find sounds", "", "", "", "cmd_ttsdetect", "")
weechat.hook_command("ignoreme", "Ignore self", "", "", "", "cmd_ignoreme", "")
weechat.hook_command("ttsblock", "Block nick/chan", "", "", "", "cmd_ttsblock", "")
weechat.hook_command("ttsdbg", "Debug logs", "", "", "", "cmd_ttsdbg", "")
weechat.hook_command("ttshelp", "Show help", "", "", "", "cmd_ttshelp", "")

def update_tts_bar(data, item, window):
    if CURRENT_BAR_TEXT: return f"{weechat.color('yellow')}🔊 {CURRENT_BAR_TEXT}"
    return ""
weechat.bar_item_new("tts_now", "update_tts_bar", "")

def tts_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    if displayed == "0": return weechat.WEECHAT_RC_OK
    if get_conf("mute_level") == "all": return weechat.WEECHAT_RC_OK
    listen_mode = get_conf("mode")
    if listen_mode == "off": return weechat.WEECHAT_RC_OK

    if "notify_message" not in tags and "irc_privmsg" not in tags: return weechat.WEECHAT_RC_OK
    if "irc_server" in tags or "irc_quit" in tags: return weechat.WEECHAT_RC_OK

    clean_nick = prefix.lstrip('@+~%&')
    if "@chat" in prefix: return weechat.WEECHAT_RC_OK
    
    ignored_nicks = get_conf("ignore_nicks").split(",")
    if clean_nick in ignored_nicks: return weechat.WEECHAT_RC_OK

    buf_name = weechat.buffer_get_string(buffer, "short_name")
    ignored_chans = get_conf("ignore_channels").split(",")
    if buf_name in ignored_chans: return weechat.WEECHAT_RC_OK

    is_highlight = (int(highlight) == 1)
    current_focus = weechat.current_buffer()
    should_read_text = False
    
    if listen_mode == "all": should_read_text = True
    elif listen_mode == "auto":
        if buffer == current_focus: should_read_text = True
    elif listen_mode == buf_name: should_read_text = True

    final_message = ""
    target_nick = clean_nick
    is_bg_event = False

    if should_read_text:
        if buffer != current_focus and listen_mode == "all":
            final_message = f"In {buf_name}. {message}"
        else:
            final_message = message
        is_bg_event = False
    else:
        if not is_highlight: return weechat.WEECHAT_RC_OK
        is_bg_event = True
        if get_conf("notify_content") == "on":
            final_message = f"In {buf_name}. {message}"
        else:
            target_nick = "System"
            final_message = f"New message in {buf_name}."

    my_current_nick = weechat.buffer_get_string(buffer, "localvar_nick")
    is_me = False
    if clean_nick == my_current_nick: is_me = True

    if is_me and get_conf("ignore_me") == "on": return weechat.WEECHAT_RC_OK

    speech_queue.put((target_nick, final_message, is_bg_event))
    return weechat.WEECHAT_RC_OK

weechat.hook_print("", "", "", 1, "tts_cb", "")
