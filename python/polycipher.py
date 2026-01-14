# -*- coding: utf-8 -*-
#
# polycipher.py -- Advanced Poly-Cipher Suite: Axolotl (PFS) and FiSH (Blowfish)
#
# SPDX-FileCopyrightText: 2014-2016 David R. Andersen <k0rx@rxcomm.net>
# SPDX-FileCopyrightText: 2010-2016 Nicolai Lissner <nlissne@linux01.org>
# SPDX-FileCopyrightText: 2026 AnonShell
#
# SPDX-License-Identifier: GPL-3.0-or-later
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
# -----------------------------------------------------------------------------
#
# HISTORY:
#
# 0.6.4 (2026-01-14):
#     AnonShell:
#     - Ported to Python 3 (Requires 3.6+).
#     - Unified Axolotl (PFS) and FiSH (Blowfish) into a single plugin.
#     - Added Strict Mode (Fail-Secure) to prevent plaintext leaks.
#     - Added Anti-Forensics (Ghost Mode) to disable disk logging.
#     - Hardened input sanitization and fixed UTF-8 splitting issues.
#
# -----------------------------------------------------------------------------

"""
PolyCipher: The Ultimate Encryption Suite for WeeChat
=====================================================

This module integrates two powerful encryption protocols into the WeeChat IRC client:
**Axolotl** (Double Ratchet) for Perfect Forward Secrecy (PFS) and **FiSH** (Blowfish) for
legacy backward compatibility with mIRC/HexChat users.

Architecture
------------
The script operates by hooking into WeeChat's signal system:

1.  **Outgoing Messages (`irc_out_privmsg`):**
    Intercepts messages before they leave the client. It checks if a valid key or
    database exists for the target. If so, it encrypts the payload and replaces
    the original message.

2.  **Incoming Messages (`irc_in2_privmsg`):**
    Intercepts messages received from the server. It checks for protocol markers
    (like `+OK` for FiSH) or attempts to decrypt using the Ratchet session.
    If successful, it replaces the ciphertext with readable text for the display buffer.

Security Features
-----------------
* **Strict Mode (Fail-Secure):**
    If the encryption library fails (e.g., bug, key mismatch), the script blocks
    the message entirely rather than sending it in plain text.
    
* **Anti-Forensics (Ghost Mode):**
    Automatically detects when a buffer is using encryption and disables WeeChat's
    disk logging mechanism (`localvar_set_no_log`) for that specific buffer.
    This ensures decrypted text resides only in RAM, not on the hard drive.

Dependencies
------------
* ``weechat`` (Provided by the host process)
* ``pyaxo`` (For Axolotl ratchet logic)
* ``pycryptodome`` (For Blowfish CBC logic)
* ``libsodium`` (System library required by pyaxo)

Configuration
-------------
Settings are stored in ``plugins.var.python.polycipher.*``.

.. code-block:: text

    /set plugins.var.python.polycipher.strict_mode on
    /set plugins.var.python.polycipher.prevent_logging on

"""

import weechat
import os
import re
import sys
import binascii
import traceback
import struct
from binascii import b2a_base64, a2b_base64

# --- Import Capabilities ---
# We use a "capability flag" system here.
# Instead of crashing if a library is missing, we set a flag to False.
# This allows the script to load partially or at least alert the user
# nicely instead of throwing a traceback on startup.
CAPABILITY_AXOLOTL = False
CAPABILITY_FISH = False

try:
    from pyaxo import Axolotl
    CAPABILITY_AXOLOTL = True
except ImportError:
    pass

try:
    from Crypto.Cipher import Blowfish
    from Crypto.Util.Padding import pad, unpad
    CAPABILITY_FISH = True
except ImportError:
    pass

SCRIPT_NAME = "polycipher"
SCRIPT_AUTHOR = "AnonShell"
SCRIPT_VERSION = "0.6.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Advanced Poly-Cipher Suite: Axolotl (PFS) and FiSH (Blowfish) with Anti-Forensics capabilities."

