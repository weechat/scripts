# -*- coding: utf-8 -*-
#
# Copyright (C) David Flatz <david@upcs.at>
# Copyright (C) 2017 Ricardo Ferreira <ricardo.sff@goatse.cx>
# Copyright (C) 2012 Markus Näsman <markus@botten.org>
# Copyright (C) 2009 Bjorn Edstrom <be@bjrn.se>
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

#
# Changelog, Suggestions, Bugs, ...?
# https://github.com/freshprince/weechat-fish
#

#
# HINTS:
# =====
#
# Getting long lines cut off by the irc server? Try setting
# irc.*.split_msg_max_length to something smaller:
#     /set irc.server_default.split_msg_max_length 400
#
# You can have an indicator showing whether a key is set and messages in a
# buffer are encrypted by adding the fish item to a bar:
#     /blowkey setup_bar_item
#
# If you want to keep the keys stored on disk to be encrypted you can use
# weechat secure data:
#     /secure set fish.foo cbc:verysecr1tkey
#     /blowkey set #foo ${sec.data.fish.foo}
#

#
# NOTE ABOUT DH1080:
# =================
#
# Diffie-Hellman key exchange assumes that you already have
# authenticated channels between Alice and Bob.  Which means that Alice
# has to be sure that she is really talking to Bob and not to any man in
# the middle.  But since the whole idea of FiSH is that you want to
# encrypt your communication on the IRC server whose operators you do
# not trust, there is no reliable way for Alice to tell if she really is
# talking to Bob.  It could also be some rogue IRC admin impersonating
# Bob with a fake hostname and ident or even doing a MITM attack on
# DH1080.  This means you can consider using DH1080 key exchange over
# IRC utterly broken in terms of security.
#

import re
import struct
import hashlib
import base64
import sys
import traceback
from os import urandom

SCRIPT_NAME = "fish"
SCRIPT_AUTHOR = "David Flatz <david@upcs.at>"
SCRIPT_VERSION = "1.0rc2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "FiSH for weechat"
CONFIG_FILE_NAME = SCRIPT_NAME
BAR_ITEM_NAME = SCRIPT_NAME
TAG_NAME = SCRIPT_NAME

import_ok = True

try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

try:
    import Crypto.Cipher.Blowfish as CryptoBlowfish
except ImportError:
    try:
        import Cryptodome.Cipher.Blowfish as CryptoBlowfish
    except ImportError:
        print("Pycryptodome must be installed to use fish")
        import_ok = False


#
# GLOBALS
#

fish_config_file = None
fish_config_option = {}
fish_config_keys = None
fish_DH1080ctx = {}
fish_bar_item = None


#
# CONFIG
#

def fish_config_reload_cb(data, config_file):
    return weechat.config_reload(config_file)


def fish_config_keys_create_cb(data, config_file, section, option_name, value):
    option = weechat.config_search_option(config_file, section, option_name)
    if option:
        return weechat.config_option_set(option, value, 1)

    option = weechat.config_new_option(
        config_file, section, option_name, "string", "", "", 0, 0, "",
        value, 0, "", "", "", "", "", "")
    if not option:
        return weechat.WEECHAT_CONFIG_OPTION_SET_ERROR

    weechat.bar_item_update(BAR_ITEM_NAME)
    return weechat.WEECHAT_CONFIG_OPTION_SET_OK_SAME_VALUE


def fish_config_keys_delete_cb(data, config_file, section, option):
    option_name = weechat.config_option_get_string(option, 'name')
    weechat.config_option_free(option)
    server, name = option_name.split('/')
    buffer = weechat.info_get("irc_buffer", f"{server},{name}")
    if buffer:
        fish_state_set(buffer, None)
    return weechat.WEECHAT_CONFIG_OPTION_UNSET_OK_REMOVED


