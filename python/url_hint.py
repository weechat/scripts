# -*- coding: utf-8 -*-

# Copyright (c) 2017 oakkitten <jatjasjem@gmail.com>
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

So, this script prepends tiny digits to links, ¹ to the latest url, ² to the second latest, etc.
Also, it can put these urls in the window title, which you can grab using your OS automation, or your terminal emulator.
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

You can use command /url_hint_replace that replaces {url1}, {url2}, etc with according urls and then
executes the result. For example, the following will open url 1 in your default browser:

    /url_hint_replace /exec -bg xdg-open {url1}

or in elinks a new tmux window:

    /url_hint_replace /exec -bg tmux new-window elinks {url1}

You can bind opening of url 1 to f1 and url 2 to f2 like this, for example:

    (press meta-k, then f1. that prints `meta2-11~`)
    /alias add open_url /url_hint_replace /exec -bg tmux new-window elinks {url$1}
    /key bind meta2-11~ /open_url 1
    /key bind meta2-12~ /open_url 2

WARNING: Avoid passing urls to the shell as they can contain special characters. If you must do that, consider setting
the option safe_urls to "base64".

Configuration (plugins.var.python.url_hint.*):

    * max_lines: the maximum number of lines that contain urls to track ("10")
    * no_urls_title: title for buffers that don't contain urls ("weechat")
    * prefix: the beginning of the title when there are urls ("urls: ")
    * delimiter: what goes between the urls in the title (" ")
    * postfix: the end of the title when there are urls ("")
    * hints: comma-separated list of hints. evaluated, can contain colors ("⁰,¹,²,³,⁴,⁵,⁶,⁷,⁸,⁹")
    * update_title: whether the script should put urls into the title ("on")
    * safe_urls: whether the script will convert urls to their safe ascii equivalents. can be either "off",
      "on" for idna- & percent-encoding, or "base64" for utf-8 base64 encoding ("off")