# --- Configuration ---
script_options = {
    "message_indicator_axo": "(axo) ",
    "message_indicator_fish": "\x0303\x02(fish)\x0f ", 
    "statusbar_indicator_axo": "[AXO]",
    "statusbar_indicator_fish": "[FiSH]",
    "statusbar_color": "lightgreen",
    "default_password": "change_me_in_sec_data",
    "strict_mode": "on",       # Enforces security protocols
    "prevent_logging": "on",   # Disables disk logging for crypto buffers
    "verbose": "off",
    "fish_prefix": "+OK ",
}

weechat_dir = ""

# --- Utils ---
def log(msg, level=""):
    """
    Logs formatted messages to the main WeeChat buffer.
    
    This wrapper ensures that all output from this script is consistently
    prefixed with the script name, making debugging easier.

    :param str msg: The message content to display.
    :param str level: The severity level.
        * ``"error"``: Uses the WeeChat error prefix (usually red).
        * ``""`` (default): Uses the network prefix.
    """
    prefix = weechat.prefix("error") if level == "error" else weechat.prefix("network")
    weechat.prnt("", f"{prefix}{SCRIPT_NAME}: {msg}")

def debug(msg):
    """
    Logs debug information only if verbose mode is enabled.
    
    Use this for printing internal state, variable values, or flow tracing
    that is not relevant to the end-user during normal operation.

    :param str msg: The debug information to print.
    """
    if weechat.config_get_plugin("verbose") == "on":
        weechat.prnt("", f"{weechat.prefix('debug')}{SCRIPT_NAME}: {msg}")

def is_strict_mode():
    """
    Determines if Strict Mode (Fail-Secure) is active.
    
    **Fail-Secure Logic:**
    This function implements a "safety first" default. It returns ``True``
    (Strict Mode ON) for *any* configuration value except a case-insensitive
    "off".
    
    This protects the user if the configuration file is missing, corrupt,
    or contains typos (e.g., "onn", "true", "1").

    :return: ``True`` if strict mode is enforcing security, ``False`` otherwise.
    :rtype: bool
    """
    val = weechat.config_get_plugin("strict_mode")
    return val.lower() != "off"

def get_axolotl_db_path(username):
    """
    Generates a secure, sanitized filesystem path for an Axolotl database.
    
    **Security Mechanism:**
    This function creates a filename derived from the **hex-encoded** username.
    
    * **Input:** ``User|Name``
    * **Hex:** ``557365727c4e616d65``
    * **Output:** ``.../axolotl_557365727c4e616d65.db``
    
    **Why?**
    IRC nicknames can contain characters that are dangerous on file systems
    (like ``/``, ``\``, ``:``, or even ``..`` for path traversal). Encoding ensures
    the filename is always safe alphanumeric ASCII.

    :param str username: The nickname of the communication partner.
    :return: Absolute path to the SQLite database file.
    :rtype: str or None
    """
    try:
        if not username: return None
        safe_name = binascii.hexlify(username.encode('utf-8')).decode('ascii')
    except Exception:
        safe_name = "unknown"
    return os.path.join(weechat_dir, f"axolotl_{safe_name}.db")

def get_key(target, method="axo"):
    """
    Retrieves the decryption key/passphrase for a given target.
    
    This acts as an abstraction layer over WeeChat's ``sec.conf`` (Secure Vault).
    Instead of storing passwords in plain text variables, we fetch them
    dynamically from the vault.

    **Lookup Strategy:**
    1.  Look for a specific key: ``sec.data.axolotl_pass_nickname``
    2.  (Axolotl only) Fallback to global default: ``sec.data.axolotl_default_pass``

    :param str target: The channel name (e.g., ``#lobby``) or nickname.
    :param str method: The protocol identifier (``"axo"`` or ``"fish"``).
    :return: The plaintext password string, or ``None`` if not set.
    :rtype: str or None
    """
    if not target: return None
    prefix = "axolotl_pass_" if method == "axo" else "fish_key_"
    sec_key = f"{prefix}{target}"
    
    # string_eval_expression resolves variables like ${sec.data.key}
    passphrase = weechat.string_eval_expression(f"${{sec.data.{sec_key}}}")
    if passphrase: return passphrase

    if method == "axo":
        passphrase = weechat.string_eval_expression("${sec.data.axolotl_default_pass}")
        if passphrase: return passphrase

    return None

def enforce_anti_forensics(buffer):
    """
    Implements the **Anti-Forensics (Ghost Mode)** protocol.
    
    When encryption is detected in a conversation, this function modifies the
    buffer's runtime properties to disable disk logging.
    
    **Mechanism:**
    It sets the WeeChat local buffer variable ``localvar_set_no_log`` to ``"1"``.
    This overrides global logging settings for this specific window only.

    :param str buffer: The pointer to the WeeChat buffer to secure.
    """
    if weechat.config_get_plugin("prevent_logging") == "on":
        # Check current state to avoid spamming the log/debug window
        current_val = weechat.buffer_get_string(buffer, "localvar_no_log")
        if current_val != "1":
            weechat.buffer_set(buffer, "localvar_set_no_log", "1")
            debug(f"Anti-Forensics: Logging DISABLED for buffer {buffer}")

# --- Custom Engine: FiSH Base64 ---
class FishBase64:
    """
    A custom Base64 implementation compliant with the mIRCryption/FiSH standard.
    
    **The Problem:**
    Standard Base64 (RFC 4648) uses the alphabet ``A-Za-z0-9+/``.
    The FiSH protocol, originating from old eggdrop bots and mIRC scripts, uses
    a non-standard alphabet: ``./0-9A-Za-z``.
    
    Furthermore, FiSH packs bits differently (Big Endian words to Little Endian
    6-bit chunks), requiring a custom implementation to be compatible with other
    clients like HexChat.
    """
    
    B64 = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    @staticmethod
    def encrypt(data_bytes):
        """
        Converts raw bytes into FiSH-compliant Base64 string.
        
        **Process:**
        1. Takes 8 bytes (64 bits) of input (Blowfish block size).
        2. Unpacks into two 32-bit integers (Left and Right).
        3. Encodes those integers into 12 characters from the custom alphabet.

        :param bytes data_bytes: The raw encrypted binary data.
        :return: The encoded string ready for transmission.
        :rtype: str
        """
        res = ""
        for i in range(0, len(data_bytes), 8):
            if i + 8 > len(data_bytes): break
            left, right = struct.unpack(">LL", data_bytes[i:i+8])
            for val in (left, right):
                for _ in range(6):
                    res += FishBase64.B64[val & 0x3F]
                    val >>= 6
        return res

    @staticmethod
    def decrypt(data_str):
        """
        Converts a FiSH-compliant Base64 string back into raw bytes.
        
        Reverses the logic of ``encrypt()``, mapping the custom alphabet back
        to 6-bit values and reconstructing the 32-bit integers.

        :param str data_str: The encoded ciphertext string.
        :return: The raw binary data.
        :rtype: bytes
        """
        res = bytearray()
        rev = {c: i for i, c in enumerate(FishBase64.B64)}
        for i in range(0, len(data_str), 12):
            chunk = data_str[i:i+12]
            if len(chunk) < 12: break
            left_val = 0
            right_val = 0
            temp = 0
            for j in range(5, -1, -1):
                temp = (temp << 6) | rev.get(chunk[6+j], 0)
            right_val = temp
            temp = 0
            for j in range(5, -1, -1):
                temp = (temp << 6) | rev.get(chunk[j], 0)
            left_val = temp
            res.extend(struct.pack(">LL", left_val, right_val))
        return bytes(res)

# --- Engine: FiSH (Blowfish CBC) ---
class FishEngine:
    """
    Implements the Blowfish Cipher in CBC (Cipher Block Chaining) mode.
    
    This class handles the core cryptographic operations for the FiSH protocol.
    It serves as a compatibility layer for group chats.
    """
    
    @staticmethod
    def encrypt(msg, key):
        """
        Encrypts a plaintext message using Blowfish.
        
        **Compatibility Note (Zero-IV):**
        Modern cryptography usually requires a random Initialization Vector (IV).
        However, the legacy FiSH protocol mandates a **Zero-IV** (8 null bytes).
        We adhere to this requirement to ensure we can talk to mIRC users.

        :param str msg: The plaintext message.
        :param str key: The shared secret key.
        :return: The FiSH-Base64 encoded ciphertext.
        :rtype: str
        """
        if not CAPABILITY_FISH or not key: return None
        try:
            iv = b'\x00' * 8 
            key_bytes = key.encode('utf-8') if isinstance(key, str) else key
            cipher = Blowfish.new(key_bytes, Blowfish.MODE_CBC, iv)
            padded_data = pad(msg.encode('utf-8'), Blowfish.block_size)
            encrypted = cipher.encrypt(padded_data)
            del cipher, padded_data
            return FishBase64.encrypt(encrypted)
        except Exception as e:
            debug(f"FiSH Encrypt Error: {e}")
            raise e

    @staticmethod
    def decrypt(msg_b64, key):
        """
        Decrypts a FiSH message.

        :param str msg_b64: The ciphertext string (without the ``+OK`` prefix).
        :param str key: The shared secret key.
        :return: The decrypted UTF-8 string, or None if decryption failed.
        :rtype: str or None
        """
        if not CAPABILITY_FISH or not key: return None
        try:
            iv = b'\x00' * 8
            key_bytes = key.encode('utf-8') if isinstance(key, str) else key
            cipher = Blowfish.new(key_bytes, Blowfish.MODE_CBC, iv)
            encrypted_bytes = FishBase64.decrypt(msg_b64)
            decrypted_padded = cipher.decrypt(encrypted_bytes)
            del cipher, encrypted_bytes
            return unpad(decrypted_padded, Blowfish.block_size).decode('utf-8', errors='replace')
        except Exception:
            return None

# --- Engine: Axolotl (Ratchet) ---
class AxolotlEngine:
    """
    Implements the Axolotl (Double Ratchet) protocol wrapper.
    
    **Concept:**
    Unlike FiSH, Axolotl does not use a static key. It uses a "Ratchet".
    Every time a message is sent or received, the encryption keys "step forward".
    Old keys are deleted. This guarantees **Perfect Forward Secrecy**: even if
    someone steals your database today, they cannot decrypt messages from yesterday.
    """
    
    @staticmethod
    def encrypt_chunk_bytes(msg_bytes, nick, username, db_path, passphrase):
        """
        Encrypts a chunk of data and advances the ratchet.
        
        **Important:** This method accepts ``bytes``, not ``str``.
        This is crucial for the chunking logic. If we split a message string,
        we might slice a multi-byte emoji in half, creating invalid UTF-8.
        By splitting bytes instead, we avoid data corruption.

        :param bytes msg_bytes: The data chunk.
        :param str nick: Local user nickname.
        :param str username: Remote user nickname.
        :param str db_path: Path to the state database.
        :param str passphrase: Database password.
        :return: Base64 string of the ciphertext.
        :rtype: str
        """
        if not CAPABILITY_AXOLOTL: return None
        try:
            a = Axolotl(nick, dbname=db_path, dbpassphrase=passphrase)
            a.loadState(nick, username)
            enc = a.encrypt(msg_bytes)
            # Remove newlines to prevent IRC protocol injection
            b64 = b2a_base64(enc).decode('ascii').replace("\n", "").replace("\r", "")
            a.saveState()
            del a
            return b64
        except Exception as e:
            debug(f"Axolotl Internal Error: {e}")
            raise e

    @staticmethod
    def decrypt(b64_msg, nick, username, db_path, passphrase):
        """
        Decrypts a message and advances the local ratchet state.

        :param str b64_msg: The incoming Base64 ciphertext.
        :return: Decrypted UTF-8 string.
        :rtype: str or None
        """
        if not CAPABILITY_AXOLOTL: return None
        try:
            a = Axolotl(nick, dbname=db_path, dbpassphrase=passphrase)
            a.loadState(nick, username)
            dec = a.decrypt(a2b_base64(b64_msg))
            a.saveState()
            
            # Clean up control characters that might mess up the terminal
            clean_bytes = bytes([b for b in dec if b > 31 or b in (9, 2, 3, 15)])
            del a 
            return clean_bytes.decode('utf-8', errors='replace')
        except Exception:
            return None

# --- Core Logic ---

def determine_context(buffer=None, args=None):
    """
    Analyzes the environment to determine who we are talking to.
    
    This helper is used by both the command handler and the signal callbacks
    to figure out the encryption target (Channel name or Nickname).

    :param buffer: The WeeChat buffer pointer (optional).
    :param args: The raw arguments from a command string (optional).
    :return: A tuple ``(target_name, is_channel_bool)``.
    :rtype: tuple
    """
    if not buffer: buffer = weechat.current_buffer()
    target = weechat.buffer_get_string(buffer, 'localvar_channel') or ""
    
    if args:
        try:
            # Parse "PRIVMSG <target> :message"
            pre = args.split(":", 1)[0]
            preparts = pre.split()
            if len(preparts) >= 2:
                target = preparts[-2]
        except: pass
            
    is_channel = target.startswith("#") or target.startswith("&")
    return target, is_channel

def cmd_polycipher(data, buffer, args):
    """
    The main command handler for ``/polycipher``.
    
    Processes user commands to manage keys and check status.
    
    **Subcommands:**
    
    * ``status``: Checks the current buffer for active encryption.
    * ``setkey <target> <key>``: Safely stores a FiSH key.
    
    **Input Sanitization:**
    This function applies strict regex validation to targets and escapes
    shell characters in passwords to prevent command injection vulnerabilities.

    :param data: WeeChat internal data.
    :param buffer: The current buffer context.
    :param args: The arguments string passed to the command.
    """
    args = args.strip().split()
    cmd = args[0].lower() if args else ""
    target, is_channel = determine_context(buffer)

    if cmd == "status":
        weechat.prnt(buffer, f"\n{weechat.prefix('info')}PolyCipher Security Status for {target}:")
        
        axo_db = get_axolotl_db_path(target)
        axo_active = os.path.exists(axo_db) if axo_db else False
        fish_key = get_key(target, "fish")
        fish_active = fish_key is not None
        
        weechat.prnt(buffer, f"  [Axolotl] DB File: {axo_db}")
        weechat.prnt(buffer, f"  [Axolotl] Active:  {axo_active}")
        weechat.prnt(buffer, f"  [FiSH]    Key Set: {fish_active}")
        
        strict = is_strict_mode()
        color_strict = "lightgreen" if strict else "red"
        weechat.prnt(buffer, f"  [Global]  Strict Mode: {weechat.color(color_strict)}{'ON' if strict else 'OFF'}")
        
        ghost = weechat.config_get_plugin("prevent_logging") == "on"
        ghost_color = "lightgreen" if ghost else "yellow"
        weechat.prnt(buffer, f"  [Global]  Anti-Forensics: {weechat.color(ghost_color)}{'ON' if ghost else 'OFF'}")
        
        no_log = weechat.buffer_get_string(buffer, "localvar_no_log")
        log_status = "Disabled (Safe)" if no_log == "1" else "Enabled (Forensic Risk)"
        weechat.prnt(buffer, f"  [Buffer]  Disk Logging: {log_status}")

    elif cmd == "setkey":
        if len(args) < 3:
            weechat.prnt("", "Usage: /polycipher setkey <target> <secret>")
            return weechat.WEECHAT_RC_OK
        
        tgt = args[1]
        key = " ".join(args[2:])
        
        if not re.match(r'^[#&!+A-Za-z0-9_\-\[\]]+$', tgt):
            weechat.prnt("", f"{weechat.prefix('error')}Invalid Target Format.")
            return weechat.WEECHAT_RC_ERROR
            
        if any(c in key for c in ['\n', '\r']):
            weechat.prnt("", f"{weechat.prefix('error')}Invalid Key.")
            return weechat.WEECHAT_RC_ERROR

        safe_key = key.replace("\\", "\\\\").replace("\"", "\\\"").replace("$", "\\$")
        weechat.command("", f"/secure set fish_key_{tgt} \"{safe_key}\"")
        weechat.prnt("", f"Key for {tgt} secured in Vault.")

    else:
        weechat.prnt("", "Usage: /polycipher [status | setkey]")

    return weechat.WEECHAT_RC_OK

