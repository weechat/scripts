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
# Python interpreter for WeeChat, and module for debugging python scripts.
#
#   Commands (see detailed help with /help in WeeChat):
#   * /pybuffer: Opens a python interpreter buffer.
#
# For debug a script, insert these lines after script's register() call.
#
#   import pybuffer
#   debug = pybuffer.debugBuffer(globals(), "buffer_name")
#
# Then, after loading your script, try "dir()" in the new "buffer_name" buffer, it should
# display the script's global functions and variables.
# This module should be in your python scripts path.
#
# Session example:
#
#   >>> buffer_search('irc', 'freenode.#weechat')
#   '0x9ca4ce0'
#   >>> b = buffer_search('irc', 'freenode.#weechat')
#   >>> b
#   '0x9ca4ce0'
#   >>> buffer_get(b, 'input')
#   Traceback (most recent call last):
#     File "<console>", line 1, in <module>    
#   NameError: name 'buffer_get' is not defined
#   >>> search('buffer')
#   ['buffer_clear', 'buffer_close', 'buffer_get_integer', 'buffer_get_pointer', 'buffer_get_string',
#   'buffer_merge', 'buffer_new', 'buffer_search', 'buffer_search_main', 'buffer_set',
#   'buffer_string_replace_local_var', 'buffer_unmerge', 'current_buffer', 'string_input_for_buffer']
#   >>> buffer_get_string(b, 'input')
#   ''
#   >>> buffer_get_string(b, 'input')
#   'asdasdas hello!'
#   >>> buffer_get_string(b, 'title')
#   'WeeChat, stable: 0.3.3, web: http://www.weechat.org/ | English support channel | Please read
#   doc/faq/quickstart before asking here | Old versions (0.2.6.x and earlier) are not supported any
#   more'
#
#
#   History:
#   2010-11-05
#   version 0.2:
#   * More interperter console.
#   * renamed to pybuffer.
#   * added /pybuffer command (buffer isn't created on script load).
#
#   2010-10-30
#   version 0.1: Initial release
###

SCRIPT_NAME    = "pybuffer"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Python interpreter for WeeChat and module for debug scripts."

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import code, sys, traceback
from fnmatch import fnmatch

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
                raise Exception("Instance %s has no __name__ attribute" %im_self)
        cls = type(im_self).__name__
        name = '_'.join((cls, inst, func))
    except AttributeError:
        # not a bound method
        name = func

    # set our callback
    import __main__
    setattr(__main__, name, method)
    return name


class NoArguments(Exception):
    pass


class ArgumentError(Exception):
    pass


class Command(object):
    """Class for hook WeeChat commands."""
    description, usage, help = "WeeChat command.", "[define usage template]", "detailed help here"
    command = ''
    completion = ''

    def __init__(self):
        assert self.command, "No command defined"
        self.__name__ = self.command
        self._pointer = ''   
        self._callback = ''   

    def __call__(self, *args):
        return self.callback(*args)

    def callback(self, data, buffer, args):
        """Called by WeeChat when /command is used."""
        self.data, self.buffer, self.args = data, buffer, args
        try:
            self.parser(args)  # argument parsing
        except ArgumentError, e:
            error('Argument error, %s' %e)
        except NoArguments:
            pass
        else:
            self.execute()
        return WEECHAT_RC_OK

    def parser(self, args):
        """Argument parsing, override if needed."""
        pass

    def execute(self):
        """This method is called when the command is run, override this."""
        pass

    def hook(self):
        assert not self._pointer, \
                "There's already a hook pointer, unhook first (%s)" %self.command
        self._callback = callback(self.callback)
        pointer = weechat.hook_command(self.command,
                                       self.description,
                                       self.usage,
                                       self.help,
                                       self.completion,
                                       self._callback, '')
        if pointer == '':
            raise Exception, "hook_command failed: %s %s" %(SCRIPT_NAME, self.command)
        self._pointer = pointer

    def unhook(self):
        if self._pointer:
            weechat.unhook(self._pointer)
            self._pointer = ''
            self._callback = ''


class SimpleBuffer(object):
    """WeeChat buffer. Only for displaying lines."""
    _title = ''
    def __init__(self, name):
        assert name, "Buffer needs a name."
        self.__name__ = name
        self._pointer = ''

    def _getBuffer(self):
        # we need to always search the buffer, since there's no close callback we can't know if the
        # buffer was closed.
        buffer = weechat.buffer_search('python', self.__name__)
        if not buffer:
            buffer = self.create()
        return buffer

    def _create(self):
        return weechat.buffer_new(self.__name__, '', '', '', '')

    def create(self):
        buffer = self._create()
        if self._title:
            weechat.buffer_set(buffer, 'title', self._title)
        self._pointer = buffer
        return buffer

    def title(self, s):
        self._title = s
        weechat.buffer_set(self._getBuffer(), 'title', s)

    def clear(self):
        weechat.buffer_clear(self._getBuffer())

    def __call__(self, s, *args, **kwargs):
        self.prnt(s, *args, **kwargs)

    def display(self):
        weechat.buffer_set(self._getBuffer(), 'display', '1')

    def error(self, s, *args):
        self.prnt(s, prefix=weechat.prefix('error'))

    def prnt(self, s, *args, **kwargs):
        """Prints messages in buffer."""
        buffer = self._getBuffer()
        if not isinstance(s, basestring):
            s = str(s)
        if args:
            s = s %args
        try:
            s = kwargs['prefix'] + s
        except KeyError:
            pass
        prnt(buffer, s)

    def prnt_lines(self, s, *args, **kwargs):
        for line in s.splitlines():
            self.prnt(line, *args, **kwargs)


