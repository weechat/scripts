# -*- coding: utf-8 -*-
#
# xcrypt.py - End-to-end encryption plugin for WeeChat
#
# SPDX-FileCopyrightText: 2026 xcrypt AnonShell <contact@anonshell.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Copyright (c) 2026 xcrypt AnonShell <contact@anonshell.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    WEECHAT_RC_ERROR = weechat.WEECHAT_RC_ERROR
except ImportError:
    # For testing/linting outside WeeChat
    weechat = None  # type: ignore
    WEECHAT_RC_OK = 0
    WEECHAT_RC_ERROR = -1


# Plugin metadata
SCRIPT_NAME = "xcrypt"
SCRIPT_AUTHOR = "xcrypt AnonShell"
SCRIPT_VERSION = "1.0.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "End-to-end encryption for IRC messages using AES-256-GCM"

# Encryption constants
ENCRYPTION_PREFIX = "+ENC:"
STORAGE_PREFIX = "$XCRYPT$"  # Prefix for encrypted stored passwords
SALT_LENGTH = 16
NONCE_LENGTH = 12
KEY_LENGTH = 32  # 256 bits
PBKDF2_ITERATIONS = 600000  # OWASP recommended minimum for PBKDF2-SHA256
STORAGE_ITERATIONS = 100000  # Faster iterations for storage encryption (local only)

# Global storage for encryption keys (server.target -> password)
encryption_passwords: dict[str, str] = {}

# Master passphrase for encrypting stored passwords (kept in memory only)
master_passphrase: str | None = None
passphrase_verified: bool = False


def prnt(message: str) -> None:
    weechat.prnt("", f"{SCRIPT_NAME}: {message}")


def prnt_buffer(buffer: str, message: str) -> None:
    weechat.prnt(buffer, f"{SCRIPT_NAME}: {message}")


