# -*- coding: utf-8 -*-
#
# Copyright (C) 2013  Stefan Wold <ratler@stderr.eu>
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
# (This script requires WeeChat 0.3.0 or higher).
#
# WeeChat script that convert ascii emotes to the Unicode (version 6.3) equivalent emoticon.
#
# Source available on GitHUB: https://github.com/Ratler/ratlers-weechat-scripts
#
# Contributors:
# Nicolas G. Querol 
#
# Commands:
# /weemoticons - List supported emoticons in the current buffer

SCRIPT_NAME    = "weemoticons"
SCRIPT_AUTHOR  = "Stefan Wold <ratler@stderr.eu>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Convert ascii emotes to unicode emoticons."
SCRIPT_COMMAND = "weemoticons"

import_ok = True

try:
    import weechat
    import re
except ImportError:
    print "This script must be run under WeeChat."
    import_ok = False

ICONS = {
    '^^': u'\U0001F601', '^_^': u'\U0001F601',  # GRINNING FACE WITH SMILING EYES
    # '': u'\U0001F602',  # FACE WITH TEARS OF JOY
    ':)': u'\U0001F603', ':-)': u'\U0001F603', '=)': u'\U0001F603',  # SMILING FACE WITH OPEN MOUTH
    ':D': u'\U0001F604', '=D': u'\U0001F604',  # SMILING FACE WITH OPEN MOUTH AND SMILING EYES
    # '': u'\U0001F605',  # SMILING FACE WITH OPEN MOUTH AND COLD SWEAT
    # '': u'\U0001F606',  # SMILING FACE WITH OPEN MOUTH AND TIGHTLY-CLOSED EYES
    # '': u'\U0001F607',  # SMILING FACE WITH HALO
    '>:D': u'\U0001F608', '>=D': u'\U0001F608',  # SMILING FACE WITH HORNS
    ';)': u'\U0001F609', ';-)': u'\U0001F609',  # WINKING FACE
    '8)': u'\U0001F60A', 'B)': u'\U0001F60A',   # SMILING FACE WITH SMILING EYES
    # '': u'\U0001F60B',  # FACE SAVOURING DELICIOUS FOOD
    # '': u'\U0001F60C',  # RELIEVED FACE
    # '': u'\U0001F60D',  # SMILING FACE WITH HEART-SHAPED EYES
    # '': u'\U0001F60E',  # SMILING FACE WITH SUNGLASSES
    # '': u'\U0001F60F',  # SMIRKING FACE
    # '': u'\U0001F610',  # NEUTRAL FACE
    # '': u'\U0001F611',  # EXPRESSIONLESS FACE
    ':|': u'\U0001F612', '=|': u'\U0001F612', '>_>': u'\U0001F612', '<_<': u'\U0001F612',  # UNAMUSED FACE
    # '': u'\U0001F613',  # FACE WITH COLD SWEAT
    # '': u'\U0001F614',  # PENSIVE FACE
    ':S': u'\U0001F615', ':/': u'\U0001F615', ':\\': u'\U0001F615', '=S': u'\U0001F615', '=/': u'\U0001F615',
    '=\\': u'\U0001F615',  # CONFUSED FACE
    # '': u'\U0001F616',  # CONFOUNDED FACE
    # '': u'\U0001F617',  # KISSING FACE
    # '': u'\U0001F618',  # FACE THROWING A KISS
    # '': u'\U0001F619',  # KISSING FACE WITH SMILING EYES
    # '': u'\U0001F61A',  # KISSING FACE WITH CLOSED EYES
    ':P': u'\U0001F61B', ':p': u'\U0001F61B', '=P': u'\U0001F61B', '=p': u'\U0001F61B',  # FACE WITH STUCK-OUT TONGUE
    ';P': u'\U0001F61C', ';-P': u'\U0001F61C',  # FACE WITH STUCK-OUT TONGUE AND WINKING EYE
    # '': u'\U0001F61D',  # FACE WITH STUCK-OUT TONGUE AND TIGHTLY-CLOSED EYES
    ':(': u'\U0001F61E', ':-(': u'\U0001F61E', '=(': u'\U0001F61E', '=-(': u'\U0001F61E',  # DISAPPOINTED FACE
    # '': u'\U0001F61F',  # WORRIED FACE
    # '': u'\U0001F620',  # ANGRY FACE
    '>:(': u'\U0001F621', '>=(': u'\U0001F621',  # POUTING FACE
    ':\'(': u'\U0001F622', '=\'(': u'\U0001F622',  # CRYING FACE
    '>_<': u'\U0001F623',  # PERSEVERING FACE
    # '': u'\U0001F624',  # FACE WITH LOOK OF TRIUMPH
    # '': u'\U0001F625',  # DISAPPOINTED BUT RELIEVED FACE
    # '': u'\U0001F626',  # FROWNING FACE WITH OPEN MOUTH
    # '': u'\U0001F627',  # ANGUISHED FACE
    # '': u'\U0001F628',  # FEARFUL FACE
    # '': u'\U0001F629',  # WEARY FACE
    # '': u'\U0001F62A',  # SLEEPY FACE
    # '': u'\U0001F62B',  # TIRED FACE
    # '': u'\U0001F62C',  # GRIMACING FACE
    # '': u'\U0001F62D',  # LOUDLY CRYING FACE
    # '': u'\U0001F62E',  # FACE WITH OPEN MOUTH
    # '': u'\U0001F62F',  # HUSHED FACE
    # '': u'\U0001F630',  # FACE WITH OPEN MOUTH AND COLD SWEAT
    # '': u'\U0001F631',  # FACE SCREAMING IN FEAR
    # '': u'\U0001F632',  # ASTONISHED FACE
    ':")': u'\U0001F633', '=")': u'\U0001F633',  # FLUSHED FACE
}

ICON_PATTERN = re.compile(r"(?<!\S)([>;:=8B\^]\S{1,2})")

def icon(match):
    global ICONS
    emoticon = match.group(0)

    if emoticon in ICONS:
        return "%s " % ICONS[emoticon].encode("utf-8")

    return emoticon

def convert_icon_cb(data, modifier, modifier_data, message):
    global ICON_PATTERN

    plugin, buf, tags = modifier_data.split(';')
    tags = tags.split(',')

    if 'irc_privmsg' in tags or 'irc_notice' in tags:
        if ICON_PATTERN.search(message):
            message = ICON_PATTERN.sub(icon, message)

    return message

def list_icons_cb(data, buf, args):
    global ICONS

    l = dict()
    for key, val in ICONS.items():
        if val in l:
            l[val] += ", " + key
        else:
            l[val] = key

    weechat.prnt(buf, "%s - list of supported emoticons:" % SCRIPT_NAME)
    [weechat.prnt(buf, " %s  = %s" % (key.encode("utf-8"), l[key])) for key in l.keys()]

    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
        weechat.hook_modifier("weechat_print", "convert_icon_cb", "")
        weechat.hook_command(SCRIPT_COMMAND, "List supported emoticons", "", "", "", "list_icons_cb", "")