def fish_config_init():
    global fish_config_file, fish_config_option, fish_config_keys

    fish_config_file = weechat.config_new(
        CONFIG_FILE_NAME, "fish_config_reload_cb", "")
    if not fish_config_file:
        return

    # look
    section_look = weechat.config_new_section(
        fish_config_file, "look", 0, 0, "", "", "", "", "", "", "", "", "", "")
    if not section_look:
        weechat.config_free(fish_config_file)
        return

    fish_config_option["announce"] = weechat.config_new_option(
        fish_config_file, section_look, "announce", "boolean",
        "announce if messages are being encrypted or not", "", 0, 0,
        "off", "off", 0, "", "", "", "", "", "")
    fish_config_option["marker"] = weechat.config_new_option(
        fish_config_file, section_look, "marker",
        "string", "marker for important FiSH messages", "", 0, 0,
        "O<", "O<", 0, "", "", "", "", "", "")
    fish_config_option["item"] = weechat.config_new_option(
        fish_config_file, section_look, "item", "string",
        "string used to show FiSH being used in current buffer", "", 0, 0,
        "%", "%", 0, "", "", "", "", "", "")
    fish_config_option["prefix"] = weechat.config_new_option(
        fish_config_file, section_look, "prefix", "boolean",
        "mark in prefix if message is encrypted or not", "", 0, 0,
        "on", "on", 0, "", "", "", "", "", "")
    fish_config_option["prefix_plaintext"] = weechat.config_new_option(
        fish_config_file, section_look, "prefix.plaintext", "string",
        "marker in prefix if message is plaintext", "", 0, 0,
        "‼", "‼", 0, "", "", "", "", "", "")
    fish_config_option["prefix_ecb"] = weechat.config_new_option(
        fish_config_file, section_look, "prefix.ecb", "string",
        "marker in prefix if message is encrypted in ecb mode", "", 0, 0,
        "°", "°", 0, "", "", "", "", "", "")
    fish_config_option["prefix_cbc"] = weechat.config_new_option(
        fish_config_file, section_look, "prefix.cbc", "string",
        "marker in prefix if message is encrypted in cbc mode", "", 0, 0,
        "·", "·", 0, "", "", "", "", "", "")

    # color
    section_color = weechat.config_new_section(
        fish_config_file, "color", 0, 0, "", "", "", "", "", "", "", "", "",
        "")
    if not section_color:
        weechat.config_free(fish_config_file)
        return

    fish_config_option["alert"] = weechat.config_new_option(
        fish_config_file, section_color, "alert",
        "color", "color for important FiSH message markers", "", 0, 0,
        "lightblue", "lightblue", 0, "", "", "", "", "", "")
    fish_config_option["unknown"] = weechat.config_new_option(
        fish_config_file, section_color, "unknown", "color",
        "color for bar item when state of encryption is unknown", "", 0, 0,
        "darkgray", "darkgray", 0, "", "", "", "", "", "")
    fish_config_option["plaintext"] = weechat.config_new_option(
        fish_config_file, section_color, "plaintext", "color",
        "color for bar item when messages are in plain text", "", 0, 0,
        "*red", "*red", 0, "", "", "", "", "", "")
    fish_config_option["ecb"] = weechat.config_new_option(
        fish_config_file, section_color, "ecb", "color",
        "color for bar item when messages are encrypted in ECB mode", "", 0, 0,
        "lightblue", "lightblue", 0, "", "", "", "", "", "")
    fish_config_option["cbc"] = weechat.config_new_option(
        fish_config_file, section_color, "cbc", "color",
        "color for bar item when messages are encrypted in CBC mode", "", 0, 0,
        "green", "green", 0, "", "", "", "", "", "")

    # keys
    fish_config_keys = weechat.config_new_section(
        fish_config_file, "keys", 1, 1, "", "", "", "", "", "",
        "fish_config_keys_create_cb", "", "fish_config_keys_delete_cb", "")
    if not fish_config_keys:
        weechat.config_free(fish_config_file)
        return


def fish_config_read():
    return weechat.config_read(fish_config_file)


def fish_config_write():
    return weechat.config_write(fish_config_file)


def fish_key_set(target: str, key: str, cbc: bool):
    value = f"cbc:{key}" if cbc else key
    target = target.lower()

    return fish_config_keys_create_cb(
        "", fish_config_file, fish_config_keys, target, value)


def fish_key_get(target: str):
    target = target.lower()
    option = weechat.config_search_option(
        fish_config_file, fish_config_keys, target)
    if not option:
        return None

    key = weechat.string_eval_expression(
        weechat.config_string(option), {}, {}, {})
    cbc = False
    if key.startswith('cbc:'):
        cbc = True
        key = key[4:]

    return (key, cbc)


