# SPDX-FileCopyrightText: 2022-2026 Sébastien Helleu <flashcode@flashtux.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""QR code generator."""

import io

import qrcode

IMPORT_OK = True
try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    IMPORT_OK = False

SCRIPT_NAME = "qr_code"
SCRIPT_AUTHOR = "Sébastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "1.0.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "QR code generator"

SCRIPT_COMMAND = "qrcode"
SCRIPT_INFO = "qrcode"
SCRIPT_BUFFER = "qrcode"


def qrcode_input_buffer(_data: str, buffer: str, str_input: str) -> int:
    """Input data in qrcode buffer."""
    if str_input.lower() == "q":
        weechat.buffer_close(buffer)
    else:
        qrcode_display(str_input, qrcode_generate(str_input))
    return weechat.WEECHAT_RC_OK


def qrcode_close_buffer(_data: str, _buffer: str) -> int:
    """Close qrcode buffer."""
    return weechat.WEECHAT_RC_OK


def qrcode_open_buffer(force_display: bool = False) -> str:
    """Open qrcode buffer."""
    qrcode_buffer: str = weechat.buffer_search("python", SCRIPT_BUFFER)
    if not qrcode_buffer:
        qrcode_buffer = weechat.buffer_new(
            SCRIPT_BUFFER,
            "qrcode_input_buffer",
            "",
            "",
            "",
        )
        weechat.buffer_set(qrcode_buffer, "display", "1")
    elif force_display:
        weechat.buffer_set(qrcode_buffer, "display", "1")
    return qrcode_buffer


def qrcode_generate(data: str) -> str:
    """Generate and return a QR code as ASCII."""
    try:
        qr = qrcode.QRCode(border=0)
        qr.add_data(data)
        f = io.StringIO()
        qr.print_ascii(out=f)
        f.seek(0)
    except Exception as err:  # noqa: BLE001
        weechat.prnt(
            "",
            f'{weechat.prefix("error")}Error generating QR code with data "{data}": {err}',
        )
        return ""
    return f.getvalue()


def qrcode_display(data: str, qr_code: str) -> None:
    """Display the QR code."""
    if qr_code:
        qrcode_buffer = qrcode_open_buffer()
        if qrcode_buffer:
            weechat.prnt(qrcode_buffer, f"{data}\n\n{qr_code}\n")


def qrcode_info_cb(_data: str, _info_name: str, arguments: str) -> str:
    """Return a QR code as string."""
    return qrcode_generate(arguments) if arguments else ""


def qrcode_cmd_cb(_data: str, _buffer: str, args: str) -> int:
    """Execute command /qrcode."""
    if args:
        qrcode_display(args, qrcode_generate(args))
    else:
        qrcode_open_buffer(force_display=True)
    return weechat.WEECHAT_RC_OK


if (
    __name__ == "__main__"
    and IMPORT_OK
    and weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        "",
        "",
    )
):
    weechat.hook_command(
        SCRIPT_COMMAND,
        "Generate and display QR codes.",
        "[data]",
        "data: data to encode in QR code, it can be an URL, eg: https://google.com",
        "",
        "qrcode_cmd_cb",
        "",
    )
    weechat.hook_info(
        SCRIPT_INFO,
        "Generate a QR code and return it as string (with newlines)",
        "data to encode in QR code, it can be an URL, eg: https://google.com",
        "qrcode_info_cb",
        "",
    )