def derive_key(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_message(plaintext: str, password: str) -> str:
    # Generate random salt and nonce
    salt = secrets.token_bytes(SALT_LENGTH)
    nonce = secrets.token_bytes(NONCE_LENGTH)
    
    # Derive key from password
    key = derive_key(password, salt)
    
    # Encrypt with AES-GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    
    # Combine salt + nonce + ciphertext and encode
    encrypted_data = salt + nonce + ciphertext
    encoded = base64.b64encode(encrypted_data).decode("ascii")
    
    return f"{ENCRYPTION_PREFIX}{encoded}"


def decrypt_message(encrypted: str, password: str) -> str | None:
    # Remove prefix if present
    if encrypted.startswith(ENCRYPTION_PREFIX):
        encrypted = encrypted[len(ENCRYPTION_PREFIX):]
    
    try:
        # Decode from base64
        encrypted_data = base64.b64decode(encrypted)
        
        # Extract salt, nonce, and ciphertext
        if len(encrypted_data) < SALT_LENGTH + NONCE_LENGTH + 16:
            return None  # Too short to be valid
            
        salt = encrypted_data[:SALT_LENGTH]
        nonce = encrypted_data[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
        ciphertext = encrypted_data[SALT_LENGTH + NONCE_LENGTH:]
        
        # Derive key from password
        key = derive_key(password, salt)
        
        # Decrypt with AES-GCM
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode("utf-8")
        
    except Exception:
        # Decryption failed - wrong password or corrupted data
        return None


def encrypt_for_storage(plaintext: str, passphrase: str) -> str:
    salt = secrets.token_bytes(SALT_LENGTH)
    nonce = secrets.token_bytes(NONCE_LENGTH)
    
    key = derive_key(passphrase, salt, STORAGE_ITERATIONS)
    
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    
    encrypted_data = salt + nonce + ciphertext
    encoded = base64.b64encode(encrypted_data).decode("ascii")
    
    return f"{STORAGE_PREFIX}{encoded}"


def decrypt_from_storage(encrypted: str, passphrase: str) -> str | None:
    if not encrypted.startswith(STORAGE_PREFIX):
        # Not encrypted - return as-is (legacy plain text)
        return encrypted
    
    encrypted = encrypted[len(STORAGE_PREFIX):]
    
    try:
        encrypted_data = base64.b64decode(encrypted)
        
        if len(encrypted_data) < SALT_LENGTH + NONCE_LENGTH + 16:
            return None
        
        salt = encrypted_data[:SALT_LENGTH]
        nonce = encrypted_data[SALT_LENGTH:SALT_LENGTH + NONCE_LENGTH]
        ciphertext = encrypted_data[SALT_LENGTH + NONCE_LENGTH:]
        
        key = derive_key(passphrase, salt, STORAGE_ITERATIONS)
        
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        
        return plaintext.decode("utf-8")
        
    except Exception:
        return None


def get_passphrase_hash(passphrase: str) -> str:
    # Use a fixed salt for the verification hash
    # This is not for security but just to verify the passphrase is correct
    salt = b"xcrypt_verify_salt_v1"
    key = derive_key(passphrase, salt, STORAGE_ITERATIONS)
    return base64.b64encode(key[:16]).decode("ascii")


def verify_passphrase(passphrase: str) -> bool:
    stored_hash = weechat.config_get_plugin("passphrase_hash")
    if not stored_hash:
        return True  # No hash stored yet
    
    computed_hash = get_passphrase_hash(passphrase)
    return computed_hash == stored_hash


def get_target_key(server: str, target: str) -> str:
    return f"{server.lower()}.{target.lower()}"


def get_password_for_target(server: str, target: str) -> str | None:
    key = get_target_key(server, target)
    return encryption_passwords.get(key)


def set_password_for_target(server: str, target: str, password: str) -> None:
    key = get_target_key(server, target)
    encryption_passwords[key] = password
    save_passwords()


def del_password_for_target(server: str, target: str) -> bool:
    key = get_target_key(server, target)
    if key in encryption_passwords:
        del encryption_passwords[key]
        save_passwords()
        return True
    return False


def save_passwords() -> None:
    global master_passphrase
    
    if not master_passphrase:
        prnt("Warning: No master passphrase set! Passwords stored in plain text.")
        prnt("Use '/xcrypt passphrase <your-passphrase>' to secure your passwords.")
    
    # Store each password (encrypted if passphrase is set)
    for key, password in encryption_passwords.items():
        option_name = f"password.{key}"
        if master_passphrase:
            encrypted = encrypt_for_storage(password, master_passphrase)
            weechat.config_set_plugin(option_name, encrypted)
        else:
            weechat.config_set_plugin(option_name, password)
    
    # Save the list of keys
    keys_str = ",".join(encryption_passwords.keys())
    weechat.config_set_plugin("password_keys", keys_str)


def load_passwords() -> None:
    global encryption_passwords, master_passphrase, passphrase_verified
    
    keys_str = weechat.config_get_plugin("password_keys")
    if not keys_str:
        return
    
    # Check if we have encrypted passwords but no passphrase
    has_encrypted = False
    for key in keys_str.split(","):
        if key:
            option_name = f"password.{key}"
            stored = weechat.config_get_plugin(option_name)
            if stored and stored.startswith(STORAGE_PREFIX):
                has_encrypted = True
                break
    
    if has_encrypted and not master_passphrase:
        prnt("Encrypted passwords found but no passphrase set.")
        prnt("Use '/xcrypt passphrase <your-passphrase>' to unlock your passwords.")
        return
    
    # Load and decrypt passwords
    for key in keys_str.split(","):
        if key:
            option_name = f"password.{key}"
            stored = weechat.config_get_plugin(option_name)
            if stored:
                if stored.startswith(STORAGE_PREFIX):
                    if master_passphrase:
                        decrypted = decrypt_from_storage(stored, master_passphrase)
                        if decrypted:
                            encryption_passwords[key] = decrypted
                        else:
                            prnt(f"Failed to decrypt password for {key} - wrong passphrase?")
                else:
                    # Legacy plain text password
                    encryption_passwords[key] = stored


def get_buffer_info(buffer: str) -> tuple[str, str] | None:
    # Check if this is an IRC buffer
    plugin = weechat.buffer_get_string(buffer, "plugin")
    if plugin != "irc":
        return None
    
    # Get server and channel from local variables
    server = weechat.buffer_get_string(buffer, "localvar_server")
    channel = weechat.buffer_get_string(buffer, "localvar_channel")
    buffer_type = weechat.buffer_get_string(buffer, "localvar_type")
    
    if not server or not channel:
        return None
    
    # Only handle channel and private buffers
    if buffer_type not in ("channel", "private"):
        return None
    
    return (server, channel)


def modifier_irc_out_privmsg_cb(
    data: str,
    modifier: str,
    modifier_data: str,
    string: str,
) -> str:
    if not string:
        return string
    
    # Parse the PRIVMSG command
    # Format: PRIVMSG <target> :<message>
    if not string.upper().startswith("PRIVMSG "):
        return string
    
    # Get the server name from modifier_data
    server = modifier_data
    
    # Split into command parts
    parts = string.split(" ", 2)
    if len(parts) < 3:
        return string
    
    command = parts[0]  # PRIVMSG
    target = parts[1]   # channel or nick
    message = parts[2]  # :message
    
    # Remove leading colon from message
    if message.startswith(":"):
        message = message[1:]
    
    # Don't encrypt already encrypted messages
    if message.startswith(ENCRYPTION_PREFIX):
        return string
    
    # Don't encrypt CTCP messages (except ACTION)
    if message.startswith("\x01") and not message.startswith("\x01ACTION "):
        return string
    
    # Check if we have a password for this target
    password = get_password_for_target(server, target)
    if not password:
        return string
    
    # Handle ACTION messages specially
    is_action = message.startswith("\x01ACTION ")
    if is_action:
        # Extract action text: \x01ACTION text\x01
        action_text = message[8:]  # Remove "\x01ACTION "
        if action_text.endswith("\x01"):
            action_text = action_text[:-1]
        encrypted = encrypt_message(f"ACTION:{action_text}", password)
    else:
        encrypted = encrypt_message(message, password)
    
    return f"{command} {target} :{encrypted}"


def modifier_irc_in_privmsg_cb(
    data: str,
    modifier: str,
    modifier_data: str,
    string: str,
) -> str:
    if not string:
        return string
    
    # Get the server name from modifier_data
    server = modifier_data
    
    # Parse IRC message
    # Format: :nick!user@host PRIVMSG <target> :<message>
    if " PRIVMSG " not in string.upper():
        return string
    
    # Find the PRIVMSG position
    privmsg_pos = string.upper().find(" PRIVMSG ")
    if privmsg_pos == -1:
        return string
    
    prefix = string[:privmsg_pos]  # :nick!user@host
    rest = string[privmsg_pos + 9:]  # <target> :<message>
    
    # Split target and message
    parts = rest.split(" ", 1)
    if len(parts) < 2:
        return string
    
    target = parts[0]
    message = parts[1]
    
    # Remove leading colon from message
    if message.startswith(":"):
        message = message[1:]
    
    # Check if message is encrypted
    if not message.startswith(ENCRYPTION_PREFIX):
        return string
    
    # Extract sender nick for private messages
    sender_nick = ""
    if prefix.startswith(":"):
        nick_end = prefix.find("!")
        if nick_end > 1:
            sender_nick = prefix[1:nick_end]
    
    # For private messages, the "target" in the PRIVMSG is our nick,
    # but we want to look up the password by the sender's nick
    password = None
    
    # First try the target (for channels)
    password = get_password_for_target(server, target)
    
    # If not found and this might be a private message, try the sender
    if not password and sender_nick and not target.startswith(("#", "&", "!", "+")):
        password = get_password_for_target(server, sender_nick)
    
    if not password:
        return string
    
    # Try to decrypt
    decrypted = decrypt_message(message, password)
    if decrypted is None:
        # Decryption failed - might be wrong password or corrupted
        # Leave the message as-is with a marker
        return f"{prefix} PRIVMSG {target} :[DECRYPT FAILED] {message}"
    
    # Handle ACTION messages
    if decrypted.startswith("ACTION:"):
        action_text = decrypted[7:]
        return f"{prefix} PRIVMSG {target} :\x01ACTION {action_text}\x01"
    
    # Mark as decrypted with green E> prefix
    return f"{prefix} PRIVMSG {target} :\x0303E>\x0F {decrypted}"


def xcrypt_command_cb(data: str, buffer: str, args: str) -> int:
    global master_passphrase, passphrase_verified, encryption_passwords
    
    if not HAS_CRYPTOGRAPHY:
        prnt("Error: cryptography library is not installed!")
        prnt("Install it with: pip install cryptography")
        return WEECHAT_RC_ERROR
    
    argv = args.split(" ") if args else []
    argc = len(argv)
    
    if argc == 0 or argv[0] == "":
        # Show help
        prnt("xcrypt - End-to-end encryption for IRC")
        prnt("Usage:")
        prnt("  /xcrypt passphrase <pass>              - Set master passphrase (REQUIRED)")
        prnt("  /xcrypt set <channel|nick> <password>  - Set encryption password")
        prnt("  /xcrypt del <channel|nick>             - Remove encryption password")
        prnt("  /xcrypt list                           - List all encrypted targets")
        prnt("  /xcrypt status                         - Show status for current buffer")
        prnt("")
        if master_passphrase:
            prnt("Master passphrase: SET (passwords are encrypted)")
        else:
            prnt("Master passphrase: NOT SET (use /xcrypt passphrase <pass>)")
        return WEECHAT_RC_OK
    
    cmd = argv[0].lower()
    
    if cmd == "passphrase":
        if argc < 2:
            prnt("Usage: /xcrypt passphrase <your-master-passphrase>")
            prnt("This passphrase encrypts your channel/nick passwords at rest.")
            return WEECHAT_RC_ERROR
        
        new_passphrase = " ".join(argv[1:])  # Passphrase can contain spaces
        
        if len(new_passphrase) < 8:
            prnt("Error: Passphrase must be at least 8 characters long")
            return WEECHAT_RC_ERROR
        
        # Check if we have a stored hash to verify against
        stored_hash = weechat.config_get_plugin("passphrase_hash")
        
        if stored_hash:
            # Verify the passphrase matches
            if not verify_passphrase(new_passphrase):
                prnt("Error: Incorrect passphrase! This doesn't match your existing passphrase.")
                prnt("If you forgot your passphrase, you'll need to delete your passwords and start over.")
                return WEECHAT_RC_ERROR
            
            master_passphrase = new_passphrase
            passphrase_verified = True
            prnt("Passphrase verified! Loading encrypted passwords...")
            
            # Now load the encrypted passwords
            encryption_passwords.clear()
            load_passwords()
            
            if encryption_passwords:
                prnt(f"Loaded {len(encryption_passwords)} encrypted password(s)")
            else:
                prnt("No passwords found.")
        else:
            # First time setting passphrase
            old_passphrase = master_passphrase
            master_passphrase = new_passphrase
            passphrase_verified = True
            
            # Store the verification hash
            passphrase_hash = get_passphrase_hash(new_passphrase)
            weechat.config_set_plugin("passphrase_hash", passphrase_hash)
            
            # Re-encrypt any existing passwords with the new passphrase
            if encryption_passwords:
                prnt(f"Re-encrypting {len(encryption_passwords)} password(s) with new passphrase...")
                save_passwords()
            
            prnt("Master passphrase set! Your passwords will now be encrypted at rest.")
            prnt("IMPORTANT: Remember this passphrase - you'll need it each time you start WeeChat.")
        
        return WEECHAT_RC_OK
    
    elif cmd == "set":
        if argc < 3:
            prnt("Usage: /xcrypt set <channel|nick> <password>")
            return WEECHAT_RC_ERROR
        
        # Get server from current buffer
        buffer_info = get_buffer_info(buffer)
        if not buffer_info:
            prnt("Error: This command must be run from an IRC buffer")
            return WEECHAT_RC_ERROR
        
        server = buffer_info[0]
        target = argv[1]
        password = " ".join(argv[2:])  # Password can contain spaces
        
        if len(password) < 8:
            prnt("Error: Password must be at least 8 characters long")
            return WEECHAT_RC_ERROR
        
        set_password_for_target(server, target, password)
        prnt(f"Encryption enabled for {target} on {server}")
        prnt(f"Messages to/from {target} will now be encrypted")
        return WEECHAT_RC_OK
    
    elif cmd == "del":
        if argc < 2:
            prnt("Usage: /xcrypt del <channel|nick>")
            return WEECHAT_RC_ERROR
        
        # Get server from current buffer
        buffer_info = get_buffer_info(buffer)
        if not buffer_info:
            prnt("Error: This command must be run from an IRC buffer")
            return WEECHAT_RC_ERROR
        
        server = buffer_info[0]
        target = argv[1]
        
        if del_password_for_target(server, target):
            prnt(f"Encryption disabled for {target} on {server}")
        else:
            prnt(f"No encryption was set for {target} on {server}")
        return WEECHAT_RC_OK
    
    elif cmd == "list":
        if not encryption_passwords:
            prnt("No encryption passwords configured")
        else:
            prnt("Encrypted targets:")
            for key in sorted(encryption_passwords.keys()):
                parts = key.split(".", 1)
                if len(parts) == 2:
                    prnt(f"  {parts[0]}: {parts[1]}")
                else:
                    prnt(f"  {key}")
        return WEECHAT_RC_OK
    
    elif cmd == "status":
        buffer_info = get_buffer_info(buffer)
        if not buffer_info:
            prnt("Not an IRC channel or private buffer")
            return WEECHAT_RC_OK
        
        server, target = buffer_info
        password = get_password_for_target(server, target)
        
        prnt(f"--- xcrypt status ---")
        prnt(f"Master passphrase: {'SET' if master_passphrase else 'NOT SET'}")
        prnt(f"Storage encryption: {'ENABLED' if master_passphrase else 'DISABLED (plain text!)'}")
        prnt(f"")
        if password:
            prnt(f"Encryption is ENABLED for {target} on {server}")
            prnt(f"Password length: {len(password)} characters")
        else:
            prnt(f"Encryption is DISABLED for {target} on {server}")
            prnt(f"Use '/xcrypt set {target} <password>' to enable")
        return WEECHAT_RC_OK
    
    else:
        prnt(f"Unknown command: {cmd}")
        prnt("Use '/xcrypt' for help")
        return WEECHAT_RC_ERROR


def config_cb(data: str, option: str, value: str) -> int:
    # Reload passwords when config changes
    load_passwords()
    return WEECHAT_RC_OK


def unload_cb() -> int:
    # Save passwords before unloading
    save_passwords()
    return WEECHAT_RC_OK


def main() -> None:
    if not weechat:
        print("This script must be run inside WeeChat")
        return
    
    # Register the script
    if not weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "unload_cb",
        "",
    ):
        return
    
    # Check for cryptography library
    if not HAS_CRYPTOGRAPHY:
        weechat.prnt(
            "",
            f"{SCRIPT_NAME}: WARNING - cryptography library not found! "
            "Install with: pip install cryptography"
        )
    
    # Load saved passwords
    load_passwords()
    
    # Register the /xcrypt command
    weechat.hook_command(
        "xcrypt",
        "Manage end-to-end encryption for IRC messages",
        "passphrase <pass> || set <channel|nick> <password> || del <channel|nick> || list || status",
        "passphrase: set master passphrase for secure password storage (REQUIRED)\n"
        "       set: set encryption password for a channel or nick\n"
        "       del: remove encryption password\n"
        "      list: list all targets with encryption enabled\n"
        "    status: show encryption status for current buffer\n"
        "\n"
        "SECURITY: Set a master passphrase first! Without it, passwords are stored in plain text.\n"
        "Messages are encrypted using AES-256-GCM with PBKDF2 key derivation.\n"
        "Encrypted messages are prefixed with '+ENC:' and base64 encoded.\n"
        "Both parties must use the same password to communicate.\n"
        "\n"
        "Examples:\n"
        "  /xcrypt passphrase MyMasterPassword123\n"
        "  /xcrypt set #secret mypassword123\n"
        "  /xcrypt set friend supersecretkey\n"
        "  /xcrypt del #secret\n"
        "  /xcrypt list\n"
        "  /xcrypt status",
        "passphrase || set %(irc_channels)|%(nicks) || del %(irc_channels)|%(nicks) || list || status",
        "xcrypt_command_cb",
        "",
    )
    
    # Hook into outgoing messages (before sending)
    # irc_out1_xxx is called before the message is sent, with UTF-8 valid string
    weechat.hook_modifier("irc_out1_privmsg", "modifier_irc_out_privmsg_cb", "")
    
    # Hook into incoming messages (after charset decoding)
    # irc_in2_xxx is called after charset decoding, string is always UTF-8 valid
    weechat.hook_modifier("irc_in2_privmsg", "modifier_irc_in_privmsg_cb", "")
    
    # Hook config changes
    weechat.hook_config(f"plugins.var.python.{SCRIPT_NAME}.*", "config_cb", "")
    
    prnt(f"loaded (version {SCRIPT_VERSION})")
    
    # Check if we have encrypted passwords waiting for passphrase
    keys_str = weechat.config_get_plugin("password_keys")
    stored_hash = weechat.config_get_plugin("passphrase_hash")
    
    if stored_hash and keys_str:
        prnt("Encrypted passwords found. Use '/xcrypt passphrase <pass>' to unlock.")
    elif encryption_passwords:
        prnt(f"Loaded {len(encryption_passwords)} encryption password(s)")
        prnt("WARNING: Passwords are stored in plain text!")
        prnt("Use '/xcrypt passphrase <pass>' to enable secure storage.")


# Entry point
if __name__ == "__main__":
    main()