def fish_key_delete(target: str):
    target = target.lower()
    option = weechat.config_search_option(
        fish_config_file, fish_config_keys, target)
    if option:
        fish_config_keys_delete_cb(
            "", fish_config_file, fish_config_keys, option)
        return True

    return False


##
# Blowfish and DH1080 Code:
##
#
# BLOWFISH
#

class Blowfish:

    def __init__(self, key=None):
        if key:
            if len(key) > 72:
                key = key[:72]
            self.blowfish = CryptoBlowfish.new(
                key.encode('utf-8'), CryptoBlowfish.MODE_ECB)

    def decrypt(self, data):
        return self.blowfish.decrypt(data)

    def encrypt(self, data):
        return self.blowfish.encrypt(data)


# XXX: Unstable.
def blowcrypt_b64encode(s):
    """A non-standard base64-encode."""
    B64 = "./0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    res = ''
    while s:
        left, right = struct.unpack('>LL', s[:8])
        for _ in range(6):
            res += B64[right & 0x3f]
            right >>= 6
        for _ in range(6):
            res += B64[left & 0x3f]
            left >>= 6
        s = s[8:]
    return res


def blowcrypt_b64decode(s):
    """A non-standard base64-decode."""
    B64 = "./0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    res = []
    while s:
        left, right = 0, 0
        for i, p in enumerate(s[0:6]):
            right |= B64.index(p) << (i * 6)
        for i, p in enumerate(s[6:12]):
            left |= B64.index(p) << (i * 6)
        for i in range(0, 4):
            res.append((left & (0xFF << ((3 - i) * 8))) >> ((3 - i) * 8))
        for i in range(0, 4):
            res.append((right & (0xFF << ((3 - i) * 8))) >> ((3 - i) * 8))
        s = s[12:]
    return bytes(res)


def padto(msg, length):
    """Pads 'msg' with zeroes until it's length is divisible by 'length'.
    If the length of msg is already a multiple of 'length', does nothing."""
    L = len(msg)
    if L % length:
        msg += b'\x00' * (length - L % length)
    assert len(msg) % length == 0
    return msg


def blowcrypt_pack(msg, key, cbc):
    """."""
    if cbc:
        cipher = CryptoBlowfish.new(
            key.encode('utf-8'), CryptoBlowfish.MODE_CBC)
        return '+OK *' + base64.b64encode(
            cipher.iv + cipher.encrypt(padto(msg, 8))).decode('utf-8')

    cipher = Blowfish(key)
    return '+OK ' + blowcrypt_b64encode(cipher.encrypt(padto(msg, 8)))


def blowcrypt_unpack(msg, key):
    """."""
    if not (msg.startswith('+OK ') or msg.startswith('mcps ')):
        raise ValueError
    _, rest = msg.split(' ', 1)

    if rest.startswith('*'):  # CBC mode
        cbc = True
        rest = rest[1:]
        if len(rest) % 4:
            rest += '=' * (4 - len(rest) % 4)
        raw = base64.b64decode(rest)

        iv = raw[:8]
        raw = raw[8:]

        cipher = CryptoBlowfish.new(
            key.encode('utf-8'), CryptoBlowfish.MODE_CBC, iv)

        plain = cipher.decrypt(padto(raw, 8))

    else:
        cbc = False
        cipher = Blowfish(key)

        if len(rest) < 12:
            raise ValueError

        if not (len(rest) % 12) == 0:
            rest = rest[:-(len(rest) % 12)]

        try:
            raw = blowcrypt_b64decode(padto(rest, 12))
        except TypeError as e:
            raise ValueError from e
        if not raw:
            raise ValueError

        plain = cipher.decrypt(raw)

    return (plain.strip(b'\x00').replace(b'\n', b''), cbc)


#
# DH1080
#

g_dh1080 = 2
p_dh1080 = int('FBE1022E23D213E8ACFA9AE8B9DFAD'
               'A3EA6B7AC7A7B7E95AB5EB2DF85892'
               '1FEADE95E6AC7BE7DE6ADBAB8A783E'
               '7AF7A7FA6A2B7BEB1E72EAE2B72F9F'
               'A2BFB2A2EFBEFAC868BADB3E828FA8'
               'BADFADA3E4CC1BE7E8AFE85E9698A7'
               '83EB68FA07A77AB6AD7BEB618ACF9C'
               'A2897EB28A6189EFA07AB99A8A7FA9'
               'AE299EFA7BA66DEAFEFBEFBF0B7D8B', 16)