Notes:

    * to avoid auto renaming tmux windows use :set allow-rename off
    * in PuTTyTray and possibly other clients, window titles are parsed using wrong charset (see bug #88). The option
      safe_urls must be set to non-"off" value to avoid issues

Limitations:

    * will not work with urls that have color codes inside them
    * will be somewhat useless in merged and zoomed buffers

Version history:

    0.6 (26 june 2017): renamed /url_hint to /url_hint_replace; /url_hint simply prints help now
    0.5 (22 june 2017): implemented base64 encoding of urls
    0.4 (18 june 2017): encode fewer characters for safe urls—helps with servers that don't follow the rfc
    0.3 (10 june 2017): don't fail when safe url encoding fails
    0.2 (4 june 2017): don't crash if a new buffer has the same pointer as the old one
    0.1 (30 may 2017): added an option to make safe urls
    0.0 (6 may 2017): initial release
'''

import re
from urllib import quote, unquote

SCRIPT_NAME = "url_hint"
SCRIPT_VERSION = "0.6"

# the following code constructs a simple but neat regular expression for detecting urls
# it's by no means perfect, but it will detect an url in quotes and parentheses, http iris,
# punycode, urls followed by punctuation and such

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

RE_IPV4_SEGMENT = ur"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
RE_IPV6_SEGMENT = ur"[0-9A-Fa-f]{1,4}"

RE_GOOD_ASCII_CHAR = ur"[A-Za-z0-9]"
RE_BAD_CHAR = ur"\x00-\x20\x7f-\xa0\ufff0-\uffff\s"
RE_GOOD_CHAR = ur"[^{bad}]".format(bad=RE_BAD_CHAR)
RE_GOOD_HOST_CHAR = ur"[^\x00-\x2f\x3a-\x40\x5b-\x60\x7b-\xa0\ufff0-\uffff]"
RE_GOOD_TLD_CHAR = ur"[^\x00-\x40\x5b-\x60\x7b-\xa0\ufff0-\uffff]"

RE_HOST_SEGMENT = ur"""(?:xn--(?:{good_ascii}+-)*{good_ascii}+|(?:{good_host}+-)*{good_host}+)""" \
    .format(good_ascii=RE_GOOD_ASCII_CHAR, good_host=RE_GOOD_HOST_CHAR)
RE_TLD = ur"(?:xn--{good_ascii}+|{good_tld}{{2,}})".format(good_ascii=RE_GOOD_ASCII_CHAR, good_tld=RE_GOOD_TLD_CHAR)

# language=PythonVerboseRegExp
RE_URL = ur"""
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
RE_URL = RE_URL.format(s4=RE_IPV4_SEGMENT, s6=RE_IPV6_SEGMENT,
                       bad=RE_BAD_CHAR, good=RE_GOOD_CHAR, host_segment=RE_HOST_SEGMENT, tld=RE_TLD)
RE_URL = re.compile(RE_URL, re.U | re.X | re.I)
RE_DOTS = re.compile(u"[\u002E\u3002\uFF0E\uFF61]", re.U)

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
    def __init__(self, match):
        self._match = match

    @lazy
    def exact(self):
        return self._match.group(0)

    @lazy
    def safe(self):
        prefix, userinfo, ip_or_host, c_port, rest = self._match.groups()
        safe = prefix.encode("ascii")
        if userinfo: safe += q(userinfo, safe=SAFE_USERINFO) + "@"
        try: safe += ip_or_host.encode("idna")
        except UnicodeError: safe += ".".join(safe_label(label) for label in RE_DOTS.split(ip_or_host))
        if c_port: safe += c_port.encode("ascii")
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
    def base64(self):
        return self.exact.encode("utf-8").encode("base64")

    @property
    def url(self):
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
# quote() takes the rest of unreserved characters by itself, so we only need to adjust it for the rest

SUB_DELIMS = "!$&'()*+,;="
SAFE_USERINFO = SUB_DELIMS + ":"
SAFE_PATH = SUB_DELIMS + ":@"
SAFE_FRAGMENT = SAFE_QUERY = SUB_DELIMS + ":@" + "/?"

def q(uni, safe):
    return quote(unquote(uni.encode("utf-8")), safe=safe)

SAFE_HOST_LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ-abcdefghijklmnopqrstuvwxyz.1234567890")
def safe_label(label):
    return label.encode("utf-8") if set(label).issubset(SAFE_HOST_LETTERS) else "xn--" + label.lower().encode("punycode")

def find_urls(string):
    last_end = 0
    for match in RE_URL.finditer(string):
        start, end = match.span()
        yield string[last_end:start]
        yield Url(match)
        last_end = end
    yield string[last_end:]

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
    def __init__(self, pointer, message, parts):
        assert pointer
        self.pointer = pointer
        self.urls = parts[-2::-2]
        self._data = weechat.hdata_pointer(H_LINE, pointer, "data")
        self._original_message = message
        self._current_message = message
        self._parts = [part.exact if isinstance(part, Url) else part for part in parts]
        for i in range(1, len(self._parts) * 3 / 2, 3):
            self._parts.insert(i, None)

    def is_of_pointer(self, pointer):
        return self.pointer == pointer and self._data == weechat.hdata_pointer(H_LINE, pointer, "data") and \
               self._current_message == weechat.hdata_string(H_LINE_DATA, self._data, 'message').decode("utf-8")

    def redraw(self, index):
        self._parts[1::3] = (get_hint(i) for i in reversed(xrange(index, index + len(self.urls))))
        self._set_message("".join(self._parts))

    def reset(self):
        self._set_message(self._original_message)

    def _set_message(self, message):
        self._current_message = message
        weechat.hdata_update(H_LINE_DATA, self._data, {"message": message.encode("utf-8")})

def get_hint(i):
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

    on_message(displayed): *must* be called on every message on a buffer
    valid(): returns True if this buffer still exists in weechat and is safe to operate on
    redraw(full_reset): redraw all lines. if full_reset is True, restores all lines to their original conditions
    """
    def __init__(self, pointer):
        assert pointer
        self.pointer = pointer
        self.urls = []
        self._lines = []                        # reverse order

    def on_message(self, message, displayed):
        if not displayed:
            return
        message = message.decode("utf-8")
        parts = list(find_urls(message))        # parts = ["text", url, "text", url, ""]
        if len(parts) < 3:
            return
        line = Line(self.get_last_line_pointer(), message, parts)
        self._lines.insert(0, line)
        self.redraw(last_pointer=line.pointer)

    def redraw(self, last_pointer=None, full_reset=False):
        if last_pointer is None:
            last_pointer = self.get_last_line_pointer()

        max_lines = 0 if full_reset else C[MAX_LINES]
        lines, urls = [], []
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
    def get_last_line_pointer(self):
        try:
            assert weechat.hdata_check_pointer(H_BUFFER, HL_GUI_BUFFERS, self.pointer)
            own_lines = weechat.hdata_pointer(H_BUFFER, self.pointer, "own_lines"); assert own_lines
            last_line = weechat.hdata_pointer(H_LINES, own_lines, "last_line"); assert last_line
        except AssertionError:
            return None
        return last_line

def line_reverse_walker(pointer):
    while pointer:
        yield pointer
        pointer = weechat.hdata_move(H_LINE, pointer, -1)

###############################################################################
###############################################################################
###############################################################################

buffers = type("", (dict,), {"__missing__": lambda self, p: self.setdefault(p, Buffer(p))})()
current_buffer = ""

# noinspection PyUnusedLocal
def on_print(data, pointer, date, tags, displayed, highlighted, prefix, message):
    displayed = int(displayed)          # https://weechat.org/files/doc/devel/weechat_plugin_api.en.html#_hook_print
    buffers[pointer].on_message(message, displayed)
    if displayed and C[UPDATE_TITLE] and current_buffer == pointer:
        update_title()
    return weechat.WEECHAT_RC_OK

# noinspection PyUnusedLocal
def on_buffer_switch(data, signal, pointer):
    global current_buffer
    if C[UPDATE_TITLE] and current_buffer != pointer:
        current_buffer = pointer
        update_title()
    return weechat.WEECHAT_RC_OK

def update_title():
    if not current_buffer: return
    urls = buffers[current_buffer].urls
    title = (C[PREFIX] + C[DELIMITER].join(url.url for url in urls) + C[POSTFIX]) if urls else C[NO_URLS_TITLE]
    weechat.window_set_title(title.encode("utf-8"))

RE_REP = re.compile(r"{url(\d+)}", re.I)

# simply print help
# noinspection PyUnusedLocal
def url_hint(data, pointer, command):
    weechat.prnt("", __doc__.strip())
    return weechat.WEECHAT_RC_OK

# noinspection PyUnusedLocal
def url_hint_replace(data, pointer, command):
    urls = buffers[pointer].urls
    def get_url(match):
        try: return urls[int(match.group(1)) - 1].url
        except IndexError: raise IndexError("could not replace " + match.group(0))
    try: weechat.command(pointer, RE_REP.sub(get_url, command.decode("utf-8")).encode("utf-8"))
    except IndexError as e: print_error(e.message)
    return weechat.WEECHAT_RC_OK

def print_error(text):
    weechat.prnt("", "%s%s: %s" % (weechat.prefix("error"), SCRIPT_NAME, text))

def redraw_everything(full_reset):
    for pointer, buffer in buffers.items():
        buffer.redraw(full_reset=full_reset)
    update_title()
    return weechat.WEECHAT_RC_OK

def exit_function():
    return redraw_everything(full_reset=True)

###############################################################################
###############################################################################
###############################################################################

def hints_from_string(x):
    hints = weechat.string_eval_expression(x.encode("utf-8"), "", "", "").decode("utf-8").split(",")
    return None if len(hints) < 2 or any(not hint.strip() for hint in hints) else hints

def boolean_from_string(x):
    return {"on": True, "off": False}.get(x.lower(), None)

def safe_from_string(x):
    return {"off": "exact", "on": "safe", "base64": "base64"}[x.lower()] if x.lower() in ("on", "off", "base64") else None

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
    HINTS: (u"⁰,¹,²,³,⁴,⁵,⁶,⁷,⁸,⁹", "comma-separated list of hints. evaluated, can contain colors", hints_from_string),
    UPDATE_TITLE: ("on", "whether the script should put urls into the title", boolean_from_string),
    SAFE: ("off", """whether the script will convert urls to their safe ascii equivalents. can be either "off", "on" for idna- & percent-encoding, or "base64" for utf-8 base64 encoding""", safe_from_string)
}

C = {}

def load_config(*_):
    for name, (default, description, from_string) in DEFAULT_CONFIG.iteritems():
        value = None
        if weechat.config_is_set_plugin(name):
            value = weechat.config_get_plugin(name).decode("utf-8")
            if from_string: value = from_string(value)
        if value is None:
            value = from_string(default) if from_string else default
            weechat.config_set_plugin(name, default.encode("utf-8"))
            weechat.config_set_desc_plugin(name, ('%s (default: "%s")' % (description, default)).encode("utf-8"))
        C[name] = value
    redraw_everything(full_reset=False)
    return weechat.WEECHAT_RC_OK

###############################################################################
###############################################################################
###############################################################################

try:
    # noinspection PyUnresolvedReferences
    import weechat
except ImportError:
    # noinspection SpellCheckingInspection
    TESTS = (
        u"foo",
        u"http://",
        u"http://#",
        u"http:// fail.com",
        u"http://xm--we.co",
        u"http://.www..foo.bar/",
        u"http://url.c",
        u"http://url.co1/,",
        u"http://2.2.2.256/foo ",
        u"http://[3210:123z::]:80/bye#",
        u"www.mail-.lv",
        u"http://squirrel",                                                 # this is valid but we don't want it anyway,
        u"wut://server.com",
        u"http://ser$ver.com",
        u"http://ser_ver.com",

        (u"http://url.co\u00a0m/,", u"http://url.co", "http://url.co"),     # non-breaking space
        (u"[http://[3ffe:2a00:100:7031::1]", u"http://[3ffe:2a00:100:7031::1]", "http://[3ffe:2a00:100:7031::1]"),
        (u"http://[1080::8:800:200C:417A]/foo)", u"http://[1080::8:800:200C:417A]/foo", "http://[1080::8:800:200C:417A]/foo"),
        (u"http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html", u"http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html", "http://[FEDC:BA98:7654:3210:FEDC:BA98:7654:3210]:80/index.html"),
        (u"http://[::3210]:80/hi", u"http://[::3210]:80/hi", "http://[::3210]:80/hi"),
        (u"http://[3210:123::]:80/bye#", u"http://[3210:123::]:80/bye#", "http://[3210:123::]:80/bye#"),
        (u"http://127.0.0.1/foo ", u"http://127.0.0.1/foo", "http://127.0.0.1/foo"),
        (u"www.ma-il.lv/$_", u"www.ma-il.lv/$_", "www.ma-il.lv/$_"),
        (u"http://url.com", u"http://url.com", "http://url.com"),
        (u"(http://url.com)", u"http://url.com", "http://url.com"),
        (u"0HTTP://ПРЕЗИДЕНТ.РФ'", u"HTTP://ПРЕЗИДЕНТ.РФ", "HTTP://xn--d1abbgf6aiiy.xn--p1ai"),
        (u"http://xn-d1abbgf6aiiy.xnpai/,", u"http://xn-d1abbgf6aiiy.xnpai/", "http://xn-d1abbgf6aiiy.xnpai/"),
        (u"http://xn--d1abbgf6aiiy.xn--p1ai/,", u"http://xn--d1abbgf6aiiy.xn--p1ai/", "http://xn--d1abbgf6aiiy.xn--p1ai/"),
        (u"  https://en.wikipedia.org/wiki/Bap_(food)\x01", u"https://en.wikipedia.org/wiki/Bap_(food)", "https://en.wikipedia.org/wiki/Bap_(food)"),
        (u"\x03www.猫.jp", u"www.猫.jp", "www.xn--z7x.jp"),
        (u'"https://en.wikipedia.org/wiki/Bap_(food)"', u"https://en.wikipedia.org/wiki/Bap_(food)", "https://en.wikipedia.org/wiki/Bap_(food)"),
        (u"(https://ru.wikipedia.org/wiki/Мыло_(значения))", u"https://ru.wikipedia.org/wiki/Мыло_(значения)", "https://ru.wikipedia.org/wiki/%D0%9C%D1%8B%D0%BB%D0%BE_(%D0%B7%D0%BD%D0%B0%D1%87%D0%B5%D0%BD%D0%B8%D1%8F)"),
        (u"http://foo.com/blah_blah_(wikipedia)_(again))", u"http://foo.com/blah_blah_(wikipedia)_(again)", "http://foo.com/blah_blah_(wikipedia)_(again)"),
        (u"http://➡.ws/䨹", u"http://➡.ws/䨹", "http://xn--hgi.ws/%E4%A8%B9"),
        (u" http://server.com/www.server.com ", u"http://server.com/www.server.com", "http://server.com/www.server.com"),
        (u"http://➡.ws/♥?♥#♥'", u"http://➡.ws/♥?♥#♥", "http://xn--hgi.ws/%E2%99%A5?%E2%99%A5#%E2%99%A5"),
        (u"http://➡.ws/♥/pa%2Fth;par%2Fams?que%2Fry=a&b=c", u"http://➡.ws/♥/pa%2Fth;par%2Fams?que%2Fry=a&b=c", "http://xn--hgi.ws/%E2%99%A5/pa%2Fth;par%2Fams?que/ry=a&b=c"),
        (u"http://badutf8pcokay.com/%FF?%FE#%FF", u"http://badutf8pcokay.com/%FF?%FE#%FF", "http://badutf8pcokay.com/%FF?%FE#%FF"),
        (u"http://website.com/path/is%2fslash/!$&'()*+,;=:@/path?query=!$&'()*+,;=:@?query#fragment!$&'()*+,;=:@#fragment", u"http://website.com/path/is%2fslash/!$&'()*+,;=:@/path?query=!$&'()*+,;=:@?query#fragment!$&'()*+,;=:@#fragment", "http://website.com/path/is%2Fslash/!$&'()*+,;=:@/path?query=!$&'()*+,;=:@?query#fragment!$&'()*+,;=:@%23fragment")
    )
    ITERATIONS = 10000

    print "testing the urls…\n"
    for test in TESTS:
        string, exact, safe = test if isinstance(test, tuple) else (test, None, None)
        result = list(find_urls(string))
        e, s = (result[1].exact, result[1].safe) if len(result) == 3 else (None, None)
        if e == exact and s == safe: print u"OK `%s`: `%s`; `%s`" % (string, exact, safe)
        else: print u"FAIL `%s`: `%s` → `%s`; `%s` → `%s`" % (string, exact, e, safe, s)

    print "\ntesting speed…\n"
    from timeit import Timer
    urls = [test[0] for test in TESTS if isinstance(test, tuple)]
    string = " lorem ipsum dolor sit amet ".join(urls)
    time = Timer("list(find_urls(string))", "import re; from __main__ import find_urls, string").timeit(ITERATIONS)
    print "%s lookups on a %s character long string with %s urls took %s seconds (%s seconds per iteration)" % \
          (ITERATIONS, len(string), len(urls), time, time/ITERATIONS)
else:
    if not weechat.register(SCRIPT_NAME, "oakkitten", SCRIPT_VERSION, "MIT", "Display hints for urls and open them with keyboard shortcuts", "exit_function", ""):
        raise Exception("Could not register script")

    WEECHAT_VERSION = int(weechat.info_get('version_number', '') or 0)
    if WEECHAT_VERSION <= 0x00040000:
        raise Exception("Need Weechat 0.4 or higher")

    H_BUFFER = weechat.hdata_get("buffer")
    H_LINES = weechat.hdata_get("lines")
    H_LINE = weechat.hdata_get("line")
    H_LINE_DATA = weechat.hdata_get("line_data")
    HL_GUI_BUFFERS = weechat.hdata_get_list(H_BUFFER, "gui_buffers")

    load_config()

    weechat.hook_print("", "", "", 0, "on_print", "")
    weechat.hook_signal("buffer_switch", "on_buffer_switch", "")
    weechat.hook_config("plugins.var.python." + SCRIPT_NAME + ".*", "load_config", "")

    if not weechat.hook_command("url_hint", __doc__.strip(), "", "", "", "url_hint", ""):
        print_error("could not hook command /url_hint")

    if not weechat.hook_command("url_hint_replace", """Replaces {url1} with url hinted with a 1, etc. Example usage:

Open url 1 in your default browser:

  /url_hint_replace /exec -bg xdg-open {url1}

Open url 1 in elinks in a new tmux window:

  /url_hint_replace /exec -bg tmux new-window elinks {url1}

Bind opening of url 1 to F1 and url 2 to F2:

  (press meta-k, then f1. that prints "meta2-11~")
  /alias add open_url /url_hint_replace /exec -bg tmux new-window elinks {url$1}
  /key bind meta2-11~ /open_url 1
  /key bind meta2-12~ /open_url 2""", "<command>", "", "", "url_hint_replace", ""):
        print_error("could not hook command /url_hint_replace")
