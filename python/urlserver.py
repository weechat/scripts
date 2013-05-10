# -*- coding: utf-8 -*-
#
# Copyright (C) 2011-2013 Sebastien Helleu <flashcode@flashtux.org>
# Copyright (C) 2011 xt <xt@bash.no>
# Copyright (C) 2012 Filip H.F. "FiXato" Slagter <fixato+weechat+urlserver@gmail.com>
# Copyright (C) 2012 WillyKaze <willykaze@willykaze.org>
# Copyright (C) 2013 Thomas Kindler <mail_weechat@t-kindler.de>
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
# Shorten URLs with own HTTP server.
# (this script requires Python >= 2.6)
#
# How does it work?
#
# 1. The URLs displayed in buffers are shortened and stored in memory (saved in
#    a file when script is unloaded).
# 2. URLs shortened can be displayed below messages, in a dedicated buffer, or
#    as HTML page in your browser.
# 3. This script embeds an HTTP server, which will redirect shortened URLs
#    to real URL and display list of all URLs if you browse address without URL key.
# 4. It is recommended to customize/protect the HTTP server using script options
#    (see /help urlserver)
#
# Example after message:
#
#   FlashCode | look at this: http://test.server.com/this-is-a-long-url
#             | [ http://myhost.org:1234/8aK ]
#
# Example inside message:
#
#   FlashCode | look at this: http://test.server.com/this-is-a-long-url [ http://myhost.org:1234/8aK ]
#
# List of URLs:
# - in WeeChat: /urlserver
# - in browser: http://myhost.org:1234/
#
# History:
#
# 2013-05-04, Thomas Kindler <mail_weechat@t-kindler.de>
#     version 1.2: added a "http_scheme_display" option. This makes it possible to run
#                  the server behind a reverse proxy with https:// URLs.
# 2013-03-25, Hermit (@irc.freenode.net):
#     version 1.1: made links relative in the html, so that they can be followed when accessing
#                  the listing remotely using the weechat box's IP directly.
# 2012-12-12, WillyKaze <willykaze@willykaze.org>:
#     version 1.0: add options "http_time_format", "display_msg_in_url" (works with relay/irc),
#                  "color_in_msg", "separators"
# 2012-04-18, Filip H.F. "FiXato" Slagter <fixato+weechat+urlserver@gmail.com>:
#     version 0.9: add options "http_autostart", "http_port_display"
#                  "url_min_length" can now be set to -1 to auto-detect minimal url length
#                  Also, if port is 80 now, :80 will no longer be added to the shortened url.
# 2012-04-17, Filip H.F. "FiXato" Slagter <fixato+weechat+urlserver@gmail.com>:
#     version 0.8: add more CSS support by adding options "http_fg_color", "http_css_url",
#                  and "http_title", add descriptive classes to most html elements.
#                  See https://raw.github.com/FiXato/weechat_scripts/master/urlserver/sample.css
#                  for a sample css file that can be used for http_css_url
# 2012-04-11, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7: fix truncated HTML page (thanks to xt), fix base64 decoding with Python 3.x
# 2012-01-19, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.6: add option "http_hostname_display"
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.5: make script compatible with Python 3.x
# 2011-10-31, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: add options "http_embed_youtube_size" and "http_bg_color",
#                  add extensions jpeg/bmp/svg for embedded images
# 2011-10-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: escape HTML chars for page with list of URLs, add option
#                  "http_prefix_suffix", disable highlights on urlserver buffer
# 2011-10-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: fix error on loading of file "urlserver_list.txt" when it is empty
# 2011-10-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
#

SCRIPT_NAME    = 'urlserver'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '1.2'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Shorten URLs with own HTTP server'

SCRIPT_COMMAND = 'urlserver'
SCRIPT_BUFFER  = 'urlserver'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

try:
    import sys, os, string, ast, datetime, socket, re, base64, cgi
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

# regex are from urlbar.py, written by xt
url_octet = r'(?:2(?:[0-4]\d|5[0-5])|1\d\d|\d{1,2})'
url_ipaddr = r'%s(?:\.%s){3}' % (url_octet, url_octet)
url_label = r'[0-9a-z][-0-9a-z]*[0-9a-z]?'
url_domain = r'%s(?:\.%s)*\.[a-z][-0-9a-z]*[a-z]?' % (url_label, url_label)

urlserver = {
    'socket'        : None,
    'hook_fd'       : None,
    'regex'         : re.compile(r'(\w+://(?:%s|%s)(?::\d+)?(?:/[^\])>\s]*)?)' % (url_domain, url_ipaddr), re.IGNORECASE),
    'urls'          : {},
    'number'        : 0,
    'buffer'        : '',
}

# script options
urlserver_settings_default = {
    # HTTP server settings
    'http_autostart'     : ('on', 'start the built-in HTTP server automatically)'),
    'http_scheme_display': ('http', 'display this scheme in shortened URLs'),
    'http_hostname'      : ('', 'force hostname/IP in bind of socket (empty value = auto-detect current hostname)'),
    'http_hostname_display': ('', 'display this hostname in shortened URLs'),
    'http_port'          : ('', 'force port for listening (empty value = find a random free port)'),
    'http_port_display'  : ('', 'display this port in shortened URLs. Useful if you forward a different external port to the internal port'),
    'http_allowed_ips'   : ('', 'regex for IPs allowed to use server (example: "^(123.45.67.89|192.160.*)$")'),
    'http_auth'          : ('', 'login and password (format: "login:password") required to access to page with list of URLs'),
    'http_url_prefix'    : ('', 'prefix to add in URLs to prevent external people to scan your URLs (for example: prefix "xx" will give URL: http://host.com:1234/xx/8)'),
    'http_bg_color'      : ('#f4f4f4', 'background color for HTML page'),
    'http_fg_color'      : ('#000', 'foreground color for HTML page'),
    'http_css_url'       : ('', 'URL of external Cascading Style Sheet to add (BE CAREFUL: the HTTP referer will be sent to site hosting CSS file!) (empty value = use default embedded CSS)'),
    'http_embed_image'   : ('off', 'embed images in HTML page (BE CAREFUL: the HTTP referer will be sent to site hosting image!)'),
    'http_embed_youtube' : ('off', 'embed youtube videos in HTML page (BE CAREFUL: the HTTP referer will be sent to youtube!)'),
    'http_embed_youtube_size': ('480*350', 'size for embedded youtube video, format is "xxx*yyy"'),
    'http_prefix_suffix' : (' ', 'suffix displayed between prefix and message in HTML page'),
    'http_title'         : ('WeeChat URLs', 'title of the HTML page'),
    'http_time_format'   : ('%d/%m/%y %H:%M:%S', 'time format in the HTML page'),
    # message filter settings
    'msg_ignore_buffers' : ('core.weechat,python.grep', 'comma-separated list (without spaces) of buffers to ignore (full name like "irc.freenode.#weechat")'),
    'msg_ignore_tags'    : ('irc_quit,irc_part,notify_none', 'comma-separated list (without spaces) of tags (or beginning of tags) to ignore (for example, use "notify_none" to ignore self messages or "nick_weebot" to ignore messages from nick "weebot")'),
    'msg_require_tags'   : ('nick_', 'comma-separated list (without spaces) of tags (or beginning of tags) required to shorten URLs (for example "nick_" to shorten URLs only in messages from other users)'),
    'msg_ignore_regex'   : ('', 'ignore messages matching this regex'),
    'msg_ignore_dup_urls': ('off', 'ignore duplicated URLs (do not add an URL in list if it is already)'),
    # display settings
    'color'              : ('darkgray', 'color for urls displayed after message'),
    'color_in_msg'       : ('', 'color for urls displayed inside irc message: it is a number (irc color) between 00 and 15 (see doc for a list of irc colors)'),
    'separators'         : ('[|]', 'separators for short url list (string with exactly 3 chars)'),
    'display_urls'       : ('on', 'display URLs below messages'),
    'display_urls_in_msg': ('off', 'add shorten url next to the original url (only in IRC messages) (useful for urlserver behind relay/irc)'),
    'url_min_length'     : ('0', 'minimum length for an URL to be shortened (0 = shorten all URLs, -1 = detect length based on shorten URL)'),
    'urls_amount'        : ('100', 'number of URLs to keep in memory (and in file when script is not loaded)'),
    'buffer_short_name'  : ('off', 'use buffer short name on dedicated buffer'),
    'debug'              : ('off', 'print some debug messages'),
}
urlserver_settings = {}


def base62_encode(number):
    """Encode a number in base62 (all digits + a-z + A-Z)."""
    base62chars = string.digits + string.ascii_letters
    l = []
    while number > 0:
        remainder = number % 62
        number = number // 62
        l.insert(0, base62chars[remainder])
    return ''.join(l) or '0'

def base62_decode(str_value):
    """Decode a base62 string (all digits + a-z + A-Z) to a number."""
    base62chars = string.digits + string.ascii_letters
    return sum([base62chars.index(char) * (62 ** (len(str_value) - index - 1)) for index, char in enumerate(str_value)])

def base64_decode(s):
    if sys.version_info >= (3,):
        # python 3.x
        return base64.b64decode(s.encode('utf-8'))
    else:
        # python 2.x
        return base64.b64decode(s)