def cb_decrypt(data, msgtype, servername, args):
    """
    Signal Callback for ``irc_in2_privmsg``.
    
    This function is the **Ingress Gatekeeper**. It inspects every message arriving
    from the IRC server.
    
    **Logic:**
    1.  Check for the FiSH prefix (``+OK``). If found, decrypt using ``FishEngine``.
    2.  If not FiSH, check if an Axolotl DB exists for the sender. If yes, try ``AxolotlEngine``.
    3.  If decryption succeeds, activate Anti-Forensics (disable logging) and return the decrypted text.
    4.  If decryption fails or is not applicable, return the original message.

    :return: The processed message string to be displayed.
    :rtype: str
    """
    try:
        hostmask, chanmsg = args.split("PRIVMSG ", 1)
        channelname, message = chanmsg.split(" :", 1)
    except ValueError:
        return args

    if "!" in hostmask:
        sender_nick = hostmask.split("!", 1)[0].lstrip(":")
    else:
        sender_nick = channelname.strip()
    
    is_channel = channelname.startswith("#")
    decrypted_text = None
    method_used = ""

    fish_prefix = weechat.config_get_plugin("fish_prefix")
    if message.startswith(fish_prefix):
        target_for_key = channelname if is_channel else sender_nick
        key = get_key(target_for_key, "fish")
        if key:
            decrypted_text = FishEngine.decrypt(message[len(fish_prefix):].strip(), key)
            if decrypted_text: method_used = "fish"
            del key

    if not decrypted_text and not is_channel:
        db_path = get_axolotl_db_path(sender_nick)
        if db_path and os.path.exists(db_path):
            passphrase = get_key(sender_nick, "axo") or weechat.config_get_plugin("default_password")
            decrypted_text = AxolotlEngine.decrypt(message.strip(), sender_nick, sender_nick, db_path, passphrase)
            if decrypted_text: method_used = "axo"
            del passphrase

    if decrypted_text:
        buf = weechat.buffer_search("irc", f"{servername}.{channelname}")
        if buf: enforce_anti_forensics(buf)

        indicator = weechat.config_get_plugin(f"message_indicator_{method_used}")
        ts_match = re.match(r'^\[\d{2}:\d{2}:\d{2}]\s', message)
        timestamp = ts_match.group(0) if ts_match else ''
        return f"{hostmask}PRIVMSG {channelname} :{indicator}{timestamp}{decrypted_text}"

    return args