q_dh1080 = (p_dh1080 - 1) // 2


def dh1080_b64encode(s):
    """A non-standard base64-encode."""
    b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    d = [0] * len(s) * 2

    L = len(s) * 8
    m = 0x80
    i, j, k, t = 0, 0, 0, 0
    while i < L:
        if s[i >> 3] & m:
            t |= 1
        j += 1
        m >>= 1
        if not m:
            m = 0x80
        if not j % 6:
            d[k] = b64[t]
            t &= 0
            k += 1
        t <<= 1
        t %= 0x100
        #
        i += 1
    m = 5 - j % 6
    t <<= m
    t %= 0x100
    if m:
        d[k] = b64[t]
        k += 1
    d[k] = 0
    res = ''
    for q in d:
        if q == 0:
            break
        res += q
    return res


def dh1080_b64decode(s):
    """A non-standard base64-encode."""
    b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    buf = [0] * 256
    for i in range(64):
        buf[ord(b64[i])] = i

    L = len(s)
    if L < 2:
        raise ValueError
    for i in reversed(list(range(L - 1))):
        if buf[ord(s[i])] == 0:
            L -= 1
        else:
            break
    if L < 2:
        raise ValueError

    d = [0] * L
    i, k = 0, 0
    while True:
        i += 1
        if k + 1 < L:
            d[i - 1] = buf[ord(s[k])] << 2
            d[i - 1] %= 0x100
        else:
            break
        k += 1
        if k < L:
            d[i - 1] |= buf[ord(s[k])] >> 4
        else:
            break
        i += 1
        if k + 1 < L:
            d[i - 1] = buf[ord(s[k])] << 4
            d[i - 1] %= 0x100
        else:
            break
        k += 1
        if k < L:
            d[i - 1] |= buf[ord(s[k])] >> 2
        else:
            break
        i += 1
        if k + 1 < L:
            d[i - 1] = buf[ord(s[k])] << 6
            d[i - 1] %= 0x100
        else:
            break
        k += 1
        if k < L:
            d[i - 1] |= buf[ord(s[k])] % 0x100
        else:
            break
        k += 1
    return bytes(d[0:i - 1])


def dh_validate_public(public, q, p):
    """See RFC 2631 section 2.1.5."""
    return 1 == pow(public, q, p)