def urlserver_get_hostname(full=True):
    """Return hostname with port number if != default port for the protocol."""
    global urlserver_settings

    scheme = urlserver_settings['http_scheme_display']
    hostname = urlserver_settings['http_hostname_display'] or urlserver_settings['http_hostname'] or socket.getfqdn()

    # If the built-in HTTP server isn't running, default to port from settings
    port = urlserver_settings['http_port']
    if len(urlserver_settings['http_port_display']) > 0:
        port = urlserver_settings['http_port_display']
    elif urlserver['socket']:
        port = urlserver['socket'].getsockname()[1]

    # Don't add :port if the port matches the default port for the protocol
    prefixed_port = ':%s' % port

    if scheme == "http" and prefixed_port == ':80':
        prefixed_port = ''
    elif scheme == "https" and prefixed_port == ':443':
        prefixed_port = ''

    prefix = ''
    if urlserver_settings['http_url_prefix']:
        prefix = '%s/' % urlserver_settings['http_url_prefix']

    if full:
        return '%s://%s%s/%s' % (scheme, hostname, prefixed_port, prefix)
    else:
        return '/%s' % prefix

def urlserver_short_url(number, full=True):
    """Return short URL with number."""
    return '%s%s' % (urlserver_get_hostname(full), base62_encode(number))

def urlserver_server_reply(conn, code, extra_header, message, mimetype='text/html'):
    """Send a HTTP reply to client."""
    global urlserver_settings
    if extra_header:
        extra_header += '\r\n'
    s = 'HTTP/1.1 %s\r\n' \
        '%s' \
        'Content-Type: %s\r\n' \
        'Content-Length: %d\r\n' \
        '\r\n' \
        % (code, extra_header, mimetype, len(message))
    msg = None
    if sys.version_info >= (3,):
        # python 3.x
        if type(message) is bytes:
            msg = s.encode('utf-8') + message
        else:
            msg = s.encode('utf-8') + message.encode('utf-8')
    else:
        # python 2.x
        msg = s + message
    if urlserver_settings['debug'] == 'on':
        weechat.prnt('', 'urlserver: sending %d bytes' % len(msg))
    conn.sendall(msg)

def urlserver_server_favicon():
    """Return favicon for HTML page."""
    s = 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH1wgcDwo4MOEy+AAAAB10' \
        'RVh0Q29tbWVudABDcmVhdGVkIHdpdGggVGhlIEdJTVDvZCVuAAADp0lEQVQ4y12TXUxbBRTH/733ttx+XFq+Ci2Ur8AEYSBIosnS+YJhauJY9mQyXfTBh8UEnclm1Gxq' \
        'YoJGfZkzqAkmQ2IicVOcwY1YyMZwWcfXVq2Ulpax3raX2y9ob29v7+31QViIJzkPJyfn//D7/48G+2r+6jzaO9oHFCjPCTkBM7MzF06eOhng/uHMFE2dUopKExthb3cf' \
        '6h4DUAAAar+A3WB/b21l7a3pW9NLPW099Vk+axn9aPRDkROvX3FdiRtpo9LX0XeMJMm/FUW5DQDE3vHSN0t9vhXfy+eGz00hjgk6TZfcWXajlq79ePLyZGLog6Gvm7XN' \
        'nPumO+50HnYAIB8J+P3cMzmL+oVAy1ZdRhdykA4bp6YT5z/79PjaVtDJ+ThxeHCYSOUzWn17eebs2fMvAWgBoCEAIBTiS1cDG81b8azZz/rrT4+f/qWm92D2wUY6H91O' \
        'VfFhvnFkZiQRKRWnNzfj4fn5RSOA0kcM4nwhHRckQRLFwoBx4Ljd3pD3eoKNNkeDoaDTSzIvM2cqz7zLJKsVylphG//ynd8B8ABUCgC8Xn+oxt5W7V2aS99JuANP9th6' \
        '9RtsUlbNjNZkk+5tTwRjmXisK1t5gJR1qsfjDu4K/Mdg7PtPuFSKzEWS6Xi6QTdlau9ZD4Y22EgkI7KxVEZqrVgwveC8nJX08vLKQhSAB4CAPZLJZLjY2fnqYCLBV6ga' \
        'ISuROdP9xRthhnkMeVGtIQijXGo+0JTZEYzXrg8vdB0u8/Yeakj57sWEPRvVCLuzIgg0XdW3fSySdHX4A7N3+a3sH2LOQlNka1ssmmwKP2T1BJkKOJ5ST/hXN50ACAIA' \
        'Pv+2W0+UT2WFrNFkLsmVRP0PxaefNehl5b5nZ8di0OjUGp3d5eCE0fX+18nauh7u+a4jhVcAmKnvrtnrWTY6bKwcrxILUtHe5CVaWtPKE/3ki8s3Lk1aLIiq8NrrD/os' \
        'ZfZIvdVBqWSKkoNzSgYAQ5gZ4bXNQNw0cZF/P8r6fq4zJ9ORkDTXXCdrkNZo+49eon8d41apbYGjZTVlJSmfSdKE3a7cVwBYqopWDEecupYTg+TQny53uK6qkPL8Jcw+' \
        '3sh0LjbL1jZbkbwwEtgmCW2C47X5GhOhXw9oWABhADL12w/qxSIpEz/9mI9JucIsw6hzxaK6tBMyVE9dTWbKrMqb01OoUyXdrQfhAvP2G3S5y1W4CyC5/xF1u63Zy0Z1' \
        'mZ7ejSv5v50OQMnujH8BbzDFpcdRAIIAAAAASUVORK5CYII='
    return base64_decode(s)