class Buffer(SimpleBuffer):
    """WeeChat buffer. With input and close methods."""
    def _create(self):
        return weechat.buffer_new(self.__name__, callback(self.input), '', callback(self.close), '')

    def _getBuffer(self):
        if self._pointer:
            return self._pointer
        return SimpleBuffer._getBuffer(self)

    def input(self, data, buffer, input):
        return WEECHAT_RC_OK

    def close(self, data, buffer):
        self._pointer = ''
        return WEECHAT_RC_OK


class StreamObject(object):
    def __init__(self, buffer):
        self._content = ''
        self._buffer = buffer

    def write(self, s):
        self._content += s

    def prnt(self, *args, **kwargs):
        if self._content:
            self._buffer.prnt_lines(self._content, *args, **kwargs)
            self._content = ''


class PythonBuffer(Buffer):
    _title = "Python Buffer: use search([pattern]) for a list of objects."
    def __init__(self, name, locals=None):
        Buffer.__init__(self, name)
        self.output = StreamObject(self)
        self.error = StreamObject(self)
        # redirect stdout and stderr
        sys.stdout = self.output
        sys.stderr = self.error
        self.console = code.InteractiveConsole(locals)
        locals = self.console.locals
        # add our 'buildin' functions
        if 'search' not in locals:
            def search(s=''):
                """List functions/objects that match 's' in their name."""
                if '*' not in s:
                    s = '*%s*' %s
                return [ name for name in locals if fnmatch(name, s) ]
            locals['search'] = search

    def _create(self):
        buffer = Buffer._create(self)
        weechat.buffer_set(buffer, 'nicklist', '0')
        weechat.buffer_set(buffer, 'time_for_each_line', '0')
        weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
        self.color_input = weechat.color('green')
        self.color_exc = weechat.color('red')
        self.color_call = weechat.color('cyan')
        weechat.hook_command_run('/input return', callback(self.input_return), buffer)
        # print python and WeeChat version
        prnt(buffer, "Python %s" % sys.version.split(None, 1)[0])
        prnt(buffer, "WeeChat %s" % weechat.info_get('version', ''))
        return buffer

    def __call__(self, s, *args, **kwargs):
        kwargs['prefix'] = self.color_call
        self.prnt(s, *args, **kwargs)
    
    def input_return(self, data, buffer, command):
        # we need to send returns even when there's no input.
        if data == buffer and not weechat.buffer_get_string(buffer, 'input'):
            self.input(data, buffer, '\n')
        return WEECHAT_RC_OK

    def input(self, data, buffer, input):
        """Python code evaluation."""
        try:
            need_more = self.console.push(input)
            if need_more:
                prompt = '%s... ' % self.color_input
            else:
                prompt = '%s>>> ' % self.color_input
            self.prnt(input, prefix=prompt)
            self.output.prnt()
            self.error.prnt(prefix=self.color_exc)
        except:
            trace = traceback.format_exc()
            self.prnt_lines(trace, prefix=self.color_exc)
        return WEECHAT_RC_OK

def debugBuffer(globals, name='debugBuffer'):
    buffer = PythonBuffer(name, globals)
    buffer.create()
    return buffer


class PyBufferCommand(Command):
    command = SCRIPT_NAME
    description = usage = help = ''
    def execute(self):
        buffer = PythonBuffer(SCRIPT_NAME)
        buffer.title("Use \"search([pattern])\" for search WeeChat API functions.")
        # import weechat and its functions.
        buffer.input('', '', 'import weechat')
        buffer.input('', '', 'from weechat import *')
        buffer.display()


if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

        # we're being loaded as a script.
        help = \
        "Opens a session with a python interpreter-like buffer."\
        " Use function 'search([pattern])' for list objects in current session.\n"\
        "\n"\
        "For debug a script add these lines after the register call:\n"\
        "\n"\
        "  import pybuffer\n"\
        "  debug = pybuffer.debugBuffer(globals(), 'name')\n"\
        "  debug('debug message example')\n"\
        "\n"\
        "You'll be able to execute python code while your script runs.\n"\
        "\n%(b)sWARNING: %(r)s" \
        "This script isn't fool-proof, you're very capable of crashing/freezing "\
        "WeeChat if you aren't careful with the code you run, use at your own risk."\
        " Running python interactive functions such as 'help()' or 'license()' %(b)swill%(r)s hang"\
        " WeeChat." %dict(b=weechat.color('bold'), r=weechat.color('reset'))

        PyBufferCommand.help = help
        PyBufferCommand().hook()


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
