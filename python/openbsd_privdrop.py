# Copyright (c) 2022 Alvar Penning <post@0x21.biz>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# The openbsd_privdrop.py script tries to achieve the principle of least
# privilege for a WeeChat running on OpenBSD by restricting both the available
# system operations as well as the available file system paths by pledge(2) and
# unveil(2). As those functions are OpenBSD-specific, this script does not work
# on any other operating system.
#
# The respective filters are set by configuration variables. On first run or in
# the absence of configuration entries, sane defaults are set. These should be
# sufficient for a normal WeeChat installation, but would have to be adjusted,
# for example, when using other scripts or plugins. So the default does not
# allow the execution of other programs and assumes a home directory under
# /home/$USERNAME for unveil(2).
#
# - https://man.openbsd.org/pledge.2
# - https://man.openbsd.org/unveil.2

# History:
#
# 2022-11-09, Alvar Penning <post@0x21.biz>
#   version 0.1.1: sane defaults for unveil
#
# 2022-09-18, Alvar Penning <post@0x21.biz>
#   version 0.1.0: initial release


import ctypes
import os
import sys
import weechat


SCRIPT_NAME    = "openbsd_privdrop"
SCRIPT_AUTHOR  = "Alvar Penning <post@0x21.biz>"
SCRIPT_VERSION = "0.1.1"
SCRIPT_LICENSE = "ISC"
SCRIPT_DESC    = "Drop WeeChat's privileges through OpenBSD's pledge(2) and unveil(2)."

SETTINGS = {
        "pledge_promises": (
            "stdio rpath wpath cpath dpath inet flock unix dns sendfd recvfd tty proc error",
            "List of promises for pledge(2).",
            ),
        "pledge_execpromises": (
            "",
            "List of promises to executed processes; requires exec in pledge_promises.",
            ),
        "unveil": (
            ";".join([
                # Full read/write access (no exec!) to the user's home directory.
                # This may be tightened, especially if WeeChat is not run as a separate user.
                "~:rwc",
                # WeeChat `stat`s /home while building the path to /home/$USER/...
                # Might be changed if the home directory lies somehwere else.
                "/home:r",
                # Other scripts might load some library or a third-party Python modules later.
                "/usr/local/lib:r",
                # Necessary for HTTPS validation, e.g., when downloading WeeChat scripts.
                "/etc/ssl/cert.pem:r",
                ]),
            "List of path and permissions for unveil(2). Format: /a/path:rwc;/another/path:rw",
            ),
}


def libc_func(name):
    """ Returns a libc function, e.g., pledge or unveil.
        Inspired by https://nullprogram.com/blog/2021/09/15/
    """
    f = ctypes.CDLL(None, use_errno=True)[name]

    def _call_f(*args):
        weechat.prnt("", f"*\t{name}{args}")
        if f(*args) == -1:
            errno = ctypes.get_errno()
            raise OSError(errno, os.strerror(errno))

    return _call_f


def config_get(key):
    """ Fetch a stored configuration value and normalize the returned string
        for libc usage by replacing empty strings through None and converting
        non-empty strings to bytes.
    """
    value = weechat.config_get_plugin(key)
    return value.encode() if value != "" else None


def weechat_pledge():
    """ Execute pledge(2) for the configured promise.
    """
    pledge = libc_func("pledge")

    promises = config_get("pledge_promises")
    execpromises = config_get("pledge_execpromises")

    pledge(promises, execpromises)


def weechat_unveil():
    """ Execute unveil(2) for the configured paths.
        Unveil should be called before pledge unless "unveil" is promised.
    """
    unveil = libc_func("unveil")

    for path_part in config_get("unveil").split(b";"):
        path, permissions = path_part.split(b":")
        path = weechat.string_eval_path_home(path.decode(), {}, {}, {}).encode()
        unveil(path, permissions)

    unveil(None, None)


def main():
    """ Main function to load the script and apply the restrictions.
    """
    reg = weechat.register(
            SCRIPT_NAME,
            SCRIPT_AUTHOR,
            SCRIPT_VERSION,
            SCRIPT_LICENSE,
            SCRIPT_DESC,
            "", "")
    if not reg:
        return

    if not sys.platform.startswith("openbsd"):
        weechat.prnt("", f"{SCRIPT_NAME} is only supported on OpenBSD")
        return

    for key, value in SETTINGS.items():
        if not weechat.config_is_set_plugin(key):
            weechat.config_set_plugin(key, value[0])
            weechat.config_set_desc_plugin(key, f"{value[1]} (default: \"{value[0]}\")")

    weechat_unveil()
    weechat_pledge()


if __name__ == "__main__":
    main()