def urlserver_server_reply_list(conn, sort='-time'):
    """Send list of URLs as HTML page to client."""
    global urlserver, urlserver_settings
    content = '<div class="urls">\n<table id="urls_table">\n'
    if not sort.startswith('-'):
        sort = '+%s' % sort
    if sort[1:] == 'time':
        urls = sorted(urlserver['urls'].items())
    else:
        idx = ['time', 'nick', 'buffer'].index(sort[1:])
        urls = sorted(urlserver['urls'].items(), key=lambda url: url[1][idx].lower())
    if sort.startswith('-'):
        urls.reverse()
    sortkey = { '-': ('', '&uarr;'), '+': ('-', '&darr;') }
    prefix = ''
    if urlserver_settings['http_url_prefix']:
        prefix = '%s/' % urlserver_settings['http_url_prefix']
    content += '  <tr>'
    for column, defaultsort in (('time', '-'), ('nick', ''), ('buffer', '')):
        if sort[1:] == column:
            content += '<th class="sortable sorted_by %s_header"><a href="/%ssort=%s%s">%s</a> %s</th>' % (column, prefix, sortkey[sort[0]][0], column, column.capitalize(), sortkey[sort[0]][1])
        else:
            content += '<th class="sortable %s_header"><a class="sort_link" href="/%ssort=%s%s">%s</a></th>' % (column, prefix, defaultsort, column, column.capitalize())
    content += '<th class="unsortable message_header">URLs</th>'
    content += '</tr>\n'
    for key, item in urls:
        content += '  <tr>'
        url = item[3]
        obj = ''
        message = cgi.escape(item[4].replace(url, '\x01\x02\x03\x04')).split('\t', 1)
        message[0] = '<span class="prefix">%s</span>' % message[0]
        message[1] = '<span class="message">%s</span>' % message[1]

        strjoin = '<span class="prefix_suffix"> %s </span>' % urlserver_settings['http_prefix_suffix'].replace(' ', '&nbsp;')
        message = strjoin.join(message).replace('\x01\x02\x03\x04', '</span><a class="url" href="%s" title="%s">%s</a><span class="message">' % (urlserver_short_url(key, False), url, url))
        if urlserver_settings['http_embed_image'] == 'on' and url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg')):
            obj = '<div class="obj"><img src="%s" title="%s" alt="%s"></div>' % (url, url, url)
        elif urlserver_settings['http_embed_youtube'] == 'on' and 'youtube.com/' in url:
            m = re.search('v=([\w\d]+)', url)
            if m:
                yid = m.group(1)
                try:
                    size = urlserver_settings['http_embed_youtube_size'].split('*')
                    width = int(size[0])
                    height = int(size[1])
                except:
                    width = 480
                    height = 350
                obj = '<div class="obj youtube"><iframe id="%s" type="text/html" width="%d" height="%d" ' \
                    'src="http://www.youtube.com/embed/%s?enablejsapi=1"></iframe></div>' % (yid, width, height, yid)
        content += '<td class="timestamp">%s</td><td class="nick">%s</td><td class="buffer">%s</td><td class="message">' % (item[0], item[1], item[2])
        content += '%s%s</td></tr>\n' % (message, obj)
    content += '</table>'
    if len(urlserver_settings['http_css_url']) > 0:
        css = '<link rel="stylesheet" type="text/css" href="%s" />' % urlserver_settings['http_css_url']
    else:
        css = '<style type="text/css" media="screen">' \
            '<!--\n' \
            '  html { font-family: Verdana, Arial, Helvetica; font-size: 12px; background: %s; color: %s }\n' \
            '  .urls table { border-collapse: collapse }\n' \
            '  .urls table td,th { border: solid 1px #cccccc; padding: 4px; font-size: 12px }\n' \
            '  .timestamp,.nick,.buffer { white-space: nowrap }\n' \
            '  .sorted_by { font-style: italic; }\n' \
            '  .obj { margin-top: 1em }\n' \
            '-->' \
            '</style>\n' % (urlserver_settings['http_bg_color'], urlserver_settings['http_fg_color'])

    html = '<html>\n' \
        '<head>\n' \
        '<title>%s</title>\n' \
        '<meta http-equiv="content-type" content="text/html; charset=utf-8" />\n' \
        '%s\n' \
        '</head>\n' \
        '<body>\n%s\n</body>\n' \
        '</html>' % (urlserver_settings['http_title'], css, content)
    urlserver_server_reply(conn, '200 OK', '', html)

