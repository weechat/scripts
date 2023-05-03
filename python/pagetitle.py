# pagetitle plugin for weechat-0.3.0
#
#  /pagetitle http://tech.slashdot.org/tech/08/11/12/199215.shtml
#  <user> http://tech.slashdot.org/tech/08/11/12/199215.shtml
#  ('Slashdot | Microsoft's "Dead Cow" Patch Was 7 Years In the Making')
#
# xororand @ irc://irc.freenode.net/#weechat
#
# 2021-06-05, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.6: make script compatible with Python 3,
#                  rename command /pt to /pagetitle, fix PEP8 errors
# 2009-05-02, Sébastien Helleu <flashcode@flashtux.org>:
#     version 0.5: sync with last API changes

from html import unescape
from urllib.error import URLError
from urllib.request import Request, urlopen

import re
import weechat

MAX_TITLE_LENGTH = 100

regex_url = re.compile("""https?://[^ ]+""")


def get_page_title(url):
    """Retrieve the HTML <title> from a webpage."""
    req = Request(
        url,
        headers={
            "User-agent": "Mozilla/5.0 (weechat/pagetitle)",
        },
    )
    try:
        head = urlopen(req).read(8192).decode("utf-8", errors="ignore")
    except URLError:
        return ""
    match = re.search("(?i)<title>(.*?)</title>", head)
    return unescape(match.group(1)) if match else ""


def add_page_titles(data):
    """Add page titles for all URLs of a message."""
    buffer, msg = data.split(";", 1)

    def url_replace(match):
        url = match.group()
        title = get_page_title(url)
        if len(title) > MAX_TITLE_LENGTH:
            title = "%s [...]" % title[0:MAX_TITLE_LENGTH]
        url = "%s ('%s')" % (url, title)
        return url

    msg = regex_url.sub(url_replace, msg)
    return f"{buffer};{msg}"


def process_cb(data, command, rc, stdout, stderr):
    """Process callback."""
    buffer, msg = stdout.split(";", 1)
    weechat.command(buffer, "/say %s" % msg)
    return weechat.WEECHAT_RC_OK


# /pagetitle http://foo
def cmd_pagetitle_cb(data, buffer, args):
    if len(args) == 0:
        return weechat.WEECHAT_RC_ERROR
    weechat.hook_process(
        "func:add_page_titles",
        30 * 1000,
        "process_cb",
        f"{buffer};{args}",
    )
    return weechat.WEECHAT_RC_OK


weechat.register(
    "pagetitle",
    "xororand",
    "0.6",
    "GPL3",
    """Adds HTML titles to http:// urls in your message.""",
    "",
    "",
)
desc = """\
Sends a message to the current buffer and adds HTML titles to http:// URLs.
Example: /pagetitle check this out: http://xkcd.com/364/
<you> check this out: http://xkcd.com/364/ (xkcd - A webcomic of romance, \
sarcasm, math and language)"""
weechat.hook_command(
    "pagetitle",
    desc,
    "message",
    "message with URL(s)",
    "",
    "cmd_pagetitle_cb",
    "",
)

# vim:set ts=4 sw=4 noexpandtab nowrap foldmethod=marker:
