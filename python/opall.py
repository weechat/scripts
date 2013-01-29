# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, blarz <simon@blarzwurst.de>
#
# Permission to use, copy, modify, and/or distribute this software for any
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

SCRIPT_NAME    = 'opall'
SCRIPT_AUTHOR  = 'blarz'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'ISC'
SCRIPT_DESC    = 'Give op to everybody, like /op -Yes * in irssi'

try:
    import weechat
    import_ok = True
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

def withoutOp(server, channel):
    L = []

    infolist = weechat.infolist_get('irc_nick', '', '%s,%s' %(server, channel))
    while weechat.infolist_next(infolist):
        if not '@' in weechat.infolist_string(infolist, 'prefix'):
            L.append(weechat.infolist_string(infolist, 'name'))
    weechat.infolist_free(infolist)

    return L

def opall(data, buffer, args):
    channel = weechat.buffer_get_string(buffer, 'localvar_channel')
    server = weechat.buffer_get_string(buffer, 'localvar_server')

    if not weechat.info_get('irc_is_channel', channel):
        weechat.prnt(buffer, '%sopall: Not an IRC channel' % weechat.prefix('error'))
        return weechat.WEECHAT_RC_OK

    toOp = withoutOp(server, channel)
    if len(toOp) == 0:
        return weechat.WEECHAT_RC_OK

    # how many people can we op at once
    modes = int(weechat.info_get('irc_server_isupport_value', '%s,MODES' % server)) or 0
    if modes == 0:
        weechat.prnt(buffer, '%sopall: failed to determine MODES' % weechat.prefix('error'))
        return weechat.WEECHAT_RC_ERROR

    frm = 0
    to = modes
    while len(toOp) > frm:
        weechat.command(buffer, '/OP %s' % ' '.join(toOp[frm:to]))
        frm = to
        to += modes

    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')

    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, '', '', '', 'opall', '');