def urlserver_server_fd_cb(data, fd):
    """Callback for server socket."""
    global urlserver, urlserver_settings
    if not urlserver['socket']:
        return weechat.WEECHAT_RC_OK
    conn, addr = urlserver['socket'].accept()
    if urlserver_settings['debug'] == 'on':
        weechat.prnt('', 'urlserver: connection from %s' % str(addr))
    if urlserver_settings['http_allowed_ips'] and not re.match(urlserver_settings['http_allowed_ips'], addr[0]):
        if urlserver_settings['debug'] == 'on':
            weechat.prnt('', 'urlserver: IP not allowed')
        conn.close()
        return weechat.WEECHAT_RC_OK
    data = None
    try:
        conn.settimeout(0.3)
        data = conn.recv(4096).decode('utf-8')
        data = data.replace('\r\n', '\n')
    except:
        return weechat.WEECHAT_RC_OK
    replysent = False
    sort = '-time'
    m = re.search('^GET /(.*) HTTP/.*$', data, re.MULTILINE)
    if m:
        url = m.group(1)
        if urlserver_settings['debug'] == 'on':
            weechat.prnt('', 'urlserver: %s' % m.group(0))
        if 'favicon.' in url:
            urlserver_server_reply(conn, '200 OK', '',
                                   urlserver_server_favicon(), mimetype='image/x-icon')
            replysent = True
        else:
            # check if prefix is ok (if prefix defined in settings)
            prefixok = True
            if urlserver_settings['http_url_prefix']:
                if url.startswith(urlserver_settings['http_url_prefix']):
                    url = url[len(urlserver_settings['http_url_prefix']):]
                    if url.startswith('/'):
                        url = url[1:]
                else:
                    prefixok = False
            # prefix ok, go on with url
            if prefixok:
                if url.startswith('sort='):
                    # sort asked for list of urls
                    sort = url[5:]
                    url = ''
                if url:
                    # short url, read base62 key and redirect to page
                    number = -1
                    try:
                        number = base62_decode(url)
                    except:
                        pass
                    if number >= 0 and number in urlserver['urls']:
                        # no redirection with "Location:" because it sends HTTP referer
                        #conn.sendall('HTTP/1.1 302 Found\nLocation: %s\n' % urlserver['urls'][number][2])
                        urlserver_server_reply(conn, '200 OK', '',
                                               '<meta http-equiv="refresh" content="0; url=%s">' % urlserver['urls'][number][3])
                        replysent = True
                else:
                    # page with list of urls
                    authok = True
                    if urlserver_settings['http_auth']:
                        auth = re.search('^Authorization: Basic (\S+)$', data, re.MULTILINE)
                        if not auth or base64_decode(auth.group(1)).decode('utf-8') != urlserver_settings['http_auth']:
                            authok = False
                    if authok:
                        urlserver_server_reply_list(conn, sort)
                    else:
                        urlserver_server_reply(conn, '401 Authorization required',
                                               'WWW-Authenticate: Basic realm="%s"' % SCRIPT_NAME, '')
                    replysent = True
            else:
                if urlserver_settings['debug'] == 'on':
                    weechat.prnt('', 'urlserver: prefix missing')
    if not replysent:
        urlserver_server_reply(conn,
                               '404 Not found', '',
                               '<html>\n'
                               '<head><title>Page not found</title></head>\n'
                               '<body><h1>Page not found</h1></body>\n'
                               '</html>')
    conn.close()
    return weechat.WEECHAT_RC_OK

def urlserver_server_status():
    """Display status of server."""
    global urlserver
    if urlserver['socket']:
        weechat.prnt('', 'URL server listening on %s' % str(urlserver['socket'].getsockname()))
    else:
        weechat.prnt('', 'URL server not running')

def urlserver_server_start():
    """Start mini HTTP server."""
    global urlserver, urlserver_settings
    if urlserver['socket']:
        weechat.prnt('', 'URL server already running')
        return
    port = 0
    try:
        port = int(urlserver_settings['http_port'])
    except:
        port = 0
    urlserver['socket'] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    urlserver['socket'].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        urlserver['socket'].bind((urlserver_settings['http_hostname'] or socket.getfqdn(), port))
    except Exception as e:
        weechat.prnt('', '%sBind error: %s' % (weechat.prefix('error'), e))
        urlserver['socket'] = None
        urlserver_server_status()
        return
    urlserver['socket'].listen(5)
    urlserver['hook_fd'] = weechat.hook_fd(urlserver['socket'].fileno(), 1, 0, 0, 'urlserver_server_fd_cb', '')
    urlserver_server_status()

