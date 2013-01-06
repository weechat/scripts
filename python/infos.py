# -*- coding: utf-8 -*-
###
# Copyright (c) 2011 by Elián Hanisch <lambdae2@gmail.com>
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
###

###
#   View and use WeeChat's infos.
#
#   Commands:
#   * /infos
#
#   History:
#     2013-01-06, Sebastien Helleu <flashcode@flashtux.org>:
#       version 0.2: make script compatible with Python 3.x
#     2011-10-02
#       version 0.1: new script!
#
###

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

SCRIPT_NAME    = "infos"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "View and use WeeChat's infos."

# -------------------------------------------------------------------------
# Class definitions

class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'info_name'   :'string',
            'plugin_name' :'string',
            'description_nls' :'string',
            'args_description_nls' :'string',
            }

    def __init__(self, name, args=''):
        self.cursor = 0
        #debug('Generating infolist %r %r', name, args)
        self.pointer = weechat.infolist_get(name, '', args)
        if self.pointer == '':
            raise Exception("Infolist initialising failed (name:'%s' args:'%s')" %(name, args))

    def __len__(self):
        """True False evaluation."""
        if self.pointer:
            return 1
        else:
            return 0

    def __del__(self):
        """Purge infolist if is no longer referenced."""
        self.free()

    def __getitem__(self, name):
        """Implement the evaluation of self[name]."""
        value = getattr(weechat, 'infolist_%s' % self.fields[name])(self.pointer, name)
        return value

    def __iter__(self):
        def generator():
            while self.next():
                yield self
        return generator()

    def next(self):
        self.cursor = weechat.infolist_next(self.pointer)
        return self.cursor

    def prev(self):
        self.cursor = weechat.infolist_prev(self.pointer)
        return self.cursor

    def reset(self):
        """Moves cursor to beginning of infolist."""
        if self.cursor == 1: # only if we aren't in the beginning already
            while self.prev():
                pass

    def free(self):
        if self.pointer:
            #debug('Freeing Infolist')
            weechat.infolist_free(self.pointer)
            self.pointer = ''

# -------------------------------------------------------------------------
# Functions

def catchExceptions(f):
    def function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error(e)
    return function

script_nick = SCRIPT_NAME
def error(s, buffer=''):
    """Error msg"""
    prnt(buffer, '%s%s %s' % (weechat.prefix('error'), script_nick, s))
    if weechat.config_get_plugin('debug'):
        import traceback
        if traceback.sys.exc_type:
            trace = traceback.format_exc()
            prnt('', trace)

# -------------------------------------------------------------------------
# infos functions

def get_infos_list():
    return [ info['info_name'] for info in Infolist('hook', 'info') ]

def print_infos_description(buffer='', info_name=None):
    def print_desc(infolist):
        name = "%s[%s%s%s]" % (COLOR_CHAT_DELIMITERS,
                               COLOR_CHAT_BUFFER,
                               infolist['info_name'],
                               COLOR_CHAT_DELIMITERS)
        prnt(buffer, '')
        prnt(buffer, name)
        prnt(buffer, "plugin ........: %s%s" % (COLOR_CYAN,
                                                infolist['plugin_name'] or 'core'))
        prnt(buffer, "arguments .....: %s%s" % (COLOR_CYAN,
                                                infolist['args_description_nls']
                                                or '(no description)'))
        prnt(buffer, "description ...: %s%s" % (COLOR_CYAN,
                                                infolist['description_nls']
                                                or "(no description)"))

    infolist = Infolist('hook', 'info')
    found = False
    for info in infolist:
        if not info_name:
            print_desc(infolist)
        elif info_name == info['info_name']:
            found = True
            print_desc(infolist)

    if info_name and not found:
        prnt(buffer, "No info found with name \"%s\"" % info_name)

# -------------------------------------------------------------------------
# callbacks

@catchExceptions
def cmd_infos(data, buffer, args):
    cmd, _, args = args.partition(' ')
    info, _, args = args.partition(' ')
    if cmd == 'get' and info:
        if info not in get_infos_list():
            prnt('', "No info found with name \"%s\"" % info)
            return WEECHAT_RC_OK

        rt = weechat.info_get(info, args)
        header = "%s[%s%s%s] (%s%r%s)" % (COLOR_CHAT_DELIMITERS,
                                          COLOR_CHAT_BUFFER,
                                          info,
                                          COLOR_CHAT_DELIMITERS,
                                          COLOR_RESET,
                                          args,
                                          COLOR_CHAT_DELIMITERS)
        prnt('', '')
        prnt('', header)
        prnt('', "Result: %s%r" % (COLOR_CYAN, rt))
    elif cmd == 'show':
        print_infos_description(info_name=info)
    else:
        weechat.command('', "/help infos")

    return WEECHAT_RC_OK


def cmpl_infos_list(data, completion_item, buffer, completion):
    for name in get_infos_list():
        weechat.hook_completion_list_add(completion, name, 0, weechat.WEECHAT_LIST_POS_END)
    return WEECHAT_RC_OK

# -------------------------------------------------------------------------
# Main

if __name__ == '__main__' and import_ok and \
            weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR,
                             SCRIPT_VERSION, SCRIPT_LICENSE,
                             SCRIPT_DESC, '', ''):

    # colors
    COLOR_RESET           = weechat.color('reset')
    COLOR_CHAT_DELIMITERS = weechat.color('chat_delimiters')
    COLOR_CHAT_NICK       = weechat.color('chat_nick')
    COLOR_CHAT_BUFFER     = weechat.color('chat_buffer')
    COLOR_CYAN            = weechat.color('cyan')


    # pretty [SCRIPT_NAME]
    script_nick = '%s[%s%s%s]%s' % (COLOR_CHAT_DELIMITERS,
                                    COLOR_CHAT_NICK,
                                    SCRIPT_NAME,
                                    COLOR_CHAT_DELIMITERS,
                                    COLOR_RESET)

    weechat.hook_command("infos", "View and use WeeChat infos",
                         "show [<info_name>] || get <info_name> [<arguments>]",
                         "show: Shows information about all infos or info <info_name>.\n"\
                         " get: Get info <info_name>.",
                         "get|show %(infos_info_list)",
                         "cmd_infos", "")

    weechat.hook_completion('infos_info_list', 'List of info names',
                            'cmpl_infos_list', '')

    # -------------------------------------------------------------------------
    # Debug

    if weechat.config_get_plugin('debug'):
        try:
            # custom debug module I use, allows me to inspect script's objects.
            import pybuffer
            debug = pybuffer.debugBuffer(globals(), '%s_debug' % SCRIPT_NAME)
        except ImportError:
            def debug(s, *args):
                if not isinstance(s, str):
                    s = str(s)
                if args:
                    s = s %args
                prnt('', '%s\t%s' % (script_nick, s))
    else:
        def debug(s, *args):
            pass


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