def cb_encrypt(data, msgtype, servername, args):
    """
    Signal Callback for ``irc_out_privmsg``.
    
    This function is the **Egress Gatekeeper**. It inspects every message sent
    by the user.
    
    **Routing Logic:**
    1.  **Axolotl (Priority 1):** If the target is a user (not a channel) and
        we have a database for them, use Axolotl.
    2.  **FiSH (Priority 2):** If we have a key for the target (channel or user),
        use FiSH.
    3.  **Plaintext:** If no keys are found, send normally.
    
    **Strict Mode:**
    If we *attempt* encryption but it fails (e.g., library error), Strict Mode
    will return an empty string, cancelling the message to prevent a plaintext leak.

    :return: The encrypted IRC command, or empty string on failure.
    :rtype: str
    """
    try:
        pre, message = args.split(":", 1)
    except ValueError: return args

    prestr = pre.split(" ")
    if len(prestr) >= 2: target = prestr[-2]
    else: return args
    
    is_channel = target.startswith("#") or target.startswith("&")
    buf = weechat.current_buffer()
    my_nick = weechat.buffer_get_string(buf, 'localvar_nick')
    strict = is_strict_mode()

    enforce_anti_forensics(buf)

    if not is_channel:
        db_path = get_axolotl_db_path(target)
        if db_path and os.path.exists(db_path):
            passphrase = get_key(target, "axo") or weechat.config_get_plugin("default_password")
            try:
                CHUNK_SIZE = 300
                msg_bytes = message.encode('utf-8')
                total_len = len(msg_bytes)
                final_output = ""
                
                if total_len <= CHUNK_SIZE:
                    enc = AxolotlEngine.encrypt_chunk_bytes(msg_bytes, my_nick, target, db_path, passphrase)
                    if not enc: raise Exception("Encryption Result Empty")
                    final_output = f"{pre}:{enc}"
                else:
                    for i in range(0, total_len, CHUNK_SIZE):
                        chunk_bytes = msg_bytes[i : i + CHUNK_SIZE]
                        enc = AxolotlEngine.encrypt_chunk_bytes(chunk_bytes, my_nick, target, db_path, passphrase)
                        if not enc: raise Exception("Chunk Encryption Failed")
                        final_output += f"{pre}:{enc}\n"
                    final_output = final_output.rstrip()
                
                del passphrase
                return final_output

            except Exception as e:
                log(f"Axolotl Encryption Failed: {e}", "error")
                if strict:
                    weechat.prnt(buf, f"{weechat.prefix('error')}STRICT MODE: Message BLOCKED.")
                    return ""
                return args

    fish_key = get_key(target, "fish")
    if fish_key:
        try:
            prefix = weechat.config_get_plugin("fish_prefix")
            encrypted = FishEngine.encrypt(message, fish_key)
            del fish_key
            if encrypted:
                return f"{pre}:{prefix}{encrypted}"
            raise Exception("Encryption Result Empty")
        except Exception as e:
            log(f"FiSH Encryption Failed: {e}", "error")
            if strict:
                weechat.prnt(buf, f"{weechat.prefix('error')}STRICT MODE: Message BLOCKED.")
                return ""

    return args

def update_statusbar(data, signal, signal_data):
    """
    Refreshes the status bar item. Called on buffer switch.
    """
    weechat.bar_item_update('polycipher')
    return weechat.WEECHAT_RC_OK

def cb_statusbar(data, item, window):
    """
    Renders the status bar indicator.
    
    Shows ``[AXO]`` or ``[FiSH]`` depending on the active security context.
    """
    if window:
        buf = weechat.window_get_pointer(window, 'buffer')
    else:
        buf = weechat.current_buffer()
    
    target, is_channel = determine_context(buf)
    if not target: return ""
    
    if not is_channel:
        db_path = get_axolotl_db_path(target)
        if db_path and os.path.exists(db_path):
            ind = weechat.config_get_plugin("statusbar_indicator_axo")
            return f"{weechat.color(weechat.config_get_plugin('statusbar_color'))}{ind}"
    
    if get_key(target, "fish"):
        ind = weechat.config_get_plugin("statusbar_indicator_fish")
        return f"{weechat.color(weechat.config_get_plugin('statusbar_color'))}{ind}"

    return ""

if __name__ == "__main__":
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", "UTF-8"):
        
        weechat_dir = weechat.info_get("weechat_data_dir", "") or weechat.info_get("weechat_dir", "")
        
        missing = []
        if not CAPABILITY_AXOLOTL: missing.append("pyaxo")
        if not CAPABILITY_FISH: missing.append("pycryptodome")
        
        if missing:
             weechat.prnt("", f"{weechat.prefix('error')}PolyCipher: MISSING LIBS: {', '.join(missing)}")

        for option, default_value in script_options.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        
        if not is_strict_mode():
             weechat.prnt("", f"{weechat.prefix('error')}PolyCipher: WARNING! STRICT MODE IS OFF.")

        weechat.bar_item_new('polycipher', 'cb_statusbar', '')
        weechat.hook_command("polycipher", "Manage PolyCipher", "status | setkey", "", "status|setkey", "cmd_polycipher", "")
        weechat.hook_modifier("irc_in2_privmsg", "cb_decrypt", "")
        weechat.hook_modifier("irc_out_privmsg", "cb_encrypt", "")
        weechat.hook_signal("buffer_switch", "update_statusbar", "")