def urlserver_server_stop():
    """Stop mini HTTP server."""
    global urlserver
    if urlserver['socket'] or urlserver['hook_fd']:
        if urlserver['socket']:
            urlserver['socket'].close()
            urlserver['socket'] = None
        if urlserver['hook_fd']:
            weechat.unhook(urlserver['hook_fd'])
            urlserver['hook_fd'] = None
        weechat.prnt('', 'URL server stopped')

def urlserver_server_restart():
    """Restart mini HTTP server."""
    urlserver_server_stop()
    urlserver_server_start()

def urlserver_display_url_detail(key, return_url=False):
    global urlserver
    url = urlserver['urls'][key]
    nick = url[1]
    if nick:
        nick += ' @ '

    if return_url:
        return urlserver_short_url(key)
    else:
        weechat.prnt_date_tags(urlserver['buffer'], 0, 'notify_none',
                               '%s, %s%s%s%s: %s%s%s -> %s' % (url[0],
                                                               nick,
                                                               weechat.color('chat_buffer'),
                                                               url[2],
                                                               weechat.color('reset'),
                                                               weechat.color(urlserver_settings['color']),
                                                               urlserver_short_url(key),
                                                               weechat.color('reset'),
                                                               url[3]))

def urlserver_buffer_input_cb(data, buffer, input_data):
    if input_data in ('q', 'Q'):
        weechat.buffer_close(buffer)
    return weechat.WEECHAT_RC_OK

def urlserver_buffer_close_cb(data, buffer):
    global urlserver
    urlserver['buffer'] = ''
    return weechat.WEECHAT_RC_OK

def urlserver_open_buffer():
    global urlserver, urlserver_settings
    if not urlserver['buffer']:
        urlserver['buffer'] = weechat.buffer_new(SCRIPT_BUFFER,
                                                 'urlserver_buffer_input_cb', '',
                                                 'urlserver_buffer_close_cb', '')
    if urlserver['buffer']:
        weechat.buffer_set(urlserver['buffer'], 'title', 'urlserver')
        weechat.buffer_set(urlserver['buffer'], 'localvar_set_no_log', '1')
        weechat.buffer_set(urlserver['buffer'], 'time_for_each_line', '0')
        weechat.buffer_set(urlserver['buffer'], 'print_hooks_enabled', '0')
        weechat.buffer_clear(urlserver['buffer'])
        keys = sorted(urlserver['urls'])
        for key in keys:
            urlserver_display_url_detail(key)
        weechat.buffer_set(urlserver['buffer'], 'display', '1')

def urlserver_cmd_cb(data, buffer, args):
    """The /urlserver command."""
    global urlserver
    if args == 'start':
        urlserver_server_start()
    elif args == 'restart':
        urlserver_server_restart()
    elif args == 'stop':
        urlserver_server_stop()
    elif args == 'status':
        urlserver_server_status()
    elif args == 'clear':
        urlserver['urls'] = {}
        urlserver['number'] = 0
        weechat.prnt('', 'urlserver: list cleared')
    else:
        urlserver_open_buffer()
    return weechat.WEECHAT_RC_OK