class DH1080Ctx:
    """DH1080 context."""

    def __init__(self, cbc=True):
        self.public = 0
        self.private = 0
        self.secret = 0
        self.state = 0
        self.cbc = cbc

        bits = 1080
        while True:
            self.private = bytes2int(urandom(bits // 8))
            self.public = pow(g_dh1080, self.private, p_dh1080)
            if 2 <= self.public <= p_dh1080 - 1 and \
               dh_validate_public(self.public, q_dh1080, p_dh1080) == 1:
                break


def dh1080_pack(ctx):
    """."""
    if ctx.state == 0:
        ctx.state = 1
        cmd = "DH1080_INIT "
    else:
        cmd = "DH1080_FINISH "
    return cmd + dh1080_b64encode(int2bytes(ctx.public)) + (
        " CBC" if ctx.cbc else "")


def dh1080_unpack(msg, ctx):
    """."""
    if not msg.startswith("DH1080_"):
        raise ValueError

    if ctx.state == 0:
        if (not msg.startswith("DH1080_INIT ") and
                not msg.startswith("DH1080_INIT_CBC ")):
            raise ValueError
        ctx.state = 1
        try:
            cmd, public_raw, *rest = msg.split(' ')
            public = bytes2int(dh1080_b64decode(public_raw))

            if not 1 < public < p_dh1080:
                raise ValueError

            ctx.secret = pow(public, ctx.private, p_dh1080)
            ctx.cbc = "CBC" in rest or cmd == "DH1080_INIT_CBC"

        except Exception as e:
            raise ValueError from e

    elif ctx.state == 1:
        if not msg.startswith("DH1080_FINISH "):
            raise ValueError
        ctx.state = 1
        try:
            cmd, public_raw, *rest = msg.split(' ')
            public = bytes2int(dh1080_b64decode(public_raw))

            if not 1 < public < p_dh1080:
                raise ValueError

            ctx.secret = pow(public, ctx.private, p_dh1080)
            ctx.cbc = "CBC" in rest

        except Exception as e:
            raise ValueError from e

    return True


def dh1080_secret(ctx):
    """."""
    if ctx.secret == 0:
        raise ValueError
    return dh1080_b64encode(sha256(int2bytes(ctx.secret)))


def bytes2int(b):
    """Variable length big endian to integer."""
    n = 0
    for p in b:
        n *= 256
        n += p
    return n


def int2bytes(n):
    """Integer to variable length big endian."""
    if n == 0:
        return b'\x00'
    b = []
    while n:
        b.insert(0, n % 256)
        n //= 256
    return bytes(b)


def sha256(s):
    """sha256"""
    return hashlib.sha256(s).digest()


##
#  END Blowfish and DH1080 Code
##
#
# HOOKS
#

def fish_modifier_in_notice_cb(data, modifier, server_name, string):
    if isinstance(string, bytes):
        return string

    msg_info = weechat.info_get_hashtable('irc_message_parse', {
        'message': string,
        'server': server_name,
    })

    is_direct = msg_info['channel'] == weechat.info_get(
        'irc_nick', server_name)
    if is_direct:
        dest = msg_info['nick']
    else:
        dest = msg_info['channel']
    target = f'{server_name}/{dest}'
    buffer = weechat.info_get("irc_buffer", f'{server_name},{dest}')

    text = msg_info['text']
    if (is_direct and text.startswith('DH1080_FINISH ') and
            target in fish_DH1080ctx and
            dh1080_unpack(text, fish_DH1080ctx[target])):
        fish_alert(buffer, f'Key exchange for {target} successful')
        fish_key_set(target, dh1080_secret(fish_DH1080ctx[target]),
                     fish_DH1080ctx[target].cbc)
        del fish_DH1080ctx[target]

        return ""

    if (
            is_direct and
            (text.startswith('DH1080_INIT ') or
             text.startswith('DH1080_INIT_CBC ')) and
            fish_DH1080ctx.__setitem__(target, DH1080Ctx()) is None and
            dh1080_unpack(text, fish_DH1080ctx[target])):
        reply = dh1080_pack(fish_DH1080ctx[target])
        fish_key_delete(target)
        weechat.command(
            buffer, f"/mute notice -server {server_name} {dest} {reply}")
        fish_key_set(target, dh1080_secret(
            fish_DH1080ctx[target]), fish_DH1080ctx[target].cbc)
        fish_alert(buffer, f"Key exchange initiated by {target}. Key set.")
        del fish_DH1080ctx[target]

        return ""

    key = fish_key_get(target)
    if key is None:
        return string
    if not (text.startswith('+OK ') or text.startswith('mcps ')):
        fish_announce_unencrypted(buffer, target)
        return fish_tag(string)

    try:
        key, cbc = key
        clean, cbc = blowcrypt_unpack(text, key)
        preamble = fish_tag(
            string[0:int(msg_info['pos_text'])],
            'cbc' if cbc else 'ecb')
        fish_announce_encrypted(buffer, target, cbc)

        return b'%s%s' % (preamble.encode(), clean)

    except Exception:
        fish_alert('', traceback.format_exc())
        fish_announce_unencrypted(buffer, target)
        return fish_tag(string)


def fish_modifier_in_privmsg_cb(data, modifier, server_name, string):
    if isinstance(string, bytes):
        return string

    msg_info = weechat.info_get_hashtable('irc_message_parse', {
        'message': string,
        'server': server_name,
    })
    if msg_info['channel'] == weechat.info_get('irc_nick', server_name):
        dest = msg_info['nick']
    else:
        dest = msg_info['channel']
    target = f'{server_name}/{dest}'
    buffer = weechat.info_get('irc_buffer', f'{server_name},{dest}')

    key = fish_key_get(target)
    if key is None:
        return string

    key, cbc = key
    text = msg_info['text']
    is_action = text.startswith("\x01ACTION ") and text.endswith("\x01")
    if is_action:
        text = text[8:-1]
    if not (text.startswith('+OK ') or text.startswith('mcps ')):
        fish_announce_unencrypted(buffer, target)
        return fish_tag(string)

    try:
        clean, cbc = blowcrypt_unpack(text, key)
        if is_action:
            clean = b"\x01ACTION %s\x01" % clean
        preamble = fish_tag(
                string[0:int(msg_info['pos_text'])],
                'cbc' if cbc else 'ecb')
        fish_announce_encrypted(buffer, target, cbc)

        return b"%s%s" % (
            preamble.encode(), clean)

    except Exception:
        fish_alert('', traceback.format_exc())
        fish_announce_unencrypted(buffer, target)
        return fish_tag(string)


def fish_modifier_in_decrypt_cb(data, modifier, server_name, string):
    if isinstance(string, bytes):
        return string

    msg_info = weechat.info_get_hashtable('irc_message_parse', {
        'message': string,
        'server': server_name,
    })

    target = f"{server_name}/{msg_info['channel']}"
    buffer = weechat.info_get(
        "irc_buffer", f"{server_name},{msg_info['channel']}")

    key = fish_key_get(target)
    text = msg_info['text']
    if key is None:
        return string

    key, cbc = key
    if not text:
        return fish_tag(string, 'cbc' if cbc else 'ecb')
    if not (text.startswith('+OK ') or text.startswith('mcps ')):
        fish_announce_unencrypted(buffer, target)
        return fish_tag(string)

    try:
        clean, cbc = blowcrypt_unpack(text, key)
        preamble = fish_tag(
            string[0:int(msg_info['pos_text'])],
            'cbc' if cbc else 'ecb')
        fish_announce_encrypted(buffer, target, cbc)

        return b"%s%s" % (preamble.encode(), clean)

    except Exception:
        fish_alert('', traceback.format_exc())
        fish_announce_unencrypted(buffer, target)
        return fish_tag(string)


def fish_modifier_out_encrypt_cb(data, modifier, server_name, string):
    if isinstance(string, bytes):
        return string

    msg_info = weechat.info_get_hashtable('irc_message_parse', {
        'message': string,
        'server': server_name,
    })

    target = f"{server_name}/{msg_info['channel']}"
    buffer = weechat.info_get(
        "irc_buffer", f"{server_name},{msg_info['channel']}")

    key = fish_key_get(target)
    text = msg_info['text']
    if key is None:
        return string

    key, cbc = key
    cypher = blowcrypt_pack(text.encode(), key, cbc) if text else ''
    preamble = string[0:int(msg_info['pos_text'])] if text else string
    fish_announce_encrypted(buffer, target, cbc)

    return f'{preamble}{cypher}'


def fish_line_cb(data: str, line):
    buffer = line['buffer']
    server_name = weechat.buffer_get_string(buffer, "localvar_server")
    target_user = weechat.buffer_get_string(buffer, "localvar_channel")
    target = f'{server_name}/{target_user}'
    key = fish_key_get(target)
    if key is None:
        return {}
    if not weechat.config_boolean(fish_config_option['prefix']):
        return {}
    state = 'plaintext'
    for tag in line['tags'].split(','):
        if tag.startswith('irc_tag_fish='):
            _, state = tag.split('=')
        if tag == 'self_msg':
            _, cbc = key
            state = 'cbc' if cbc else 'ecb'

    item = weechat.config_string(fish_config_option[f'prefix_{state}'])
    color = weechat.color(
        weechat.config_color(fish_config_option[state]))
    return {'prefix': line['prefix'] + f'{color}{item}'}


def fish_bar_cb(data, item, window, buffer, extra_info):
    server_name = weechat.buffer_get_string(buffer, "localvar_server")
    target_user = weechat.buffer_get_string(buffer, "localvar_channel")
    target = f"{server_name}/{target_user}"

    if fish_key_get(target) is None:
        return ''

    state = fish_state_get(buffer, 'unknown')
    item = weechat.config_string(fish_config_option['item'])
    color = weechat.color(weechat.config_color(fish_config_option[state]))

    return f"{color}{item}"


def fish_unload_cb():
    fish_config_write()
    weechat.bar_item_remove(fish_bar_item)

    return weechat.WEECHAT_RC_OK


#
# COMMANDS
#

def fish_cmd_blowkey(data, buffer, args):
    global fish_DH1080ctx

    if args in ['', 'list']:
        fish_list_keys(buffer)

        return weechat.WEECHAT_RC_OK

    argv = args.split(" ")

    if argv[0] == 'setup_bar_item':
        option_name = 'weechat.bar.status.items'
        option = weechat.config_get(option_name)
        if option is None:
            weechat.prnt(buffer, f'{option_name} not found.')
            return weechat.WEECHAT_RC_ERROR
        value = weechat.config_string(option)
        if re.search(r'\b' + re.escape(BAR_ITEM_NAME) + r'\b', value):
            weechat.prnt(buffer, 'Bar item already set up.')
            return weechat.WEECHAT_RC_ERROR
        if re.search(r'\bbuffer_name\b', value):
            value = re.sub(
                r'(buffer_name(\+[^,]*)?)',
                r'\1+' + BAR_ITEM_NAME,
                value)
        else:
            value = (value + ',' if value else '') + BAR_ITEM_NAME
        weechat.command(buffer, f'/set {option_name} "{value}"')

        return weechat.WEECHAT_RC_OK

    if (len(argv) > 2 and argv[1] == "-server"):
        server_name = argv[2]
        del argv[2]
        del argv[1]
        pos = args.find(" ")
        pos = args.find(" ", pos + 1)
        args = args[pos+1:]
    else:
        server_name = weechat.buffer_get_string(buffer, "localvar_server")

    buffer_type = weechat.buffer_get_string(buffer, "localvar_type")
    # if no target user has been specified grab the one from the buffer if it
    # is private
    if argv[0] == "exchange" and len(argv) == 1 and buffer_type == "private":
        target_user = weechat.buffer_get_string(buffer, "localvar_channel")
    elif (argv[0] == "set" and
            buffer_type in ['private', 'channel'] and
            len(argv) == 2):
        target_user = weechat.buffer_get_string(buffer, "localvar_channel")
    elif len(argv) < 2:
        return weechat.WEECHAT_RC_ERROR
    else:
        target_user = argv[1]

    argv2eol = ""
    pos = args.find(" ")
    if pos:
        pos = args.find(" ", pos + 1)
        if pos > 0:
            argv2eol = args[pos + 1:]
        else:
            argv2eol = args[args.find(" ") + 1:]

    target = f'{server_name}/{target_user}'

    if argv[0] == "set":
        cbc = False
        key = argv2eol
        if key.startswith('cbc:'):
            cbc = True
            key = argv2eol[4:]

        fish_key_set(target, key, cbc)

        weechat.prnt(buffer, f'set key for {target} to {argv2eol}')

        return weechat.WEECHAT_RC_OK

    if argv[0] == "remove":
        if not len(argv) == 2:
            return weechat.WEECHAT_RC_ERROR

        if not fish_key_delete(target):
            return weechat.WEECHAT_RC_ERROR

        weechat.prnt(buffer, f'removed key for {target}')

        return weechat.WEECHAT_RC_OK

    if argv[0] == "exchange":
        if server_name == "":
            return weechat.WEECHAT_RC_ERROR

        weechat.prnt(buffer, f'Initiating DH1080 Exchange with {target}')
        fish_DH1080ctx[target] = DH1080Ctx()
        msg = dh1080_pack(fish_DH1080ctx[target])
        fish_key_delete(target)
        weechat.command(
            buffer, f'/mute notice -server {server_name} {target_user} {msg}')

        return weechat.WEECHAT_RC_OK

    return weechat.WEECHAT_RC_ERROR


#
# HELPERS
#

def fish_tag(msg, mode=None):
    tag = f'{TAG_NAME}={mode}' if mode is not None else None
    if msg.startswith('@'):
        msg = re.sub(
            r'^@([^ ]*;|)' +
            re.escape(TAG_NAME) +
            r'(=[^ ;])?(;| )', r'@\1\3',
            msg)
        if tag is not None:
            msg = re.sub(r'^@', f"@{tag};", msg)
    elif tag is not None:
        msg = f'@{tag} {msg}'

    return msg


def fish_announce_encrypted(buffer, target, cbc):
    new_state = 'cbc' if cbc else 'ecb'

    if fish_state_get(buffer) == new_state:
        return

    server, nick = target.split('/')

    if (weechat.info_get('irc_is_nick', nick) and
            weechat.buffer_get_string(buffer, 'localvar_type') != 'private'):
        # if we get a private message and there no buffer yet, create one and
        # jump back to the previous buffer
        weechat.command(buffer, f'/mute query -server {server} {nick}')
        buffer = weechat.info_get('irc_buffer', f'{server},{nick}')
        weechat.command(buffer, '/input jump_previously_visited_buffer')

    if weechat.config_boolean(fish_config_option['announce']):
        fish_alert(
            buffer, f'Messages to/from {target} are encrypted ({new_state}).')

    fish_state_set(buffer, new_state)


def fish_announce_unencrypted(buffer, target):
    if fish_state_get(buffer) == 'plaintext':
        return

    if weechat.config_boolean(fish_config_option['announce']):
        fish_alert(
            buffer, f"Messages to/from {target} are {
                weechat.color(
                    weechat.config_color(fish_config_option['alert']))}*not*{
                weechat.color('chat')} encrypted.")

    fish_state_set(buffer, "plaintext")


def fish_alert(buffer, message):
    mark = f"{
        weechat.color(weechat.config_color(fish_config_option['alert']))}{
        weechat.config_string(fish_config_option['marker'])}{
        weechat.color('chat')}"
    weechat.prnt(buffer, f'{mark}\t{message}')


def fish_list_keys(buffer):
    weechat.command(buffer, f"/set {CONFIG_FILE_NAME}.keys.*")


def fish_state_set(buffer, state):
    if state is None:
        weechat.buffer_set(buffer, f'localvar_del_{SCRIPT_NAME}_state', '')
    else:
        weechat.buffer_set(buffer, f'localvar_set_{SCRIPT_NAME}_state', state)
    weechat.bar_item_update(BAR_ITEM_NAME)


def fish_state_get(buffer, default=None):
    state = weechat.buffer_get_string(buffer, f'localvar_{SCRIPT_NAME}_state')
    if not state:
        state = default

    return state


#
# MAIN
#

if (__name__ == "__main__" and import_ok and
        weechat.register(
            SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
            SCRIPT_DESC, "fish_unload_cb", "")):

    weechat.hook_command(
        "blowkey", "Manage FiSH keys",
        "[list] | set [-server <server>] [<target>] <key> "
        "| remove [-server <server>] <target> "
        "| exchange [-server <server>] [<nick>] "
        "| setup_bar_item",
        "Add, change or remove key for target or perform DH1080 key"
        "exchange with <nick>.\n"
        "Target can be a channel or a nick.\n"
        "\n"
        "Without arguments this command lists all keys.\n"
        "\n"
        "Examples:\n"
        "Set the key for a channel: /blowkey set -server freenet #blowfish"
        " key\n"
        "Remove the key:            /blowkey remove #blowfish\n"
        "Set the key for a query:   /blowkey set nick secret+key\n"
        "List all keys:             /blowkey\n"
        "DH1080:                    /blowkey exchange nick\n"
        "Set up bar item:           /blowkey setup_bar_item\n"
        "\nPlease read the source for a note about DH1080 key exchange\n",
        "list || set %(irc_channel)|%(nicks)|-server %(irc_servers) %- "
        "|| remove %(irc_channel)|%(nicks)|-server %(irc_servers) %- "
        "|| exchange %(nick)|-server %(irc_servers) %- "
        "|| setup_bar_item",
        "fish_cmd_blowkey", "")

    fish_config_init()
    fish_config_read()

    fish_bar_item = weechat.bar_item_new(
        '(extra)' + BAR_ITEM_NAME, 'fish_bar_cb', '')

    weechat.hook_line(
        "", "", "irc_privmsg,irc_topic,irc_notice,irc_332", "fish_line_cb", "")

    weechat.hook_modifier("irc_in_notice", "fish_modifier_in_notice_cb", "")
    weechat.hook_modifier("irc_in_privmsg", "fish_modifier_in_privmsg_cb", "")
    weechat.hook_modifier("irc_in_topic", "fish_modifier_in_decrypt_cb", "")
    weechat.hook_modifier("irc_in_332", "fish_modifier_in_decrypt_cb", "")
    weechat.hook_modifier(
        "irc_out_privmsg", "fish_modifier_out_encrypt_cb", "")
    weechat.hook_modifier("irc_out_topic", "fish_modifier_out_encrypt_cb", "")
    weechat.hook_modifier("irc_out_notice", "fish_modifier_out_encrypt_cb", "")
elif (__name__ == "__main__" and len(sys.argv) == 3):
    key = sys.argv[1]
    msg = sys.argv[2]
    print(blowcrypt_unpack(msg, key))
