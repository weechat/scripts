# -*- coding: utf-8 -*-

# Copyright (c) 2017-2019 oakkitten <jatjasjem@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
Why yet another url script? Well, this is what sets this one apart from others:
  * always visible hints for urls (by default looks like ¹http://this)
  * the hints change as the urls appear. hint ¹ always points to the last url, ² to the second last, etc
  * you can open these with keyboard shortcuts — just one key press to open an url!
  * it can be made to work even when your weechat is on a remote machine through your OS or terminal emulator
  * a ready recipe for opening urls from your PuTTY!

So, this script prepends tiny digits to links, ¹ to the latest url, ² to the second latest, etc. \\
Also, it can put these urls in the window title, which you can grab using your OS automation, or your terminal emulator. \\
This is an example script in AutoHotkey that works with PuTTY (just install ahk, save this to file.ahk and run it):

  #IfWinActive, ahk_class PuTTY
    F1::
    F2::
    F3::
    F4::
    F5::
      WinGetTitle, title
      if (!RegExMatch(title, "[^""]+""urls: (.+)""", out))
        Return
      url := StrSplit(out1, " ")[SubStr(A_ThisHotkey, 2)]
      If (RegExMatch(url, "^(?:http|www)"))
        Run, %url%
    Return
  #IfWinActive

You can use command /url_hint_replace that replaces {url1}, {url2}, etc with according urls and then \\
executes the result. For example, the following will open url 1 in your default browser:
  /url_hint_replace /exec -bg xdg-open {url1}

or in elinks a new tmux window:
  /url_hint_replace /exec -bg tmux new-window elinks {url1}

You can bind opening of url 1 to f1 and url 2 to f2 like this, for example (press meta-k, then f1. that prints `meta2-11~`):
  /alias add open_url /url_hint_replace /exec -bg tmux new-window elinks {url$1}
  /key bind meta2-11~ /open_url 1
  /key bind meta2-12~ /open_url 2

WARNING: Avoid passing urls to the shell as they can contain special characters. \\
If you must do that, consider setting the option safe_urls to "base64".

Configuration (plugins.var.python.url_hint.*):
  * max_lines: the maximum number of lines that contain urls to track ("10")
  * no_urls_title: title for buffers that don't contain urls ("weechat")
  * prefix: the beginning of the title when there are urls ("urls: ")
  * delimiter: what goes between the urls in the title (" ")
  * postfix: the end of the title when there are urls ("")
  * hints: comma-separated list of hints. evaluated, can contain colors ("⁰,¹,²,³,⁴,⁵,⁶,⁷,⁸,⁹")
  * update_title: whether the script should put urls into the title ("on")
  * safe_urls: whether the script will convert urls to their safe ascii equivalents. can be either "off", \\
    "on" for idna- & percent-encoding, or "base64" for utf-8 base64 encoding ("off")

Notes:
  * to avoid auto renaming tmux windows use :set allow-rename off
  * in PuTTyTray and possibly other clients, window titles are parsed using wrong charset (see bug #88). \\
    The option safe_urls must be set to non-"off" value to avoid issues

Limitations:
  * will not work with urls that have color codes inside them
  * will be somewhat useless in merged and zoomed buffers

Version history:
  0.8 (21 august 2019): fixed minor issues in url detections and improved code quality
  0.7 (4 august 2019): py3 compatibility
  0.6 (26 june 2017): renamed /url_hint to /url_hint_replace; /url_hint simply prints help now
  0.5 (22 june 2017): implemented base64 encoding of urls
  0.4 (18 june 2017): encode fewer characters for safe urls—helps with servers that don't follow the rfc
  0.3 (10 june 2017): don't fail when safe url encoding fails
  0.2 (4 june 2017): don't crash if a new buffer has the same pointer as the old one
  0.1 (30 may 2017): added an option to make safe urls
  0.0 (6 may 2017): initial release
'''

from __future__ import unicode_literals, print_function
import re
import sys
from base64 import b64encode

MYPY = False
if MYPY:
    # noinspection PyUnresolvedReferences
    from typing import Match, Pattern, Generator, List, Union, Optional, Any, Callable, Dict, Tuple

PY3 = sys.version_info[0] >= 3
if PY3:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from urllib.parse import quote_from_bytes, unquote_to_bytes
    from_weechat = to_weechat = lambda s: s
else:
    # noinspection PyUnresolvedReferences
    from urllib import quote as quote_from_bytes, unquote as unquote_to_bytes
    from_weechat, to_weechat = lambda s: s.decode("utf-8"), lambda s: s.encode("utf-8")
    # noinspection PyUnresolvedReferences,PyShadowingBuiltins
    str = unicode

SCRIPT_NAME = "url_hint"
SCRIPT_VERSION = "0.8"
SCRIPT_DOC = re.sub(r" *\\\n *", " ", __doc__.strip())

# the following code constructs a simple but neat regular expression for detecting urls
# it's by no means perfect, but it will detect an url in quotes and parentheses, http iris,
# punycode, urls followed by punctuation and such
def construct_url_finder_pattern():
    ipv4_segment = r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    ipv6_segment = r"[0-9A-Fa-f]{1,4}"

    # 00-1f     c0 control chars
    # 20        space
    # 21-2f     !"#$%&'()*+,-./
    # 30-39         0123456789
    # 3a-40     :;<=>?@
    # 41-5a         ABCDEFGHIJKLMNOPQRSTUVWXYZ
    # 5b-60     [\]^_`
    # 61-7a         abcdefghijklmnopqrstuvwxyz
    # 7b-7e     {|}~
    # 7f        del
    # 80-9f     c1 control chars
    # a0        nbsp
    good_ascii_char = r"[A-Za-z0-9]"
    bad_char = r"\x00-\x20\x7f-\xa0\ufff0-\uffff\s"
    good_char = r"[^{bad}]".format(bad=bad_char)
    good_host_char = r"[^\x00-\x2f\x3a-\x40\x5b-\x60\x7b-\xa0\ufff0-\uffff]"
    good_tld_char = r"[^\x00-\x40\x5b-\x60\x7b-\xa0\ufff0-\uffff]"

    host_segment = r"""{good_host}+(?:-+{good_host}+)*""".format(good_host=good_host_char)
    tld = r"(?:{good_tld}{{2,}}|xn--{good_ascii}+)".format(good_ascii=good_ascii_char, good_tld=good_tld_char)

    # language=PythonVerboseRegExp
    url = r"""
        # url must be preceded by a word boundary, or a weechat color (a control character followed by a digit)
        (?:(?<=\d)|\b)
    
        # http:// or www  =1=
        (https?://|www\.)
    
        # optional userinfo at  =2=
        (?:([^{bad}@]*)@)?
    
        # ip or host  =3=
        (
            # ipv4
            (?:(?:{s4}\.){{3}}{s4})
        |
            # ipv6 (no embedded ipv4 tho)
            \[
            (?:
                                              (?:{s6}:){{7}} {s6}
                |                          :: (?:{s6}:){{6}} {s6}
                | (?:               {s6})? :: (?:{s6}:){{5}} {s6}
                | (?:(?:{s6}:)?     {s6})? :: (?:{s6}:){{4}} {s6}
                | (?:(?:{s6}:){{,2}}{s6})? :: (?:{s6}:){{3}} {s6}
                | (?:(?:{s6}:){{,3}}{s6})? :: (?:{s6}:){{2}} {s6}
                | (?:(?:{s6}:){{,4}}{s6})? :: (?:{s6}:)      {s6}
                | (?:(?:{s6}:){{,5}}{s6})? ::                {s6}
                | (?:(?:{s6}:){{,6}}{s6})? ::
            )
            \]
        |
            # domain name (a.b.c.com)
            {host_segment}
            (?:\.{host_segment})*
            \.{tld}
            
            # fqdn dot, but only if followed by url-ish things
            (?:\.(?=/|:\d))?
        )
    
        # port?  =4=
        (:\d{{1,5}})?
    
        # / & the rest  =5=
        (
            /
            # hello(world) in "hello(world))"
            (?:
                [^{bad}(]*
                \(
                [^{bad})]+
                \)
            )*
            # any string (non-greedy!)
            {good}*?
        )?
    
        # url must be directly followed by:
        (?=
            # some possible punctuation
            # AND space or end of string
            [\]>,.)!?:'"”@]*
            (?:[{bad}]|$)
        )
        """
    url = url.format(s4=ipv4_segment, s6=ipv6_segment, bad=bad_char, good=good_char, host_segment=host_segment, tld=tld)
    return re.compile(url, re.U | re.X | re.I)
RE_URL = construct_url_finder_pattern()

H_BUFFER, H_LINES, H_LINE, H_LINE_DATA, H_GUI_BUFFERS = None, None, None, None, None    # make mypy happy

###############################################################################
###############################################################################
###############################################################################

# noinspection PyPep8Naming
class lazy(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, cls):
        value = self.fget(obj)
        setattr(obj, self.fget.__name__, value)
        return value

class Url(object):
    """
    an object that represents an url

    exact (str): exact url, may contain non-ascii characters
    safe (str): safe url using punycode and percent-escaped characters
    base64 (str): safe url, encoded with utf-8 base64
    url (str): exact or safe or base64, depending on current settings
    """
    def __init__(self, match):                      # type: (Match) -> None
        self._match = match
        self.exact = match.group(0)

    @lazy
    def safe(self):                                 # type: () -> str
        prefix, userinfo, ip_or_host, c_port, rest = self._match.groups()
        safe = prefix
        if userinfo: safe += q(userinfo, safe=SAFE_USERINFO) + "@"
        safe += ip_or_host.encode("idna").decode("utf-8")
        if c_port: safe += c_port
        if rest:
            end = ""
            if "#" in rest:
                rest, fragment = rest.split("#", 1)
                end = "#" + q(fragment, safe=SAFE_FRAGMENT)
            if "?" in rest:
                rest, query = rest.split("?", 1)
                end = "?" + q(query, safe=SAFE_QUERY) + end
            safe += "/".join(q(segment, safe=SAFE_PATH) for segment in rest.split("/"))
            safe += end
        return safe

    @lazy
    def base64(self):                               # type: () -> str
        return b64encode(self.exact.encode("utf-8")).decode("utf-8")

    @property
    def url(self):                                  # type: () -> str
        return getattr(self, C[SAFE])

# these are used to encode the url in a safe manner. basically it's url normalization, but it will not fail while
# encoding invalid urls and it changes as little as possible
# the following are direct quotes from https://tools.ietf.org/html/rfc3986
#     unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
#     sub-delims    = "!" / "$" / "&" / "'" / "(" / ")" / "*" / "+" / "," / ";" / "="
#     pct-encoded   = "%" HEXDIG HEXDIG
#     pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
#     userinfo      = *( unreserved / pct-encoded / sub-delims / ":" )
#     segment       = *pchar
#     query         = *( pchar / "/" / "?" )
#     fragment      = *( pchar / "/" / "?" )
SUB_DELIMS = b"!$&'()*+,;="
SAFE_USERINFO = SUB_DELIMS + b":"
SAFE_PATH = SUB_DELIMS + b":@"
SAFE_FRAGMENT = SAFE_QUERY = SUB_DELIMS + b":@" + b"/?"

# this uses bytes as urls do not necessarily contain unicode in them. for instance,
# the string `%FF?%FE#%FF` unquoted to unicode becomes `�?�#�` (that's 3 U+FFFD replacement
# characters) instead of b'\xff?\xfe#\xff'.
def q(string, safe):                                # type: (str, bytes) -> str
    out = quote_from_bytes(unquote_to_bytes(string.encode("utf-8")), safe=safe)    # type: Any
    return out if PY3 else out.decode("utf-8")

def find_urls(string):                              # type: (str) -> Generator[Union[str, Url], None, None]
    last_end = 0
    for match in RE_URL.finditer(string):
        if not is_valid_url(match):
            continue
        start, end = match.span()
        yield string[last_end:start]
        yield Url(match)
        last_end = end
    yield string[last_end:]

# domain name (a.b.c.d.) can be a maximum of 253 characters, not counting the FQDN dot;
# each label (a, b, ...) can be a maximum of 63 characters long
def is_valid_url(match):                            # type: (Match) -> bool
    domain_name = match.group(3).rstrip(".")
    try:
        domain_name.encode("idna")
    except UnicodeError:                            # fired if label length is wrong
        return False
    if len(domain_name) > 253:
        return False
    return True

###############################################################################
###############################################################################
###############################################################################

class Line(object):
    """
    an object that represents a buffer line with urls

    pointer (str): a hex pointer to line object in weechat
    urls ([Url]): a list of urls in reverse order

    is_of_pointer(pointer): True if this line corresponds to given pointer
    redraw(index): redraw the line and assign new hints to urls, given index of last hint
    reset(): restore the line to its original condition
    """
    def __init__(self, pointer, message, parts):    # type: (str, str, List[Union[str, Url]]) -> None
        assert pointer
        self.pointer = pointer
        self.urls = parts[-2::-2]                   # type: List[Url] # type: ignore
        self._data = weechat.hdata_pointer(H_LINE, pointer, "data")
        self._original_message = message
        self._current_message = message
        self._parts = [part.exact if isinstance(part, Url) else part for part in parts]
        for i in range(1, len(self._parts) * 3 // 2, 3):
            self._parts.insert(i, None)

    def is_of_pointer(self, pointer):               # type: (str) -> bool
        return self.pointer == pointer and self._data == weechat.hdata_pointer(H_LINE, pointer, "data") and \
               self._current_message == from_weechat(weechat.hdata_string(H_LINE_DATA, self._data, "message"))

    def redraw(self, index):                        # type: (int) -> None
        self._parts[1::3] = (get_hint(i) for i in reversed(range(index, index + len(self.urls))))
        self._set_message("".join(self._parts))

    def reset(self):                                # type: () -> None
        self._set_message(self._original_message)

    def _set_message(self, message):                # type: (str) -> None
        self._current_message = message
        weechat.hdata_update(H_LINE_DATA, self._data, {"message": to_weechat(message)})

def get_hint(i):                                    # type: (int) -> str
    hints = C[HINTS]
    def do_it(j):
        d, m = divmod(j, len(hints))
        return do_it(d) + hints[m] if d else hints[m]
    return do_it(i)

###############################################################################
###############################################################################
###############################################################################

class Buffer(object):
    """
    an object that represents a buffer

    pointer (str): a hex pointer to buffer object in weechat
    urls ([Url]): a list of recent urls, in reverse order

    on_message(): called on every visible message on a buffer
    valid(): returns True if this buffer still exists in weechat and is safe to operate on
    redraw(full_reset): redraw all lines. if full_reset is True, restores all lines to their original conditions
    """
    def __init__(self, pointer):                    # type: (str) -> None
        assert pointer
        self.pointer = pointer
        self.urls = []                              # type: List[Url]
        self._lines = []                            # type: List[Line]      # (reverse order)

    def on_message(self, message):                  # type: (str) -> None
        parts = list(find_urls(message))            # parts = ["text", url, "text", url, ""]
        if len(parts) < 3:
            return
        line_pointer = self.get_last_line_pointer()
        if not line_pointer:
            return
        line = Line(line_pointer, message, parts)
        self._lines.insert(0, line)
        self.redraw(last_pointer=line.pointer)

    def redraw(self, last_pointer=None, full_reset=False):  # type: (Optional[str], bool) -> None
        if last_pointer is None:
            last_pointer = self.get_last_line_pointer()

        max_lines = 0 if full_reset else C[MAX_LINES]       # type: int
        lines, urls = [], []                                # type: List[Line], List[Url]
        walker = line_reverse_walker(last_pointer)
        for n, line in enumerate(self._lines):
            for pointer in walker:
                if line.is_of_pointer(pointer):
                    if n >= max_lines:
                        line.reset()
                    else:
                        line.redraw(len(urls) + 1)
                        urls += line.urls
                        lines.append(line)
                    break
            else:
                break
        self._lines, self.urls = lines, urls

    # return pointer to the last line, visible or not; None otherwise
    def get_last_line_pointer(self):                # type: () -> Optional[str]
        try:
            assert weechat.hdata_check_pointer(H_BUFFER, H_GUI_BUFFERS, self.pointer)
            own_lines = weechat.hdata_pointer(H_BUFFER, self.pointer, "own_lines"); assert own_lines
            last_line = weechat.hdata_pointer(H_LINES, own_lines, "last_line"); assert last_line
        except AssertionError:
            return None
        return last_line

def line_reverse_walker(pointer):                   # type: (Optional[str]) -> Generator[str, None, None]
    while pointer:
        yield pointer
        pointer = weechat.hdata_move(H_LINE, pointer, -1)

###############################################################################
###############################################################################
###############################################################################

class Buffers(dict):
    def __missing__(self, key):
        return self.setdefault(key, Buffer(key))
buffers = Buffers()
current_buffer = ""

# see the note at https://weechat.org/files/doc/devel/weechat_plugin_api.en.html#_hook_print
def on_print(_data, pointer, _date, _tags, displayed, _highlighted, _prefix, message):   # type: (str, str, str, str, Union[str, int], Union[str, int], str, str) -> int
    displayed = int(displayed)
    if displayed:
        buffers[pointer].on_message(from_weechat(message))
        if C[UPDATE_TITLE] and current_buffer == pointer:
            update_title()
    return weechat.WEECHAT_RC_OK

def on_buffer_switch(_data, _signal, pointer):      # type: (str, str, str) -> int
    global current_buffer
    if C[UPDATE_TITLE] and current_buffer != pointer:
        current_buffer = pointer
        update_title()
    return weechat.WEECHAT_RC_OK

def update_title():                                 # type: () -> None
    if not current_buffer: return
    urls = buffers[current_buffer].urls
    title = (C[PREFIX] + C[DELIMITER].join(url.url for url in urls) + C[POSTFIX]) if urls else C[NO_URLS_TITLE]     # type: ignore
    weechat.window_set_title(to_weechat(title))

RE_REP = re.compile(r"{url(\d+)}", re.I)

# simply print help
def url_hint(_data, _pointer, _command):            # type: (str, str, str) -> int
    weechat.prnt("", to_weechat(SCRIPT_DOC))
    return weechat.WEECHAT_RC_OK

def url_hint_replace(_data, pointer, command):      # type: (str, str, str) -> int
    urls = buffers[pointer].urls
    def get_url(match):
        try: return urls[int(match.group(1)) - 1].url
        except IndexError: raise IndexError("could not replace " + match.group(0))
    try: weechat.command(pointer, to_weechat(RE_REP.sub(get_url, from_weechat(command))))
    except IndexError as e: print_error(str(e))
    return weechat.WEECHAT_RC_OK

def print_error(text):                              # type: (str) -> None
    weechat.prnt("", to_weechat("%s%s: %s" % (weechat.prefix("error"), SCRIPT_NAME, text)))

def redraw_everything(full_reset):                  # type: (bool) -> int
    for pointer, buffer in buffers.items():
        buffer.redraw(full_reset=full_reset)
    update_title()
    return weechat.WEECHAT_RC_OK

def exit_function():                                # type: () -> int
    return redraw_everything(full_reset=True)

###############################################################################
###############################################################################
###############################################################################

def hints_from_string(x):                           # type: (str) -> Optional[List[str]]
    hints = from_weechat(weechat.string_eval_expression(to_weechat(x), "", "", "")).split(",")
    return None if len(hints) < 2 or any(not hint.strip() for hint in hints) else hints

def boolean_from_string(x):                         # type: (str) -> Optional[bool]
    return {"on": True, "off": False}.get(x.lower(), None)

def safe_from_string(x):                            # type: (str) -> Optional[str]
    return {"off": "exact", "on": "safe", "base64": "base64"}.get(x.lower(), None)

MAX_LINES = "max_lines"
NO_URLS_TITLE = "no_urls_title"
PREFIX, DELIMITER, POSTFIX = "prefix", "delimiter", "postfix"
UPDATE_TITLE = "update_title"
HINTS = "hints"
SAFE = "safe_urls"

# setting name: (default value, default value as stored in weechat, a method of converting/validating that
# returns None if invalid, description)
DEFAULT_CONFIG = {
    MAX_LINES: ("10", "the maximum number of lines that contain urls to track", lambda x: int(x) if x.isdigit() and int(x) > 0 else None),
    NO_URLS_TITLE: ("weechat", "title for buffers that don't contain urls", None),
    PREFIX: ("urls: ", "the beginning of the title when there are urls", None),
    DELIMITER: (" ", "what goes between the urls in the title", None),
    POSTFIX: ("", "the end of the title when there are urls", None),
    HINTS: ("⁰,¹,²,³,⁴,⁵,⁶,⁷,⁸,⁹", "comma-separated list of hints. evaluated, can contain colors", hints_from_string),
    UPDATE_TITLE: ("on", "whether the script should put urls into the title", boolean_from_string),
    SAFE: ("off", """whether the script will convert urls to their safe ascii equivalents. can be either "off", "on" for idna- & percent-encoding, or "base64" for utf-8 base64 encoding""", safe_from_string)
}                                                   # type: Dict[str, Tuple[str, str, Optional[Callable]]]

C = {}                                              # type: Dict[str, Any]

def load_config(*_):                                # type: (Any) -> int
    for name, (default, description, from_string) in DEFAULT_CONFIG.items():
        value = None
        if weechat.config_is_set_plugin(name):
            value = from_weechat(weechat.config_get_plugin(name))
            if from_string: value = from_string(value)
        if value is None:
            value = from_string(default) if from_string else default
            weechat.config_set_plugin(name, to_weechat(default))
            weechat.config_set_desc_plugin(name, to_weechat('%s (default: "%s")' % (description, default)))
        C[name] = value
    redraw_everything(full_reset=False)
    return weechat.WEECHAT_RC_OK

###############################################################################
###############################################################################
###############################################################################

def install():
    global H_BUFFER, H_LINES, H_LINE, H_LINE_DATA, H_GUI_BUFFERS
    if not weechat.register(SCRIPT_NAME, "oakkitten", SCRIPT_VERSION, "MIT",
                            "Display hints for urls and open them with keyboard shortcuts", "exit_function", ""):
        raise Exception("Could not register script")

    weechat_version = int(weechat.info_get('version_number', '') or 0)
    if weechat_version <= 0x00040000:
        raise Exception("Need Weechat 0.4 or higher")

    H_BUFFER = weechat.hdata_get("buffer")
    H_LINES = weechat.hdata_get("lines")
    H_LINE = weechat.hdata_get("line")
    H_LINE_DATA = weechat.hdata_get("line_data")
    H_GUI_BUFFERS = weechat.hdata_get_list(H_BUFFER, "gui_buffers")

    load_config()

    weechat.hook_print("", "", "", 0, "on_print", "")
    weechat.hook_signal("buffer_switch", "on_buffer_switch", "")
    weechat.hook_config("plugins.var.python." + SCRIPT_NAME + ".*", "load_config", "")

    if not weechat.hook_command("url_hint", to_weechat(SCRIPT_DOC), "", "", "", "url_hint", ""):
        print_error("could not hook command /url_hint")

    if not weechat.hook_command("url_hint_replace", """Replaces {url1} with url hinted with a 1, etc. Examples:

Open url 1 in your default browser:
  /url_hint_replace /exec -bg xdg-open {url1}

Open url 1 in elinks in a new tmux window:
  /url_hint_replace /exec -bg tmux new-window elinks {url1}

Bind opening of url 1 to F1 and url 2 to F2 (press meta-k, then f1. that prints "meta2-11~"):
  /alias add open_url /url_hint_replace /exec -bg tmux new-window elinks {url$1}
  /key bind meta2-11~ /open_url 1
  /key bind meta2-12~ /open_url 2""", "<command>", "", "", "url_hint_replace", ""):
        print_error("could not hook command /url_hint_replace")

###############################################################################
###############################################################################
###############################################################################

def run_tests():
    if sys.version_info >= (3, 5):
        print("running mypy…")
        import subprocess
        if subprocess.call(["mypy", __file__], shell=True) == 0:
            print("no errors found")
    else:
        print("skipping mypy as it's not available on python version < 3.5")

    # noinspection SpellCheckingInspection
    tests = (
        "foo",
        "http://",
        "http://#",
        "http:// fail.com",
        "http://.www..foo.bar/",
        "http://url.c",
        "http://url.co1/,",
        "http://2.2.2.256/foo ",
        "http://[3210:123z::]:80/bye#",
        "www.mail-.lv",
        "www.ma.-il.lv"
        "http://squirrel",                                                 # this is valid but we don't want it anyway,
        "wut://server.com",
        "http://ser$ver.com",
        "http://ser_ver.com",
        "http://www.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijkl.com/",     # label too long
        "http://a.bcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcde.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.com",    # domain name too long

        ("http://url.co\u00a0m/,", "http://url.co"),     # non-breaking space
        ("[http://[3ffe:2a00:100:7031::1]", "http://[3ffe:2a00:100:7031::1]"),
        ("http://[1080::8:800:200C:417A]/foo)", "http://[1080::8:800:200C:417A]/foo"),
        ("http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html", "http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html"),
        ("http://[::3210]:80/hi", "http://[::3210]:80/hi"),
        ("http://[3210:123::]:80/bye#", "http://[3210:123::]:80/bye#"),
        ("http://127.0.0.1/foo ", "http://127.0.0.1/foo"),
        ("www.ma-il.lv/$_", "www.ma-il.lv/$_"),
        ("http://url.com", "http://url.com"),
        ("http://funny.url.com", "http://funny.url.com"),
        ("http://url.com.", "http://url.com"),
        ("http://url.com./", "http://url.com./"),
        ("http://url.com.:123", "http://url.com.:123"),
        ("(http://url.com)", "http://url.com"),
        ("http://foo.com/blah_blah_(wikipedia)_(again))", "http://foo.com/blah_blah_(wikipedia)_(again)"),
        ("https://hp--community.force.com/", "https://hp--community.force.com/"),
        ("http://xn-d1abbgf6aiiy.xnpai/,", "http://xn-d1abbgf6aiiy.xnpai/"),
        ("http://xn--d1abbgf6aiiy.xn--p1ai/,", "http://xn--d1abbgf6aiiy.xn--p1ai/"),
        ("https://xn----8sbfxoeboc6b7i.xn--p1ai/", "https://xn----8sbfxoeboc6b7i.xn--p1ai/"),
        ("  https://en.wikipedia.org/wiki/Bap_(food)\x01", "https://en.wikipedia.org/wiki/Bap_(food)"),
        ('"https://en.wikipedia.org/wiki/Bap_(food)"', "https://en.wikipedia.org/wiki/Bap_(food)"),
        (" http://server.com/www.server.com ", "http://server.com/www.server.com"),
        ("http://badutf8pcokay.com/%FF?%FE#%FF", "http://badutf8pcokay.com/%FF?%FE#%FF"),
        ("http://www.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.com/", "http://www.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.com/"),
        ("http://abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcde.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.com", "http://abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcde.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijk.com"),

        ("0HTTP://ПРЕЗИДЕНТ.РФ'", "HTTP://ПРЕЗИДЕНТ.РФ", "HTTP://xn--d1abbgf6aiiy.xn--p1ai"),
        ("https://моя-молитва.рф/", "https://моя-молитва.рф/", "https://xn----8sbfxoeboc6b7i.xn--p1ai/"),
        ("\x03www.猫.jp", "www.猫.jp", "www.xn--z7x.jp"),
        ("(https://ru.wikipedia.org/wiki/Мыло_(значения))", "https://ru.wikipedia.org/wiki/Мыло_(значения)", "https://ru.wikipedia.org/wiki/%D0%9C%D1%8B%D0%BB%D0%BE_(%D0%B7%D0%BD%D0%B0%D1%87%D0%B5%D0%BD%D0%B8%D1%8F)"),
        ("http://➡.ws/䨹", "http://➡.ws/䨹", "http://xn--hgi.ws/%E4%A8%B9"),
        ("http://➡.ws/♥?♥#♥'", "http://➡.ws/♥?♥#♥", "http://xn--hgi.ws/%E2%99%A5?%E2%99%A5#%E2%99%A5"),
        ("http://➡.ws/♥/pa%2Fth;par%2Fams?que%2Fry=a&b=c", "http://➡.ws/♥/pa%2Fth;par%2Fams?que%2Fry=a&b=c", "http://xn--hgi.ws/%E2%99%A5/pa%2Fth;par%2Fams?que/ry=a&b=c"),
        ("http://website.com/path/is%2fslash/!$&'()*+,;=:@/path?query=!$&'()*+,;=:@?query#fragment!$&'()*+,;=:@#fragment", "http://website.com/path/is%2fslash/!$&'()*+,;=:@/path?query=!$&'()*+,;=:@?query#fragment!$&'()*+,;=:@#fragment", "http://website.com/path/is%2Fslash/!$&'()*+,;=:@/path?query=!$&'()*+,;=:@?query#fragment!$&'()*+,;=:@%23fragment")
    )

    print("\ntesting urls…")
    errors = False
    for test in tests:
        if not isinstance(test, tuple):
            string, exact, safe = test, None, None
        elif len(test) == 2:
            string, exact, safe = test[0], test[1], test[1]
        else:
            string, exact, safe = test
        result = list(find_urls(string))
        e, s = (result[1].exact, result[1].safe) if len(result) == 3 else (None, None)
        if e != exact or s != safe:
            print("FAIL %s: %s → %s; %s → %s" % (string, exact, e, safe, s))
            errors = True
    print("ERRORS FOUND" if errors else "no errors found")

    print("\ntesting speed…")
    iterations, repeat = 1000, 10
    import timeit
    urls = [test[0] for test in tests if isinstance(test, tuple) and "abcdefghijklm" not in test[0]]
    string = " lorem ipsum dolor sit amet ".join(urls)
    time = min(timeit.repeat(stmt="list(find_urls(text))",
                             setup="from %s import find_urls; text = u'''%s''' " % (__name__, string),
                             repeat=repeat,
                             number=iterations))
    print("%d loops, best of %d: %.5fms per loop (%d urls in %d characters)" %
          (iterations, repeat, time / iterations * 1000, len(urls), len(string)))

try:
    import weechat                                  # type: ignore
except ImportError:
    run_tests()
else:
    install()