def urlserver_update_urllist(buffer_full_name, buffer_short_name, tags, prefix, message, nick=None):
    """Update urls list and return a list of short urls for message."""
    global urlserver, urlserver_settings

    # skip ignored buffers
    if urlserver_settings['msg_ignore_buffers']:
        if buffer_full_name in urlserver_settings['msg_ignore_buffers'].split(','):
            return None

    listtags = []
    if tags:
        listtags = tags.split(',')

        # skip ignored tags
        if urlserver_settings['msg_ignore_tags']:
            for itag in urlserver_settings['msg_ignore_tags'].split(','):
                for tag in listtags:
                    if tag.startswith(itag):
                        return None

        # exit if a required tag is missing
        if urlserver_settings['msg_require_tags']:
            for rtag in urlserver_settings['msg_require_tags'].split(','):
                tagfound = False
                for tag in listtags:
                    if tag.startswith(rtag):
                        tagfound = True
                        break
                if not tagfound:
                    return None

    # ignore message is matching the "msg_ignore_regex"
    if urlserver_settings['msg_ignore_regex']:
        if re.search(urlserver_settings['msg_ignore_regex'], prefix + '\t' + message):
            return None

    # extract nick from tags
    if not nick:
        nick = ''
        for tag in listtags:
            if tag.startswith('nick_'):
                nick = tag[5:]
                break

    # get URL min length
    min_length = 0
    try:
        min_length = int(urlserver_settings['url_min_length'])
        # Detect the minimum length based on shorten url length
        if min_length == -1:
            min_length = len(urlserver_short_url(urlserver['number'])) + 1
    except:
        min_length = 0

    # shorten URL(s) in message
    urls_short = []
    for url in urlserver['regex'].findall(message):
        if len(url) >= min_length:
            if urlserver_settings['msg_ignore_dup_urls'] == 'on':
                if [key for key, value in urlserver['urls'].items() if value[3] == url]:
                    continue
            number = urlserver['number']
            if not url.startswith(urlserver_get_hostname()): # don't save urls already shorten
                urlserver['urls'][number] = (datetime.datetime.now().strftime(urlserver_settings['http_time_format']), nick, buffer_short_name, url, '%s\t%s' % (prefix, message))
                urls_short.append(urlserver_short_url(number))
                if urlserver['buffer']:
                    urlserver_display_url_detail(number)
                urlserver['number'] += 1

    # remove old URLs if we have reach max list size
    urls_amount = 50
    try:
        urls_amount = int(urlserver_settings['urls_amount'])
        if urls_amount <= 0:
            urls_amount = 50
    except:
        urls_amount = 50
    while len(urlserver['urls']) > urls_amount:
        keys = sorted(urlserver['urls'])
        del urlserver['urls'][keys[0]]

    return urls_short

def urlserver_print_cb(data, buffer, time, tags, displayed, highlight, prefix, message):
    """Callback for message printed in buffer: display short URLs after message."""
    global urlserver, urlserver_settings

    if urlserver_settings['display_urls'] == 'on':
        buffer_full_name = '%s.%s' % (weechat.buffer_get_string(buffer, 'plugin'), weechat.buffer_get_string(buffer, 'name'))
        if urlserver_settings['buffer_short_name'] == 'on':
            buffer_short_name = weechat.buffer_get_string(buffer, 'short_name')
        else:
            buffer_short_name = buffer_full_name
        urls_short = urlserver_update_urllist(buffer_full_name, buffer_short_name, tags, prefix, message)
        if urls_short:
            if urlserver_settings['separators'] and len(urlserver_settings['separators']) == 3:
                separator = ' %s ' % (urlserver_settings['separators'][1])
                urls_string = separator.join(urls_short)
                urls_string = '%s %s %s' % (urlserver_settings['separators'][0], urls_string, urlserver_settings['separators'][2])
            else:
                urls_string = ' | '.join(urls_short)
                urls_string = '[ ' + urls_string + ' ]'
            weechat.prnt_date_tags(buffer, 0, 'no_log,notify_none', '%s%s' % (weechat.color(urlserver_settings['color']), urls_string))

    return weechat.WEECHAT_RC_OK

def urlserver_modifier_irc_cb(data, modifier, modifier_data, string):
    """Modifier for IRC message: add short URLs at the end of IRC message."""
    global urlserver, urlserver_settings

    if urlserver_settings['display_urls_in_msg'] != 'on':
        return string

    msg = weechat.info_get_hashtable('irc_message_parse',
                                     { 'message': string,
                                       'server': modifier_data })
    if 'nick' not in msg or 'channel' not in msg or 'arguments' not in msg:
        return string

    try:
        message = msg['arguments'].split(' ', 1)[1]
        if message.startswith(':'):
            message = message[1:]
    except:
        return string

    if weechat.info_get('irc_is_channel', '%s,%s' % (modifier_data, msg['channel'])) == '1':
        name = msg['channel']
    else:
        name = msg['nick']
    buffer_full_name = 'irc.%s.%s' % (modifier_data, name)
    if urlserver_settings['buffer_short_name'] == 'on':
        buffer_short_name = name
    else:
        buffer_short_name = buffer_full_name
    urls_short = urlserver_update_urllist(buffer_full_name, buffer_short_name, None, msg['nick'], message, msg['nick'])
    if urls_short:
        if urlserver_settings['separators'] and len(urlserver_settings['separators']) == 3:
            separator = ' %s ' % (urlserver_settings['separators'][1])
            urls_string = separator.join(urls_short)
            urls_string = '%s %s %s' % (urlserver_settings['separators'][0], urls_string, urlserver_settings['separators'][2])
        else:
            urls_string = ' | '.join(urls_short)
            urls_string = '[ ' + urls_string + ' ]'

        if urlserver_settings['color_in_msg']:
            urls_string = '\x03%s%s' % (urlserver_settings['color_in_msg'], urls_string)
        string = "%s %s" % (string, urls_string)

    return string

