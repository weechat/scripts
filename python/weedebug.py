# -*- coding: utf-8 -*-
###
# Copyright (c) 2010 by Elián Hanisch <lambdae2@gmail.com>
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
# Module for debugging python scripts. Please note that this doesn't give you an interactive console, it
# can only evaluate simple statements, assignations like "myVar = True" will raise an exception.
#
# For debug a script, insert these lines after script's register() call.
#
#
# from weedebug import DebugBuffer
# debug = DebugBuffer("any_name", globals())
# debug.display()
#
#
# Then, after loading your script, try "dir()" in the new "any_name" buffer, it should
# display the script's global functions and variables.
# This module should be in your python scripts path.
#
# weedebug.py can be loaded as a script, but you will only able to test functions in WeeChat's API.
#
# Session example (loaded as a script):
#
# >>> buffer_search('irc', 'freenode.#weechat')
# 0x9ca4ce0
# >>> buffer_get('0x9ca4ce0', 'input')
# Traceback (most recent call last):
#   File "/home/m4v/.weechat/python/weedebug.py", line 153, in input
#     s = eval(input, self.globals)
#   File "<string>", line 1, in <module>
# NameError: name 'buffer_get' is not defined
# >>> search_api('buffer')
# ['buffer_clear', 'buffer_close', 'buffer_get_integer', 'buffer_get_pointer', 'buffer_get_string',
# 'buffer_merge', 'buffer_new', 'buffer_search', 'buffer_search_main', 'buffer_set',
# 'buffer_string_replace_local_var', 'buffer_unmerge', 'current_buffer', 'string_input_for_buffer']
# >>> buffer_get_string('0x9ca4ce0', 'input')
#
# >>> buffer_get_string('0x9ca4ce0', 'input')
# asdasdas hello!
# >>> buffer_get_string('0x9ca4ce0', 'title')
# WeeChat, stable: 0.3.3, web: http://www.weechat.org/ | English support channel | Please read
# doc/faq/quickstart before asking here | Old versions (0.2.6.x and earlier) are not supported any
# more
#
#
#   History:
#   2010-10-30
#   version 0.1: Initial release
###

SCRIPT_NAME    = "weedebug"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Debugging tool for python scripts or test WeeChat's API functions."

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import __main__
import traceback

def callback(method):
    """This function will take a bound method or function and make it a callback."""
    # try to create a descriptive and unique name.
    func = method.func_name
    try:
        im_self = method.im_self
        try:
            inst = im_self.__name__
        except AttributeError:
            try:
                inst = im_self.name
            except AttributeError:
                inst = ''
        cls = type(im_self).__name__
        name = '_'.join((cls, inst, func))
    except AttributeError:
        # not a bound method
        name = func
    # set our callback
    setattr(__main__, name, method)
    return name


class SimpleBuffer(object):
    """WeeChat buffer. Only for displaying lines."""
    def __init__(self, name):
        assert name, "Buffer needs a name."
        self.__name__ = name
        self._pointer = ''

    def _getBuffer(self):
        buffer = weechat.buffer_search('python', self.__name__)
        if not buffer:
            buffer = self.create()
        return buffer

    def _create(self):
        return weechat.buffer_new(self.__name__, '', '', '', '')

    def create(self):
        buffer = self._create()
        self._pointer = buffer
        return buffer

    def __call__(self, s, *args, **kwargs):
        self.prnt(s, *args, **kwargs)

    def display(self):
        buffer = self._getBuffer()
        weechat.buffer_set(buffer, 'display', '1')

    def error(self, s, *args):
        self.prnt(s, prefix='error')

    def prnt(self, s, *args, **kwargs):
        """Prints messages in buffer."""
        buffer = self._getBuffer()
        if not isinstance(s, basestring):
            s = str(s)
        if args:
            s = s %args
        if 'prefix' in kwargs:
            prefix = weechat.prefix(kwargs['prefix'])
            s = prefix + s
        prnt(buffer, s)


class Buffer(SimpleBuffer):
    """WeeChat buffer. With input and close methods."""
    def _create(self):
        return weechat.buffer_new(self.__name__, callback(self.input), '', callback(self.close), '')

    def input(self, data, buffer, input):
        return WEECHAT_RC_OK

    def close(self, data, buffer):
        return WEECHAT_RC_OK


class DebugBuffer(Buffer):
    def __init__(self, name, globals={}):
        Buffer.__init__(self, name)
        self.globals = globals

    def _create(self):
        buffer = Buffer._create(self)
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'time_for_each_line', '0')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
        return buffer

    def input(self, data, buffer, input):
        """Python code evaluation."""
        try:
            self.prnt(weechat.color('lightgreen') + '>>> ' + input)
            s = eval(input, self.globals)
            self.prnt(s)
        except:
            trace = traceback.format_exc()
            self.prnt(weechat.color('lightred') + trace)
        return WEECHAT_RC_OK


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

        # we're being loaded as a script.
        # create global space with weechat module and its functions.
        globals = dict(( (name, getattr(weechat, name)) for name in dir(weechat) ))
        globals['weechat'] = weechat

        def search_api(s=''):
            """List functions/objects that contains 's' in their name."""
            return [ name for name in dir(weechat) if s in name ]

        globals['search_api'] = search_api

        myBuffer = DebugBuffer(SCRIPT_NAME, globals)
        myBuffer("Test simple Python statements here.")
        myBuffer("Example: \"buffer_search('python', '%s')\"" %SCRIPT_NAME)
        myBuffer("For a list of WeeChat API functions, type \"search_api()\" or \"search_api('word')\"")
        myBuffer.display()


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