def urlserver_config_cb(data, option, value):
    """Called when a script option is changed."""
    global urlserver_settings
    pos = option.rfind('.')
    if pos > 0:
        name = option[pos+1:]
        if name in urlserver_settings:
            if name == 'http_allowed_ips':
                urlserver_settings[name] = re.compile(value)
            else:
                urlserver_settings[name] = value
                if name in ('http_hostname', 'http_port'):
                    # Don't restart if autostart is disabled and server isn't already running
                    if urlserver_settings['http_autostart'] == 'on' or urlserver['socket']:
                        urlserver_server_restart()
    return weechat.WEECHAT_RC_OK

def urlserver_filename():
    """Return name of file used to store list of urls."""
    return os.path.join(weechat.info_get('weechat_dir', ''), 'urlserver_list.txt')

def urlserver_read_urls():
    """Read file with URLs."""
    global urlserver
    filename = urlserver_filename()
    if os.path.isfile(filename):
        urlserver['number'] = 0
        try:
            urlserver['urls'] = ast.literal_eval(open(filename, 'r').read())
            keys = sorted(urlserver['urls'])
            if keys:
                urlserver['number'] = keys[-1] + 1
            else:
                urlserver['number'] = 0
        except:
            weechat.prnt('', '%surlserver: error reading file "%s"' % (weechat.prefix('error'), filename))

def urlserver_write_urls():
    """Write file with URLs."""
    global urlserver
    keys = sorted(urlserver['urls'])
    content = '{\n%s\n}\n' % '\n'.join(['  %d: %s,' % (key, str(urlserver['urls'][key])) for key in keys])
    open(urlserver_filename(), 'w').write(content)

def urlserver_end():
    """Script unloaded (oh no, why?)"""
    urlserver_server_stop()
    urlserver_write_urls()
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                        SCRIPT_DESC, 'urlserver_end', ''):
        # set default settings
        version = weechat.info_get('version_number', '') or 0
        for option, value in urlserver_settings_default.items():
            if weechat.config_is_set_plugin(option):
                urlserver_settings[option] = weechat.config_get_plugin(option)
            else:
                weechat.config_set_plugin(option, value[0])
                urlserver_settings[option] = value[0]
            if int(version) >= 0x00030500:
                weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

        # detect config changes
        weechat.hook_config('plugins.var.python.%s.*' % SCRIPT_NAME, 'urlserver_config_cb', '')

        # add command
        weechat.hook_command(SCRIPT_COMMAND, SCRIPT_DESC, 'start|restart|stop|status || clear',
                             '  start: start server\n'
                             'restart: restart server\n'
                             '   stop: stop server\n'
                             ' status: display status of server\n'
                             '  clear: remove all URLs from list\n\n'
                             'Without argument, this command opens new buffer with list of URLs.\n\n'
                             'Initial setup:\n'
                             '  - by default, script will listen on a random free port, you can force a port with:\n'
                             '      /set plugins.var.python.urlserver.http_port "1234"\n'
                             '  - you can force an IP or custom hostname with:\n'
                             '      /set plugins.var.python.urlserver.http_hostname "111.22.33.44"\n'
                             '  - it is strongly recommended to restrict IPs allowed and/or use auth, for example:\n'
                             '      /set plugins.var.python.urlserver.http_allowed_ips "^(123.45.67.89|192.160.*)$"\n'
                             '      /set plugins.var.python.urlserver.http_auth "user:password"\n'
                             '  - if you do not like the default HTML formatting, you can override the CSS:\n'
                             '      /set plugins.var.python.urlserver.http_css_url "http://example.com/sample.css"\n'
                             '      See https://raw.github.com/FiXato/weechat_scripts/master/urlserver/sample.css\n'
                             '  - don\'t like the built-in HTTP server to start automatically? Disable it:\n'
                             '      /set plugins.var.python.urlserver.http_autostart "off"\n'
                             '  - have external port 80 or 443 (https) forwarded to your internal server port? Remove :port with:\n'
                             '      /set plugins.var.python.urlserver.http_port_display "80" or "443" respectively\n'
                             '\n'
                             'Tip: use URL without key at the end to display list of all URLs in your browser.',
                             'start|restart|stop|status|clear', 'urlserver_cmd_cb', '')

        if urlserver_settings['http_autostart'] == 'on':
            # start mini HTTP server
            urlserver_server_start()

        # load urls from file
        urlserver_read_urls()

        # catch URLs in buffers
        weechat.hook_print('', '', '://', 1, 'urlserver_print_cb', '')

        # modify URLS in irc messages (for relay)
        weechat.hook_modifier('irc_in2_privmsg', 'urlserver_modifier_irc_cb', '')
        weechat.hook_modifier('irc_in2_notice', 'urlserver_modifier_irc_cb', '')

        # search buffer
        urlserver['buffer'] = weechat.buffer_search('python', SCRIPT_BUFFER)
