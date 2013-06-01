# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2013 by Elián Hanisch <lambdae2@gmail.com>
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
#   Helper script for IRC Channel Operators
#
#   Inspired by auto_bleh.pl (irssi) and chanserv.py (xchat) scripts.
#
#   Networks like Freenode and some channels encourage operators to not stay
#   permanently with +o privileges and only use it when needed. This script
#   works along those lines, requesting op, kick/ban/etc and deop
#   automatically with a single command.
#   Still this script is very configurable and its behaviour can be configured
#   in a per server or per channel basis so it can fit most needs without
#   changing its code.
#
#   Features several completions for ban/quiet masks and a memory for channel
#   masks and users (so users that parted are still bannable by nick).
#
#
#   Commands (see detailed help with /help in WeeChat):
#   *      /oop: Request or give op.
#   *    /odeop: Drop or remove op.
#   *    /okick: Kick user (or users).
#   *     /oban: Apply ban mask.
#   *   /ounban: Remove ban mask.
#   *   /oquiet: Apply quiet mask.
#   * /ounquiet: Remove quiet mask.
#   * /obankick: Ban and kick user (or users)
#   *   /otopic: Change channel topic
#   *    /omode: Change channel modes
#   *    /olist: List cached masks (bans or quiets)
#   *   /ovoice: Give voice to user
#   * /odevoice: Remove voice from user
#
#
#   Settings:
#   Most configs (unless noted otherwise) can be defined for a server or a
#   channel in particular, so it is possible to request op in different
#   networks, stay always op'ed in one channel while
#   auto-deop in another.
#
#   For define an option for a specific server use:
#   /set plugins.var.python.chanop.<option>.<server> "value"
#   For define it in a specific channel use:
#   /set plugins.var.python.chanop.<option>.<server>.<#channel> "value"
#
#   * plugins.var.python.chanop.op_command:
#     Here you define the command the script must run for request op, normally
#     is a /msg to a bot, like chanserv in freenode or Q in quakenet.
#     It accepts the special vars $server, $channel and $nick
#
#     By default it ask op to chanserv, if your network doesn't use chanserv,
#     then you must change it.
#
#     Examples:
#     /set plugins.var.python.chanop.op_command
#          "/msg chanserv op $channel $nick"
#     (globally for all servers, like freenode and oftc)
#     /set plugins.var.python.chanop.op_command.quakenet
#          "/msg q op $channel $nick"
#     (for quakenet only)
#
#   * plugins.var.python.chanop.autodeop:
#     Enables auto-deop'ing after using any of the ban or kick commands.
#     Note that if you got op manually (like with /oop) then the script won't
#     deop you.
#     Valid values: 'on', 'off' Default: 'on'
#
#   * plugins.var.python.chanop.autodeop_delay:
#     Time it must pass (without using any commands) before auto-deop, in
#     seconds. Using zero causes to deop immediately.
#     Default: 180
#
#   * plugins.var.python.chanop.default_banmask:
#     List of keywords separated by comas. Defines default banmask, when using
#     /oban, /obankick or /oquiet
#     You can use several keywords for build a banmask, each keyword defines how
#     the banmask will be generated for a given hostmask, see /help oban.
#     Valid keywords are: nick, user, host and exact.
#     Default: 'host'
#
#     Examples:
#     /set plugins.var.python.chanop.default_banmask host
#     (bans with *!*@host)
#     /set plugins.var.python.chanop.default_banmask host,user
#     (bans with *!user@host)
#
#   * plugins.var.python.chanop.kick_reason:
#     Default kick reason if none was given in the command.
#
#   * plugins.var.python.chanop.enable_remove:
#     If enabled, it will use "/quote remove" command instead of /kick, enable
#     it only in networks that support it, like freenode.
#     Valid values: 'on', 'off' Default: 'off'
#
#     Example:
#     /set plugins.var.python.chanop.enable_remove.freenode on
#
#   * plugins.var.python.chanop.display_affected:
#     Whenever a new ban is set, chanop will show the users affected by it.
#     This is intended for help operators to see if their ban is too wide or
#     point out clones in the channel.
#     Valid values: 'on', 'off' Default: 'off'
#
#
#   The following configs are global and can't be defined per server or channel.
#
#   * plugins.var.python.chanop.enable_multi_kick:
#     Enables kicking multiple users with /okick command.
#     Be careful with this as you can kick somebody by accident if
#     you're not careful when writting the kick reason.
#
#     This also applies to /obankick command, multiple bankicks would be enabled.
#     Valid values: 'on', 'off' Default: 'off'
#
#   * plugins.var.python.chanop.enable_bar:
#     This will enable a pop-up bar for displaying chanop messages that would
#     otherwise be printed in the buffer. This bar also shows in realtime the
#     users affected by a ban you're about to set.
#     Valid values: 'on', 'off' Default: 'on'
#
#
#   The following configs are defined per server and are updated by the script only.
#
#   * plugins.var.python.chanop.watchlist:
#     Indicates to chanop which channels should watch and keep track of users and
#     masks. This config is automatically updated when you use any command that needs
#     op, so manual setting shouldn't be needed.
#
#   * plugins.var.python.chanop.isupport:
#     Only used in WeeChat versions prior to 0.3.3 which lacked support for
#     irc_005 messages. These aren't meant to be set manually.
#
#
#   Completions:
#     Chanop has several completions, documented here. Some aren't used by chanop
#     itself, but can be used in aliases with custom completions.
#     Examples:
#     apply exemptions with mask autocompletion
#     /alias -completion %(chanop_ban_mask) exemption /mode $channel +e
#     if you use grep.py script, grep with host autocompletion, for look clones.
#     /alias -completion %(chanop_hosts) ogrep /grep
#
#   * chanop_unban_mask (used in /ounban)
#     Autocompletes with banmasks set in current channel, requesting them if needed.
#     Supports patterns for autocomplete several masks: *<tab> for all bans, or
#     *192.168*<tab> for bans with '192.168' string.
#
#   * chanop_unquiet (used in /ounquiet)
#     Same as chanop_unban_mask, but with masks for q channel mode.
#
#   * chanop_ban_mask (used in /oban and /oquiet)
#     Given a partial IRC hostmask, it will try to complete with hostmasks of current
#     users: *!*@192<tab> will try to complete with matching users, like
#     *!*@192.168.0.1
#
#   * chanop_nicks (used in most commands)
#     Autocompletes nicks, same as WeeChat's completer, but using chanop's user
#     cache, so nicks from users that parted the channel will be still be completed.
#
#   * chanop_users (not used by chanop)
#     Same as chanop_nicks, but with the usename part of the hostmask.
#
#   * chanop_hosts (not used by chanop)
#     Same as chanop_nicks, but with the host part of the hostmask (includes previously used
#     hostnames).
#
#
#   TODO
#   * use dedicated config file like in urlgrab.py?
#   * ban expire time
#   * save ban.mask and ban.hostmask across reloads
#   * allow to override quiet command (for quiet with ChanServ)
#   * freenode:
#    - support for bans with channel forward
#    - support for extbans (?)
#   * Sort completions by user activity
#
#
#   History:
#   2013-05-24
#   version 0.3.1: bug fixes
#   * fix exceptions while fetching bans with /mode
#   * fix crash with /olist command in networks that don't support +q channel masks.
#
#   2013-04-14
#   version 0.3:
#   * cycle between different banmasks in /oban /oquiet commands.
#   * added pop-up bar for show information.
#   * save ban mask information (date and operator)
#   * remove workarounds for < 0.3.2 weechat versions
#   * python 3.0 compatibility (not tested)
#
#   2013-01-02
#   version 0.2.7: bug fixes:
#   * fix /obankick, don't deop before kicking.
#
#   2011-09-18
#   version 0.2.6: bug fixes:
#   * update script to work with freenode's new quiet messages.
#   * /omode wouldn't work with several modes.
#
#   2011-05-31
#   version 0.2.5: bug fixes:
#   * /omode -o nick wouldn't work due to the deopNow switch.
#   * unban_completer could fetch the same masks several times.
#   * removing ban forwards falied when using exact mask.
#   * user nick wasn't updated in every call.
#
#   2011-02-02
#   version 0.2.4: fix python 2.5 compatibility
#
#   2011-01-09
#   version 0.2.3: bug fixes.
#
#   2010-12-23
#   version 0.2.2: bug fixes.
#
#   2010-10-28
#   version 0.2.1: refactoring mostly
#   * deop_command option removed
#   * removed --webchat switch, freenode's updates made it superfluous.
#   * if WeeChat doesn't know a hostmask, use /userhost or /who if needed.
#   * /oban and /oquiet without arguments show ban/quiet list.
#   * most commands allows '-o' option, that forces immediate deop (without configured delay).
#   * updated for WeeChat 0.3.4 (irc_nick infolist changes)
#
#   2010-09-20
#   version 0.2: major update
#   * fixed quiets for ircd-seven (freenode)
#   * implemented user and mask cache.
#   * added commands:
#     - /ovoice /odevoice for de/voice users.
#     - /omode for change channel modes.
#     - /olist for list bans/quiets on cache.
#   * changed /omute and /ounmute commands to /oquiet and /ounquiet, as q masks
#     is refered as a quiet rather than a mute.
#   * autocompletions:
#     - for bans set on a channel.
#     - for make new bans.
#     - for nicks/usernames/hostnames.
#   * /okban renamed to /obankick. This is because /okban is too similar to
#     /okick and bankicking somebody due to tab fail was too easy.
#   * added display_affected feature.
#   * added --webchat ban option.
#   * config options removed:
#     - merge_bans: superseded by isupport methods.
#     - enable_mute: superseded by isupport methods.
#     - invert_kickban_order: now is fixed to "ban, then kick"
#   * Use WeeChat isupport infos.
#   * /oop and /odeop can op/deop other users.
#
#   2009-11-9
#   version 0.1.1: fixes
#   * script renamed to 'chanop' because it was causing conflicts with python
#     'operator' module
#   * added /otopic command
#
#   2009-10-31
#   version 0.1: Initial release
###

WEECHAT_VERSION = (0x30200, '0.3.2')

SCRIPT_NAME    = "chanop"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.3.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Helper script for IRC Channel Operators"

# default settings
settings = {
'op_command'            :'/msg chanserv op $channel $nick',
'autodeop'              :'on',
'autodeop_delay'        :'180',
'default_banmask'       :'host',
'enable_remove'         :'off',
'kick_reason'           :'',
'enable_multi_kick'     :'off',
'display_affected'      :'on',
'enable_bar'            :'on',
}

try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

import os
import re
import time
import string
import getopt
from collections import defaultdict
from shelve import DbfilenameShelf as Shelf

chars = string.maketrans('', '')

# -----------------------------------------------------------------------------
# Messages

script_nick = SCRIPT_NAME
def error(s, buffer=''):
    """Error msg"""
    prnt(buffer, '%s%s %s' % (weechat.prefix('error'), script_nick, s))
    value = weechat.config_get_plugin('debug')
    if value and boolDict[value]:
        import traceback
        if traceback.sys.exc_type:
            trace = traceback.format_exc()
            prnt('', trace)

def say(s, buffer=''):
    """normal msg"""
    prnt(buffer, '%s\t%s' %(script_nick, s))

def _no_debug(*args):
    pass

debug = _no_debug

# -----------------------------------------------------------------------------
# Config

# TODO Need to refactor all this too

boolDict = {'on':True, 'off':False, True:'on', False:'off'}
def get_config_boolean(config, get_function=None, **kwargs):
    if get_function and callable(get_function):
        value = get_function(config, **kwargs)
    else:
        value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_int(config, get_function=None):
    if get_function and callable(get_function):
        value = get_function(config)
    else:
        value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)

valid_banmask = set(('nick', 'user', 'host', 'exact'))
def get_config_banmask(config='default_banmask', get_function=None):
    if get_function and callable(get_function):
        value = get_function(config)
    else:
        value = weechat.config_get_plugin(config)
    values = value.lower().split(',')
    for value in values:
        if value not in valid_banmask:
            default = settings[config]
            error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
            error("'%s' is an invalid value, allowed: %s." %(value, ', '.join(valid_banmask)))
            return default
    #debug("default banmask: %s" %values)
    return values

def get_config_list(config):
    value = weechat.config_get_plugin(config)
    if value:
        return value.split(',')
    else:
        return []

def get_config_specific(config, server='', channel=''):
    """Gets config defined for either server or channel."""
    value = None
    if server and channel:
        string = '%s.%s.%s' %(config, server, channel)
        value = weechat.config_get_plugin(string)
    if server and not value:
        string = '%s.%s' %(config, server)
        value = weechat.config_get_plugin(string)
    if not value:
        value = weechat.config_get_plugin(config)
    return value

# -----------------------------------------------------------------------------
# Utils

now = lambda: int(time.time())

def time_elapsed(elapsed, ret=None, level=2):
    time_hour = 3600
    time_day  = 86400
    time_year = 31536000

    if ret is None:
        ret = []

    if not elapsed:
        return ''

    if elapsed > time_year:
        years, elapsed = elapsed // time_year, elapsed % time_year
        ret.append('%s%s' %(years, 'y'))
    elif elapsed > time_day:
        days, elapsed = elapsed // time_day, elapsed % time_day
        ret.append('%s%s' %(days, 'd'))
    elif elapsed > time_hour:
        hours, elapsed = elapsed // time_hour, elapsed % time_hour
        ret.append('%s%s' %(hours, 'h'))
    elif elapsed > 60:
        mins, elapsed = elapsed // 60, elapsed % 60
        ret.append('%s%s' %(mins, 'm'))
    else:
        secs, elapsed = elapsed, 0
        ret.append('%s%s' %(secs, 's'))

    if len(ret) >= level or not elapsed:
        return ' '.join(ret)

    ret = time_elapsed(elapsed, ret, level)
    return ret

# -----------------------------------------------------------------------------
# IRC utils

_hostmaskRe = re.compile(r':?\S+!\S+@\S+') # poor but good enough
def is_hostmask(s):
    """Returns whether or not the string s starts with something like a hostmask."""
    return _hostmaskRe.match(s) is not None

def is_ip(s):
    """Returns whether or not a given string is an IPV4 address."""
    import socket
    try:
        return bool(socket.inet_aton(s))
    except socket.error:
        return False

_reCache = {}
def cachedPattern(f):
    """Use cached regexp object or compile a new one from pattern."""
    def getRegexp(pattern, *arg):
        try:
            regexp = _reCache[pattern]
        except KeyError:
            s = '^'
            for c in pattern:
                if c == '*':
                    s += '.*'
                elif c == '?':
                    s += '.'
                elif c in '[{':
                    s += r'[\[{]'
                elif c in ']}':
                    s += r'[\]}]'
                elif c in '|\\':
                    s += r'[|\\]'
                else:
                    s += re.escape(c)
            s += '$'
            regexp = re.compile(s, re.I)
            _reCache[pattern] = regexp
        return f(regexp, *arg)
    return getRegexp

def hostmaskPattern(f):
    """Check if pattern is for match a hostmask and remove ban forward if there's one."""
    def checkPattern(pattern, arg):
        # XXX this needs a refactor
        if is_hostmask(pattern):
            # nick!user@host$#channel
            if '$' in pattern:
                pattern = pattern.partition('$')[0]
            if isinstance(arg, list):
                arg = [ s for s in arg if is_hostmask(s) ]
            elif not is_hostmask(arg):
                return ''

            rt = f(pattern, arg)
            # this doesn't match any mask in args with a channel forward
            pattern += '$*'
            if isinstance(arg, list):
                rt.extend(f(pattern, arg))
            elif not rt:
                rt = f(pattern, arg)
            return rt

        return ''
    return checkPattern

match_string = lambda r, s: r.match(s) is not None
match_list = lambda r, L: [ s for s in L if r.match(s) is not None ]

pattern_match = cachedPattern(match_string)
pattern_match_list = cachedPattern(match_list)
hostmask_match = hostmaskPattern(pattern_match)
hostmask_match_list = hostmaskPattern(pattern_match_list)

def get_nick(s):
    """':nick!user@host' => 'nick'"""
    return weechat.info_get('irc_nick_from_host', s)

def get_user(s, trim=False):
    """'nick!user@host' => 'user'"""
    assert is_hostmask(s), "Invalid hostmask: %s" % s
    s = s[s.find('!') + 1:s.find('@')]
    if trim:
        # remove the stuff not part of the username.
        if s[0] == '~':
            return s[1:]
        elif s[:2] in ('i=', 'n='):
            return s[2:]
    return s

def get_host(s):
    """'nick!user@host' => 'host'"""
    assert is_hostmask(s), "Invalid hostmask: %s" % s
    if ' ' in s:
        return s[s.find('@') + 1:s.find(' ')]
    return s[s.find('@') + 1:]

def is_channel(s):
    return weechat.info_get('irc_is_channel', s)

def is_nick(s):
    return weechat.info_get('irc_is_nick', s)

def irc_buffer(buffer):
    """Returns pair (server, channel) or None if buffer isn't an irc channel"""
    get_string = weechat.buffer_get_string
    if get_string(buffer, 'plugin') == 'irc' \
            and get_string(buffer, 'localvar_type') == 'channel':
        channel = get_string(buffer, 'localvar_channel')
        server = get_string(buffer, 'localvar_server')
        return (server, channel)

# -----------------------------------------------------------------------------
# WeeChat classes

class InvalidIRCBuffer(Exception):
    pass

def catchExceptions(f):
    def function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error(e)
    return function

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
                raise Exception("Instance of %s has no __name__ attribute" %type(im_self))
        cls = type(im_self).__name__
        name = '_'.join((cls, inst, func))
    except AttributeError:
        # not a bound method
        name = func

    method = catchExceptions(method)

    # set our callback
    import __main__
    setattr(__main__, name, method)
    return name

def weechat_command(buffer, cmd):
    """I want to always keep debug() calls for this"""
    if buffer:
        debug("%ssending: %r buffer: %s", COLOR_WHITE, cmd, buffer)
    else:
        debug("%ssending: %r", COLOR_WHITE, cmd)
    weechat.command(buffer, cmd)

class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'name'        :'string',
            'option_name' :'string',
            'value'       :'string',
            'host'        :'string',
            'flags'       :'integer',
            'prefixes'    :'string',
            'is_connected':'integer',
            'buffer'      :'pointer',
            }

    _use_flags = False

    def __init__(self, name, args='', pointer=''):
        self.cursor = 0
        #debug('Generating infolist %r %r', name, args)
        self.pointer = weechat.infolist_get(name, pointer, args)
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
        if self._use_flags and name == 'prefixes':
            name = 'flags'
        value = getattr(weechat, 'infolist_%s' %self.fields[name])(self.pointer, name)
        if self._use_flags and name == 'flags':
            value = self._flagsAsString(value)
        return value

    def _flagsAsString(self, n):
        s = ''
        if n & 32:
            s += '+'
        if n & 8:
            s += '@'
        return s

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
            weechat.infolist_free(self.pointer)
            self.pointer = ''

def nick_infolist(server, channel):
    try:
        return Infolist('irc_nick', '%s,%s' % (server, channel))
    except:
        raise InvalidIRCBuffer('%s.%s' % (server, channel))

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
        debug("%s[%s] data: \"%s\" buffer: \"%s\" args: \"%s\"", COLOR_DARKGRAY,
                                                                 self.command,
                                                                 data,
                                                                 buffer,
                                                                 args)
        try:
            self.parser(args)  # argument parsing
        except ArgumentError as e:
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
            raise Exception("hook_command failed: %s %s" % (SCRIPT_NAME, self.command))
        self._pointer = pointer

    def unhook(self):
        if self._pointer:
            weechat.unhook(self._pointer)
            self._pointer = ''
            self._callback = ''

class Bar(object):
    def __init__(self, name, hidden=False, items=''):
        self.name = name
        self.hidden = hidden
        self._pointer = ''
        self._items = items

    def new(self):
        assert not self._pointer, "Bar %s already created" % self.name
        pointer = weechat.bar_search(self.name)
        if not pointer:
            pointer = weechat.bar_new(self.name, boolDict[self.hidden], '0', 'window',
                                      'active', 'bottom', 'horizontal', 'vertical',
                                      '0', '1', 'default', 'cyan', 'blue', 'off',
                                      self._items)
            if not pointer:
                raise Exception("bar_new failed: %s %s" % (SCRIPT_NAME, self.name))

        self._pointer = pointer

    def getPointer(self):
        return weechat.bar_search(self.name)

    def show(self):
        pointer = self.getPointer()
        if pointer and self.hidden:
            weechat.bar_set(pointer, 'hidden', 'off')
            self.hidden = False
        return pointer

    def hide(self):
        pointer = self.getPointer()
        if pointer and not self.hidden:
            weechat.bar_set(pointer, 'hidden', 'on')
            self.hidden = True

    def remove(self):
        pointer = self.getPointer()
        if pointer:
            weechat.bar_remove(pointer)
            self._pointer = ''

    def __len__(self):
        """True False evaluation."""
        if self.getPointer():
            return 1
        else:
            return 0

class PopupBar(Bar):
    _timer_hook = ''
    popup_mode = False

    def popup(self, delay=10):
        if self.show():
            if self._timer_hook:
                weechat.unhook(self._timer_hook)
            self._timer_hook = weechat.hook_timer(delay * 1000, 0, 1, callback(self._timer), '')

    def _timer(self, data, counter):
        self.hide()
        self._timer_hook = ''
        return WEECHAT_RC_OK

# -----------------------------------------------------------------------------
# Per buffer variables

class BufferVariables(dict):
    """Keeps variables and objects of a specific buffer."""
    def __init__(self, buffer):
        self['buffer'] = buffer
        self['irc'] = IrcCommands(buffer)
        self['autodeop'] = True
        self['deopHook'] = self.opHook = self.opTimeout = None
        self['server'] = weechat.buffer_get_string(buffer, 'localvar_server')
        self['channel'] = weechat.buffer_get_string(buffer, 'localvar_channel')
        self['nick'] = weechat.info_get('irc_nick', self.server)

    def __getattr__(self, k):
        return self[k]

    def __setattr__(self, k, v):
        debug(' -- buffer[%s] %s ... %s => %s', self.buffer, k, self.get(k), v)
        self[k] = v

class ChanopBuffers(object):
    """Keeps track of BuffersVariables instances in chanop."""
    buffer = ''
    _buffer = {} # must be shared across instances
    def __getattr__(self, k):
        return self._buffer[self.buffer][k]

    def setup(self, buffer):
        self.buffer = buffer
        if buffer not in self._buffer:
            self._buffer[buffer] = BufferVariables(buffer)
        else:
            # update nick, it might have changed.
            self.vars.nick = weechat.info_get('irc_nick', self.vars.server)

    @property
    def vars(self):
        return self._buffer[self.buffer]

    def varsOf(self, buffer):
        return self._buffer[buffer]

    def replace_vars(self, s):
        try:
            return weechat.buffer_string_replace_local_var(self.buffer, s)
        except AttributeError:
            if '$channel' in s:
                s = s.replace('$channel', self.channel)
            if '$nick' in s:
                s = s.replace('$nick', self.nick)
            if '$server' in s:
                s = s.replace('$server', self.server)
            return s

    def get_config(self, config):
        #debug('config: %s' %config)
        return get_config_specific(config, self.server, self.channel)

    def get_config_boolean(self, config):
        return get_config_boolean(config, self.get_config)

    def get_config_int(self, config):
        return get_config_int(config, self.get_config)

# -----------------------------------------------------------------------------
# IRC messages queue

class Message(ChanopBuffers):
    command = None
    args = ()
    wait = 0
    def __init__(self, cmd=None, args=(), wait=0):
        if cmd:  self.command = cmd
        if args: self.args = args
        if wait: self.wait = wait

    def payload(self):
        cmd = self.command
        if cmd[0] != '/':
            cmd = '/' + cmd
        if self.args:
            cmd += ' ' + ' '.join(self.args)
        if self.wait:
            cmd = '/wait %s ' %self.wait + cmd
        return cmd

    def register(self, buffer):
        self.buffer = buffer

    def __call__(self):
        cmd = self.payload()
        if cmd:
            self.send(cmd)

    def send(self, cmd):
        weechat_command(self.buffer, cmd)

    def __repr__(self):
        return '<Message(%s, %s)>' %(self.command, self.args)

class IrcCommands(ChanopBuffers):
    """Class that manages and sends the script's commands to WeeChat."""

    # Special message classes
    class OpMessage(Message):
        def send(self, cmd):
            if self.irc.checkOp():
                # nothing to do
                return

            self.irc.interrupt = True
            Message.send(self, cmd)

            def modeOpCallback(buffer, signal, signal_data):
                vars = self.varsOf(buffer)
                data = 'MODE %s +o %s' % (vars.channel, vars.nick)
                signal = signal_data.split(None, 1)[1]
                if signal == data:
                    debug('GOT OP')
                    # add this channel to our watchlist
                    config = 'watchlist.%s' % vars.server
                    channels = CaseInsensibleSet(get_config_list(config))
                    if vars.channel not in channels:
                        channels.add(vars.channel)
                        value = ','.join(channels)
                        weechat.config_set_plugin(config, value)
                    weechat.unhook(vars.opHook)
                    weechat.unhook(vars.opTimeout)
                    vars.opTimeout = vars.opHook = None
                    vars.irc.interrupt = False
                    vars.irc.run()
                return WEECHAT_RC_OK

            def timeoutCallback(buffer, count):
                vars = self.varsOf(buffer)
                error("Couldn't get op in '%s', purging command queue..." % vars.channel)
                weechat.unhook(vars.opHook)
                if vars.deopHook:
                    weechat.unhook(vars.deopHook)
                    vars.deopHook = None
                vars.opTimeout = vars.opHook = None
                vars.irc.interrupt = False
                vars.irc.clear()
                return WEECHAT_RC_OK

            # wait for a while before timing out.
            self.vars.opTimeout = weechat.hook_timer(30*1000, 0, 1, callback(timeoutCallback),
                    self.buffer)

            self.vars.opHook = weechat.hook_signal('%s,irc_in2_MODE' %self.server,
                    callback(modeOpCallback), self.buffer)

    class UserhostMessage(Message):
        def send(self, cmd):
            self.irc.interrupt = True
            Message.send(self, cmd)

            def msgCallback(buffer, modifier, modifier_data, string):
                vars = self.varsOf(buffer)
                if vars.server != modifier_data:
                    return string
                nick, host = string.rsplit(None, 1)[1].split('=')
                nick, host = nick.strip(':*'), host[1:]
                hostmask = '%s!%s' % (nick, host)
                debug('USERHOST: %s %s', nick, hostmask)
                userCache.remember(modifier_data, nick, hostmask)
                weechat.unhook(vars.msgHook)
                weechat.unhook(vars.msgTimeout)
                vars.msgTimeout = vars.msgHook = None
                vars.irc.interrupt = False
                vars.irc.run()
                return ''

            def timeoutCallback(buffer, count):
                vars = self.varsOf(buffer)
                weechat.unhook(vars.msgHook)
                vars.msgTimeout = vars.msgHook = None
                vars.irc.interrupt = False
                vars.irc.clear()
                return WEECHAT_RC_OK

            # wait for a while before timing out.
            self.vars.msgTimeout = \
                weechat.hook_timer(30*1000, 0, 1, callback(timeoutCallback), self.buffer)

            self.vars.msgHook = weechat.hook_modifier('irc_in_302',
                    callback(msgCallback), self.buffer)


    class ModeMessage(Message):
        command = 'mode'
        def __init__(self, char=None, args=None, **kwargs):
            self.chars = [ char ]
            self.charargs = [ args ]
            self.args = (char, args)
            Message.__init__(self, **kwargs)

        def payload(self):
            args = []
            modeChar = []
            prefix = ''
            for m, a in zip(self.chars, self.charargs):
                if a:
                    if callable(a):
                        a = a()
                        if not a:
                            continue
                    args.append(a)
                if m[0] != prefix:
                    prefix = m[0]
                    modeChar.append(prefix)
                modeChar.append(m[1])
            args.insert(0, ''.join(modeChar))
            if args:
                self.args = args
                return Message.payload(self)


    class DeopMessage(ModeMessage):
        def send(self, cmd):
            if self.irc.checkOp():
                Message.send(self, cmd)

    # IrcCommands methods
    def __init__(self, buffer):
        self.interrupt = False
        self.commands = []
        self.buffer = buffer

    def checkOp(self):
        infolist = nick_infolist(self.server, self.channel)
        while infolist.next():
            if infolist['name'] == self.nick:
                return '@' in infolist['prefixes']
        return False

    def Op(self):
        if self.opHook and self.opTimeout:
            # already send command, wait for timeout
            return

        value = self.replace_vars(self.get_config('op_command'))
        if not value:
            raise Exception("No command defined for get op.")
        msg = self.OpMessage(value)
        self.queue(msg, insert=True)

    def Deop(self):
        msg = self.DeopMessage('-o', self.nick)
        self.queue(msg)

    def Mode(self, mode, args=None, wait=0):
        msg = self.ModeMessage(mode, args, wait=wait)
        self.queue(msg)

    def Kick(self, nick, reason=None, wait=0):
        if not reason:
            reason = self.get_config('kick_reason')
        if self.get_config_boolean('enable_remove'):
            cmd = '/quote remove %s %s :%s' %(self.channel, nick, reason)
            msg = Message(cmd, wait=wait)
        else:
            msg = Message('kick', (nick, reason), wait=wait)
        self.queue(msg)

    def Voice(self, nick):
        self.Mode('+v', nick)

    def Devoice(self, nick):
        self.Mode('-v', nick)

    def Userhost(self, nick):
        msg = self.UserhostMessage('USERHOST', (nick, ))
        self.queue(msg, insert=True) # USERHOST should be sent first

    def queue(self, message, insert=False):
        debug('queuing: %s', message)
        # merge /modes
        if self.commands and message.command == 'mode':
            max_modes = supported_maxmodes(self.server)
            msg = self.commands[-1]
            if msg.command == 'mode' and len(msg.chars) < max_modes:
                msg.chars.append(message.chars[0])
                msg.charargs.append(message.charargs[0])
                return
        if insert:
            self.commands.insert(0, message)
        else:
            self.commands.append(message)

    # it happened once and it wasn't pretty
    def safe_check(f):
        def abort_if_too_many_commands(self):
            if len(self.commands) > 10:
                error("Limit of 10 commands in queue reached, aborting.")
                self.clear()
            else:
                f(self)
        return abort_if_too_many_commands

    @safe_check
    def run(self):
        while self.commands and not self.interrupt:
            msg = self.commands.pop(0)
            msg.register(self.buffer)
            msg()
            if self.interrupt:
                #debug("Interrupting queue")
                break

    def clear(self):
        debug('clear queue (%s messages)', len(self.commands))
        self.commands = []

    def __repr__(self):
        return '<IrcCommands(%s)>' % ', '.join(map(repr, self.commands))

# -----------------------------------------------------------------------------
# User/Mask classes

_rfc1459trans = string.maketrans(string.ascii_uppercase + r'\[]',
                                 string.ascii_lowercase + r'|{}')
def IRClower(s):
    return s.translate(_rfc1459trans)

class CaseInsensibleString(str):
    def __init__(self, s=''):
        self.lowered = IRClower(s)

    lower    = lambda self: self.lowered
    translate = lambda self, trans: self.lowered
    __eq__   = lambda self, s: self.lowered == IRClower(s)
    __ne__   = lambda self, s: not self == s
    __hash__ = lambda self: hash(self.lowered)

def caseInsensibleKey(k):
    if isinstance(k, str):
        return CaseInsensibleString(k)
    elif isinstance(k, tuple):
        return tuple(map(caseInsensibleKey, k))
    return k

class CaseInsensibleDict(dict):
    key = staticmethod(caseInsensibleKey)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self[k] = v

    def __setitem__(self, k, v):
        dict.__setitem__(self, self.key(k), v)

    def __getitem__(self, k):
        return dict.__getitem__(self, self.key(k))

    def __delitem__(self, k):
        dict.__delitem__(self, self.key(k))

    def __contains__(self, k):
        return dict.__contains__(self, self.key(k))

    def pop(self, k):
        return dict.pop(self, self.key(k))

class CaseInsensibleDefaultDict(defaultdict, CaseInsensibleDict):
    pass

class CaseInsensibleSet(set):
    normalize = staticmethod(caseInsensibleKey)

    def __init__(self, iterable=()):
        iterable = map(self.normalize, iterable)
        set.__init__(self, iterable)

    def __contains__(self, v):
        return set.__contains__(self, self.normalize(v))

    def update(self, L):
        set.update(self, map(self.normalize, L))

    def add(self, v):
        set.add(self, self.normalize(v))

    def remove(self, v):
        set.remove(self, self.normalize(v))

class ChannelWatchlistSet(CaseInsensibleSet):
    _updated = False
    def __contains__(self, v):
        if not self._updated:
            self.__updateFromConfig()
        return CaseInsensibleSet.__contains__(self, v)

    def __updateFromConfig(self):
        self._updated = True
        infolist = Infolist('option', 'plugins.var.python.%s.watchlist.*' %SCRIPT_NAME)
        n = len('python.%s.watchlist.' %SCRIPT_NAME)
        while infolist.next():
            name = infolist['option_name']
            value = infolist['value']
            server = name[n:]
            if value:
                channels = value.split(',')
            else:
                channels = []
            self.update([ (server, channel) for channel in channels ])

chanopChannels = ChannelWatchlistSet()

class ServerChannelDict(CaseInsensibleDict):
    def getChannels(self, server, item=None):
        """Return a list of channels that match server and has item if given"""
        if item:
            return [ chan for serv, chan in self if serv == server and item in self[serv, chan] ]
        else:
            return [ chan for serv, chan in self if serv == server ]

    def purge(self):
        for key in self.keys():
            if key not in chanopChannels:
                debug('removing %s mask list, not in watchlist.', key)
                del self[key]
        for data in self.values():
            data.purge()

# -----------------------------------------------------------------------------
# Channel Modes (bans)

class MaskObject(object):
    def __init__(self, mask, hostmask=[], operator='', date=0, expires=0):
        self.mask = mask
        self.operator = operator
        if date:
            date = int(date)
        else:
            date = now()
        self.date = date
        if isinstance(hostmask, str):
            hostmask = [ hostmask ]
        self.hostmask = hostmask
        self.expires = int(expires)

    def serialize(self):
        data = ';'.join([ self.operator,
                          str(self.date),
                          str(self.expires),
                          ','.join(self.hostmask) ])
        return data

    def deserialize(self, data):
        op, date, expires, hostmasks = data.split(';')
        assert op and date, "Error reading chanmask option %s, missing operator or date" % self.mask
        if not is_hostmask(op):
            raise Exception('Error reading chanmask option %s, invalid usermask %r' \
                            % (self.mask, op))

        self.operator = op
        try:
            self.date = int(date)
        except ValueError:
            self.date = int(time.mktime(time.strptime(date,'%Y-%m-%d %H:%M:%S')))
        if expires:
            self.expires = int(expires)
        else:
            self.expires = 0
        if hostmasks:
            hostmasks = hostmasks.split(',')
            if not all(map(is_hostmask, hostmasks)):
                raise Exception('Error reading chanmask option %s, a hostmask is invalid: %s' \
                                % (self.mask, hostmasks))

            self.hostmask = hostmasks

    def __repr__(self):
        return "<MaskObject(%s)>" % self.mask

class MaskList(CaseInsensibleDict):
    """Single list of masks"""
    def __init__(self, server, channel):
        self.synced = 0

    def add(self, mask, **kwargs):
        if mask in self:
            # mask exists, update it
            ban = self[mask]
            for attr, value in kwargs.items():
                if value and not getattr(ban, attr):
                    setattr(ban, attr, value)
        else:
            ban = self[mask] = MaskObject(mask, **kwargs)
        return ban

#    def searchByNick(self, nick):
#        try:
#            hostmask = userCache.getHostmask(nick, self.server, self.channel)
#            return self.searchByHostmask(hostmask)
#        except KeyError:
#            return []

    def search(self, pattern, reverseMatch=False):
        if reverseMatch:
            L = [ mask for mask in self if hostmask_match(mask, pattern) ]
        else:
            L = pattern_match_list(pattern, self.keys())
        return L

    def purge(self):
        pass

class MaskCache(ServerChannelDict):
    """Keeps a cache of masks for different channels."""
    def add(self, server, channel, mask, **kwargs):
        """Adds a ban to (server, channel) banlist."""
        key = (server, channel)
        if key not in self:
            self[key] = MaskList(*key)
        ban = self[key].add(mask, **kwargs)
        return ban

    def remove(self, server, channel, mask=None):#, hostmask=None):
        key = (server, channel)
        try:
            if mask is None:
                del self[key]
            else:
                del self[key][mask]
                #debug("removing ban: %s" %banmask)
        except KeyError:
            pass

class ChanopCache(Shelf):
    def __init__(self, filename):
        path = os.path.join(weechat.info_get('weechat_dir', ''), filename)
        Shelf.__init__(self, path, writeback=True)

class ModeCache(ChanopCache):
    """class for store channel modes lists."""
    def __init__(self, filename):
        ChanopCache.__init__(self, filename)
        self.modes = set()
        self.map = CaseInsensibleDict()

        # reset all sync timers
        for cache in self.values():
            for masklist in cache.values():
                masklist.synced = 0

    def registerMode(self, mode, *args):
        if mode not in self:
            cache = MaskCache()
            self[mode] = cache

        if mode not in self.modes:
            self.modes.add(mode)

        self.map[mode] = mode
        for name in args:
            self.map[name] = mode

    def __getitem__(self, mode):
        try:
            return ChanopCache.__getitem__(self, mode)
        except KeyError:
            return ChanopCache.__getitem__(self, self.map[mode])

    def add(self, server, channel, mode, mask, **kwargs):
        assert mode in self.modes
        self[mode].add(server, channel, mask, **kwargs)

    def remove(self, server, channel, mode, mask):
        self[mode].remove(server, channel, mask)

    def purge(self):
        for cache in self.values():
            cache.purge()

class MaskSync(object):
    """Class for fetch and sync bans of any channel and mode."""
    __name__ = ''
    _hide_msg = False

    _hook_mask = ''
    _hook_end = ''

    # freenode new signals for list quiet messages
    _hook_quiet_mask = ''
    _hook_quiet_end = ''

    # sync queue stuff
    queue = []
    _maskbuffer = CaseInsensibleDefaultDict(list)
    _callback = CaseInsensibleDict()

    def hook(self):
        # 367 - ban mask
        # 368 - end of ban list
        # 728 - quiet mask
        # 729 - end of quiet list
        self.unhook()
        self._hook_mask = \
                weechat.hook_modifier('irc_in_367', callback(self._maskCallback), '')
        self._hook_end = \
                weechat.hook_modifier('irc_in_368', callback(self._endCallback), '')
        self._hook_quiet_mask = \
                weechat.hook_modifier('irc_in_728', callback(self._maskCallback), '')
        self._hook_quiet_end = \
                weechat.hook_modifier('irc_in_729', callback(self._endCallback), '')

    def unhook(self):
        for hook in ('_hook_mask',
                     '_hook_end',
                     '_hook_quiet_mask',
                     '_hook_quiet_end'):
            attr = getattr(self, hook)
            if attr:
                weechat.unhook(attr)
                setattr(self, hook, '')

    def fetch(self, server, channel, mode, callback=None):
        """Fetches masks for a given server and channel."""
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        if not buffer or not weechat.info_get('irc_is_channel', channel):
            # invalid server or channel
            return

        # check modes
        if mode not in supported_modes(server):
            return
        maskCache = modeCache[mode]
        key = (server, channel)
        # check the last time we did this
        try:
            masklist = maskCache[key]
            if (now() - masklist.synced) < 60:
                # don't fetch again
                return
        except KeyError:
            pass

        if not self.queue:
            self.queue.append((server, channel, mode))
            self._fetch(server, channel, mode)
        elif (server, channel, mode) not in self.queue:
            self.queue.append((server, channel, mode))

        if callback:
            self._callback[server, channel] = callback

    def _fetch(self, server, channel, mode):
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        if not buffer:
            return
        cmd = '/mode %s %s' %(channel, mode)
        self._hide_msg = True
        weechat_command(buffer, cmd)

    def _maskCallback(self, data, modifier, modifier_data, string):
        """callback for store a single mask."""
        #debug("MASK %s: %s %s", modifier, modifier_data, string)
        args = string.split()
        if self.queue:
            server, channel, _ = self.queue[0]
        else:
            server, channel = modifier_data, args[3]

        if modifier == 'irc_in_367':
            try:
                mask, op, date = args[4:]
            except IndexError:
                mask = args[4]
                op = date = None
        elif modifier == 'irc_in_728':
            mask, op, date = args[5:]

        # store temporally until "end list" msg
        self._maskbuffer[server, channel].append((mask, op, date))
        if self._hide_msg:
            string = ''
        return string

    def _endCallback(self, data, modifier, modifier_data, string):
        """callback for end of channel's mask list."""
        #debug("MASK END %s: %s %s", modifier, modifier_data, string)
        if self.queue:
            server, channel, mode = self.queue.pop(0)
        else:
            args = string.split()
            server, channel = modifier_data, args[3]
            if modifier == 'irc_in_368':
                mode = args[7]
            elif modifier == 'irc_in_729':
                mode = args[4]
            else:
                return string

        maskCache = modeCache[mode]

        # delete old masks in cache
        if (server, channel) in maskCache:
            masklist = maskCache[server, channel]
            banmasks = [ L[0] for L in self._maskbuffer[server, channel] ]
            for mask in masklist.keys():
                if mask not in banmasks:
                    del masklist[mask]

        for banmask, op, date in self._maskbuffer[server, channel]:
            maskCache.add(server, channel, banmask, operator=op, date=date)
        del self._maskbuffer[server, channel]
        try:
            maskList = maskCache[server, channel]
        except KeyError:
            maskList = maskCache[server, channel] = MaskList(server, channel)
        maskList.synced = now()

        # run hooked functions if any
        if (server, channel) in self._callback:
            self._callback[server, channel]()
            del self._callback[server, channel]

        if self._hide_msg:
            string = ''
        if self.queue:
            next = self.queue[0]
            self._fetch(*next)
        else:
            assert not self._maskbuffer, "mask buffer not empty: %s" % self._maskbuffer.keys()
            self._hide_msg = False
        return string

maskSync = MaskSync()

# -----------------------------------------------------------------------------
# User cache

class UserObject(object):
    def __init__(self, nick, hostmask=None):
        self.nick = nick
        if hostmask:
            self._hostmask = [ hostmask ]
        else:
            self._hostmask = []
        self.seen = now()
        self._channels = 0

    @property
    def hostmask(self):
        try:
            return self._hostmask[-1]
        except IndexError:
            return ''

    def update(self, hostmask=None):
        if hostmask and hostmask != self.hostmask:
            if hostmask in self._hostmask:
                del self._hostmask[self._hostmask.index(hostmask)]
            self._hostmask.append(hostmask)
        self.seen = now()

    def __len__(self):
        return len(self.hostmask)

    def __repr__(self):
        return '<UserObject(%s)>' %(self.hostmask or self.nick)

class ServerUserList(CaseInsensibleDict):
    def __init__(self, server):
        self.server = server
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        self.irc = IrcCommands(buffer)
        self._purge_time = 3600*4 # 4 hours

    def getHostmask(self, nick):
        user = self[nick]
        return user.hostmask

    def purge(self):
        """Purge old nicks"""
        n = now()
        for nick, user in self.items():
            if user._channels < 1 and (n - user.seen) > self._purge_time:
                #debug('purging old user: %s' % nick)
                del self[nick]

class UserList(ServerUserList):
    def __init__(self, server, channel):
        self.server = server
        self.channel = channel
        self._purge_list = CaseInsensibleDict()
        self._purge_time = 3600*2 # 2 hours

    def __setitem__(self, nick, user):
        #debug('%s %s: join, %s', self.server, self.channel, nick)
        if nick not in self:
            user._channels += 1
        if nick in self._purge_list:
            #debug(' - removed from purge list')
            del self._purge_list[nick]
        ServerUserList.__setitem__(self, nick, user)

    def part(self, nick):
        try:
            #debug('%s %s: part, %s', self.server, self.channel, nick)
            user = self[nick]
            self._purge_list[nick] = user
        except KeyError:
            pass

    def values(self):
        if not all(ServerUserList.values(self)):
            userCache.who(self.server, self.channel)
        return sorted(ServerUserList.values(self), key=lambda x:x.seen, reverse=True)

    def hostmasks(self, sorted=False, all=False):
        if sorted:
            users = self.values()
        else:
            users = ServerUserList.values(self)
        if all:
            # return all known hostmasks
            return [ hostmask for user in users for hostmask in user._hostmask ]
        else:
            # only current hostmasks
            return [ user.hostmask for user in users if user._hostmask ]

    def nicks(self, *args, **kwargs):
#        if not all(self.itervalues()):
#            userCache.who(self.server, self.channel)
        L = list(self.items())
        L.sort(key=lambda x:x[1].seen)
        return reversed([x[0] for x in L])

    def getHostmask(self, nick):
        try:
            user = self[nick]
        except KeyError:
            user = userCache[self.server][nick]
        return user.hostmask

    def purge(self):
        """Purge old nicks"""
        n = now()
        for nick, user in self._purge_list.items():
            if (n - user.seen) > self._purge_time:
                #debug('%s %s: forgeting about %s', self.server, self.channel, nick)
                user._channels -= 1
                try:
                    del self._purge_list[nick]
                    del self[nick]
                except KeyError:
                    pass

class UserCache(ServerChannelDict):
    __name__ = ''
    servercache = CaseInsensibleDict()
    _hook_who = _hook_who_end = None
    _channels = CaseInsensibleSet()

    def generateCache(self, server, channel):
        debug('* building cache: %s %s', server, channel)
        users = UserList(server, channel)
        try:
            infolist = nick_infolist(server, channel)
        except:
            # better to fail silently
            #debug('invalid buffer')
            return users

        while infolist.next():
            nick = infolist['name']
            host = infolist['host']
            if host:
                hostmask = '%s!%s' %(nick, host)
            else:
                hostmask = ''
            user = self.remember(server, nick, hostmask)
            users[nick] = user
        self[server, channel] = users
        debug("new cache of %s users", len(users))
        return users

    def remember(self, server, nick, hostmask):
        cache = self[server]
        try:
            user = cache[nick]
            if hostmask:
                user.update(hostmask)
        except KeyError:
            #debug("%s: new user %s %s", server, nick, hostmask)
            user = UserObject(nick, hostmask)
            cache[nick] = user
        return user

    def __getitem__(self, k):
        if isinstance(k, tuple):
            try:
                return ServerChannelDict.__getitem__(self, k)
            except KeyError:
                return self.generateCache(*k)
        elif isinstance(k, str):
            try:
                return self.servercache[k]
            except KeyError:
                cache = self.servercache[k] = ServerUserList(k)
                return cache

    def __delitem__(self, k):
        # when we delete a channel, we need to reduce user._channels count
        # so they can be purged later.
        #debug('forgeting about %s', k)
        for user in self[k].values():
            user._channels -= 1
        ServerChannelDict.__delitem__(self, k)

    def getHostmask(self, nick, server, channel=None):
        """Returns hostmask of nick."""
        if channel:
            return self[server, channel].getHostmask(nick)
        return self[server].getHostmask(nick)

    def who(self, server, channel):
        if self._hook_who:
            return

        if (server, channel) in self._channels:
            return

        self._channels.add((server, channel))

        key = ('%s.%s' %(server, channel)).lower()
        self._hook_who = weechat.hook_modifier(
                'irc_in_352', callback(self._whoCallback), key)
        self._hook_who_end = weechat.hook_modifier(
                'irc_in_315', callback(self._endWhoCallback), key)

        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        weechat_command(buffer, '/who %s' % channel)

    def _whoCallback(self, data, modifier, modifier_data, string):
        #debug('%s %s %s', modifier, modifier_data, string)
        args = string.split()
        server, channel = modifier_data, args[3]
        key = ('%s.%s' %(server, channel)).lower()
        if key != data:
            return string

        nick, user, host = args[7], args[4], args[5]
        hostmask = '%s!%s@%s' %(nick, user, host)
        debug('WHO: %s', hostmask)
        self.remember(server, nick, hostmask)
        return ''

    def _endWhoCallback(self, data, modifier, modifier_data, string):
        args = string.split()
        server, channel = modifier_data, args[3]
        key = ('%s.%s' %(server, channel)).lower()
        if key != data:
            return string

        debug('WHO: end.')
        weechat.unhook(self._hook_who)
        weechat.unhook(self._hook_who_end)
        self._hook_who = self._hook_who_end = None
        return ''

    def purge(self):
        ServerChannelDict.purge(self)
        for cache in self.servercache.values():
            cache.purge()

userCache = UserCache()

# -----------------------------------------------------------------------------
# Chanop Command Classes

# Base classes for chanop commands
class CommandChanop(Command, ChanopBuffers):
    """Base class for our commands, with config and general functions."""
    infolist = None

    def parser(self, args):
        if not args:
            weechat_command('', '/help %s' % self.command)
            raise NoArguments
        self.setup(self.buffer)

    def execute(self):
        self.users = userCache[self.server, self.channel]
        try:
            self.execute_chanop()   # call our command and queue messages for WeeChat
            self.irc.run()          # run queued messages
        except InvalidIRCBuffer as e:
            error('Not in a IRC channel (%s)' % e)
            self.irc.clear()
        self.infolist = None    # free irc_nick infolist

    def execute_chanop(self):
        pass

    def nick_infolist(self):
        # reuse the same infolist instead of creating it many times
        if not self.infolist:
            self.infolist = nick_infolist(self.server, self.channel)
        else:
            self.infolist.reset()
        return self.infolist

    def has_op(self, nick):
        nicks = self.nick_infolist()
        while nicks.next():
            if nicks['name'] == nick:
                return '@' in nicks['prefixes']

    def has_voice(self, nick):
        nicks = self.nick_infolist()
        while nicks.next():
            if nicks['name'] == nick:
                return '+' in nicks['prefixes']

    def isUser(self, nick):
        return nick in self.users

    def inChannel(self, nick):
        return CaseInsensibleString(nick) in [ nick['name'] for nick in self.nick_infolist() ]

    def getHostmask(self, name):
        try:
            hostmask = self.users.getHostmask(name)
            if not hostmask:
                self.irc.Userhost(name)
                user = userCache[self.server][name]
                return lambda: user.hostmask or user.nick
            return hostmask
        except KeyError:
            pass

    def set_mode(self, *nicks):
        mode = self.prefix + self.mode
        for nick in nicks:
            self.irc.Mode(mode, nick)

class CommandWithOp(CommandChanop):
    """Base class for all the commands that requires op status for work."""
    _enable_deopNow = True
    deop_delay = 0

    def __init__(self, *args, **kwargs):
        CommandChanop.__init__(self, *args, **kwargs)
        # update help so it adds --deop option
        if self._enable_deopNow:
            if self.usage:
                self.usage += " "
            if self.help:
                self.help += "\n"
            self.usage += "[--deop]"
            self.help += " -o --deop: Forces deop immediately, without configured delay"\
                         " (option must be the last argument)."

    def setup(self, buffer):
        self.deopNow = False
        CommandChanop.setup(self, buffer)

    def parser(self, args):
        CommandChanop.parser(self, args)
        args = args.split()
        if self._enable_deopNow and args[-1] in ('-o', '--deop'):
            self.deopNow = True
            del args[-1]
            self.args = ' '.join(args)
        if not self.args:
            raise NoArguments

    def execute_chanop(self, *args):
        self.execute_op(*args)

        if not self.irc.commands:
            # nothing in queue, no reason to op.
            return

        self.irc.Op()
        if (self.autodeop and self.get_config_boolean('autodeop')) or self.deopNow:
            if self.deopNow:
                delay = self.deop_delay
            else:
                delay = self.get_config_int('autodeop_delay')
            if delay > 0:
                if self.deopHook:
                    weechat.unhook(self.deopHook)
                self.vars.deopHook = weechat.hook_timer(delay * 1000, 0, 1,
                        callback(self.deopCallback), self.buffer)
            elif self.irc.commands: # only Deop if there are msgs in queue
                self.irc.Deop()

    def execute_op(self, *args):
        """Commands in this method will be run with op privileges."""
        pass

    def deopCallback(self, buffer, count):
        #debug('deop %s', buffer)
        vars = self.varsOf(buffer)
        if vars.autodeop:
            if vars.irc.commands:
                # there are commands in queue yet, wait some more
                vars.deopHook = weechat.hook_timer(1000, 0, 1,
                        callback(self.deopCallback), buffer)
                return WEECHAT_RC_OK
            else:
                vars.irc.Deop()
                vars.irc.run()
        vars.deopHook = None
        return WEECHAT_RC_OK

# Chanop commands
class Op(CommandChanop):
    description, usage = "Request operator privileges or give it to users.", "[nick [nick ... ]]",
    help = \
    "The command used for ask op is defined globally in plugins.var.python.%(name)s.op_command\n"\
    "It can be defined per server or per channel in:\n"\
    " plugins.var.python.%(name)s.op_command.<server>\n"\
    " plugins.var.python.%(name)s.op_command.<server>.<#channel>\n"\
    "\n"\
    "After using this command, you won't be autodeoped." %{'name':SCRIPT_NAME}
    command = 'oop'
    completion = '%(nicks)'

    prefix = '+'
    mode = 'o'

    def parser(self, args):
        # dont show /help if no args
        self.setup(self.buffer)

    def execute_chanop(self):
        self.irc.Op()
        # /oop was used, we assume that the user wants
        # to stay opped permanently
        self.vars.autodeop = False
        if self.args:
            for nick in self.args.split():
                if self.inChannel(nick) and not self.has_op(nick):
                    self.set_mode(nick)

class Deop(Op, CommandWithOp):
    description, usage, help = \
    "Removes operator privileges from yourself or users.", "[nick [nick ... ]]", ""
    command = 'odeop'
    completion = '%(nicks)'

    prefix = '-'
    _enable_deopNow = False

    def execute_chanop(self):
        if self.args:
            nicks = []
            for nick in self.args.split():
                if self.inChannel(nick) and self.has_op(nick):
                    nicks.append(nick)
            if nicks:
                CommandWithOp.execute_chanop(self, nicks)
        else:
            self.vars.autodeop = True
            if self.has_op(self.nick):
                self.irc.Deop()

    def execute_op(self, nicks):
        self.set_mode(*nicks)

class Kick(CommandWithOp):
    description, usage = "Kick nick.", "<nick> [<reason>]"
    help = \
    "On freenode, you can set this command to use /remove instead of /kick, users"\
    " will see it as if the user parted and it can bypass autojoin-on-kick scripts."\
    " See plugins.var.python.%s.enable_remove config option." %SCRIPT_NAME
    command = 'okick'
    completion = '%(nicks)'

    def execute_op(self):
        nick, s, reason = self.args.partition(' ')
        if self.inChannel(nick):
            self.irc.Kick(nick, reason)
        else:
            say("Nick not in %s (%s)" % (self.channel, nick), self.buffer)
            self.irc.clear()

class MultiKick(Kick):
    description = "Kick one or more nicks."
    usage = "<nick> [<nick> ... ] [:] [<reason>]"
    help = Kick.help + "\n\n"\
    "Note: Is not needed, but use ':' as a separator between nicks and "\
    "the reason. Otherwise, if there's a nick in the channel matching the "\
    "first word in reason it will be kicked."
    completion = '%(nicks)|%*'

    def execute_op(self):
        args = self.args.split()
        nicks = []
        nicks_parted = []
        #debug('multikick: %s' %str(args))
        while(args):
            nick = args[0]
            if nick[0] == ':' or not self.isUser(nick):
                break
            nick = args.pop(0)
            if self.inChannel(nick):
                nicks.append(nick)
            else:
                nicks_parted.append(nick)

        #debug('multikick: %s, %s' %(nicks, args))
        reason = ' '.join(args).lstrip(':')
        if nicks_parted:
            say("Nick(s) not in %s (%s)" % (self.channel, ', '.join(nicks_parted)), self.buffer)
        elif not nicks:
            say("Unknown nick (%s)" % nick, self.buffer)
        if nicks:
            for nick in nicks:
                self.irc.Kick(nick, reason)
        else:
            self.irc.clear()

ban_help = \
"Mask options:\n"\
" -h  --host: Match hostname (*!*@host)\n"\
" -n  --nick: Match nick     (nick!*@*)\n"\
" -u  --user: Match username (*!user@*)\n"\
" -e --exact: Use exact hostmask.\n"\
"\n"\
"If no mask options are supplied, configured defaults are used.\n"\
"\n"\
"Completer:\n"\
"%(script)s will attempt to guess a complete banmask from current\n"\
"users when using <tab> in an incomplete banmask. Using <tab> in a\n"\
"complete banmask will generate variations of it. \n"\
"\n"\
"Examples:\n"\
" /%(cmd)s somebody --user --host\n"\
"   will ban with *!user@hostname mask.\n"\
" /%(cmd)s nick!*@<tab>\n"\
"   will autocomple with 'nick!*@host'.\n"\
" /%(cmd)s nick!*@*<tab>\n"\
"   will cycle through different banmask variations for the same user.\n"

class Ban(CommandWithOp):
    description = "Ban user or hostmask."
    usage = \
    "<nick|mask> [<nick|mask> ... ] [ [--host] [--user] [--nick] | --exact ]"
    command = 'oban'
    help = ban_help % {'script': SCRIPT_NAME, 'cmd': command}
    completion = '%(chanop_nicks)|%(chanop_ban_mask)|%*'

    banmask = []
    mode = 'b'
    prefix = '+'

    def __init__(self):
        self.maskCache = modeCache[self.mode]
        CommandWithOp.__init__(self)

    def parser(self, args):
        if not args:
            showBans.callback(self.data, self.buffer, self.mode)
            raise NoArguments
        CommandWithOp.parser(self, args)
        self._parser(self.args)

    def _parser(self, args):
        args = args.split()
        try:
            (opts, args) = getopt.gnu_getopt(args, 'hune', ('host', 'user', 'nick', 'exact'))
        except getopt.GetoptError as e:
            raise ArgumentError(e)
        self.banmask = []
        for k, v in opts:
            if k in ('-h', '--host'):
                self.banmask.append('host')
            elif k in ('-u', '--user'):
                self.banmask.append('user')
            elif k in ('-n', '--nick'):
                self.banmask.append('nick')
            elif k in ('-e', '--exact'):
                self.banmask = ['exact']
                break
        if not self.banmask:
            self.banmask = self.get_default_banmask()
        self.args = ' '.join(args)

    def get_default_banmask(self):
        return get_config_banmask(get_function=self.get_config)

    def make_banmask(self, hostmask):
        assert self.banmask
        template = self.banmask

        def banmask(s):
            if not is_hostmask(s):
                return s
            if 'exact' in template:
                return s
            nick = user = host = '*'
            if 'nick' in template:
                nick = get_nick(s)
            if 'user' in template:
                user = get_user(s)
            if 'host' in template:
                host = get_host(s)
                # check for freenode's webchat, and use a better mask.
                if host.startswith('gateway/web/freenode'):
                    ip = host.partition('.')[2]
                    if is_ip(ip):
                        host = '*%s' % ip
            s = '%s!%s@%s' %(nick, user, host)
            assert is_hostmask(s), "Invalid hostmask: %s" % s
            return s

        if callable(hostmask):
            return lambda: banmask(hostmask())
        return banmask(hostmask)

    def execute_op(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            if is_nick(arg):
                hostmask = self.getHostmask(arg)
                if not hostmask:
                    say("Unknown nick (%s)" % arg, self.buffer)
                    continue
                mask = self.make_banmask(hostmask)
                if self.has_voice(arg):
                    self.irc.Devoice(arg)
            else:
                # probably an extban
                mask = arg
            banmasks.append(mask)
        banmasks = set(banmasks) # remove duplicates
        self.ban(*banmasks)

    def mode_is_supported(self):
        return self.mode in supported_modes(self.server)

    def ban(self, *banmasks, **kwargs):
        if self.mode != 'b' and not self.mode_is_supported():
            error("%s doesn't seem to support channel mode '%s', using regular ban." %(self.server,
                self.mode))
            mode = 'b'
        else:
            mode = self.mode
        mode = self.prefix + mode
        for mask in banmasks:
            self.irc.Mode(mode, mask, **kwargs)

class UnBan(Ban):
    description, usage = "Remove bans.", "<nick|mask> [<nick|mask> ... ]"
    command = 'ounban'
    help = \
    "Autocompletion will use channel's bans, patterns allowed for autocomplete multiple"\
    " bans.\n"\
    "\n"\
    "Example:\n"\
    "/%(cmd)s *192.168*<tab>\n"\
    "  Will autocomplete with all bans matching *192.168*" %{'cmd':command}
    completion = '%(chanop_unban_mask)|%(chanop_nicks)|%*'
    prefix = '-'

    def search_masks(self, hostmask, **kwargs):
        try:
            masklist = self.maskCache[self.server, self.channel]
        except KeyError:
            return []

        if callable(hostmask):
            def banmask():
                L = masklist.search(hostmask(), **kwargs)
                if L: return L[0]

            return [ banmask ]
        return masklist.search(hostmask, **kwargs)

    def execute_op(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            if is_hostmask(arg):
                banmasks.extend(self.search_masks(arg))
            elif is_nick(arg):
                hostmask = self.getHostmask(arg)
                if hostmask:
                    banmasks.extend(self.search_masks(hostmask, reverseMatch=True))
                else:
                    # nick unknown to chanop
                    say("Unknown nick (%s)" % arg, self.buffer)
            else:
                banmasks.append(arg)
        self.ban(*banmasks)

class Quiet(Ban):
    description = "Silence user or hostmask."
    command = 'oquiet'
    help = "This command is only for networks that support channel mode 'q'.\n\n" \
            + ban_help % {'script': SCRIPT_NAME, 'cmd': command}
    completion = '%(chanop_nicks)|%(chanop_ban_mask)|%*'

    mode = 'q'

class UnQuiet(UnBan):
    command = 'ounquiet'
    description = "Remove quiets."
    help = "Works exactly like /ounban, but only for quiets. See /help ounban"
    completion = '%(chanop_unquiet_mask)|%(chanop_nicks)|%*'

    mode = 'q'

class BanKick(Ban, Kick):
    description = "Bankicks nick."
    usage = "<nick> [<reason>] [ [--host] [--user] [--nick] | --exact ]"
    help = "Combines /oban and /okick commands. See /help oban and /help okick."
    command = 'obankick'
    completion = '%(chanop_nicks)'
    deop_delay = 2

    def execute_op(self):
        nick, s, reason = self.args.partition(' ')
        if not self.isUser(nick):
            say("Unknown nick (%s)" % nick, self.buffer)
            self.irc.clear()
            return

        hostmask = self.getHostmask(nick)
        # we already checked that nick is valid, so hostmask shouldn't be None
        banmask = self.make_banmask(hostmask)
        self.ban(banmask)
        if self.inChannel(nick):
            self.irc.Kick(nick, reason, wait=1)

class MultiBanKick(BanKick):
    description = "Bankicks one or more nicks."
    usage = \
    "<nick> [<nick> ... ] [:] [<reason>] [ [--host)] [--user] [--nick] | --exact ]"
    completion = '%(chanop_nicks)|%*'

    def execute_op(self):
        args = self.args.split()
        nicks = []
        while(args):
            nick = args[0]
            if nick[0] == ':' or not self.isUser(nick):
                break
            nicks.append(args.pop(0))
        reason = ' '.join(args).lstrip(':')
        if not nicks:
            say("Unknown nick (%s)" % nick, self.buffer)
            self.irc.clear()
            return

        for nick in nicks:
            hostmask = self.getHostmask(nick)
            banmask = self.make_banmask(hostmask)
            self.ban(banmask)

        self.deop_delay = 1
        for nick in nicks:
            if self.inChannel(nick):
                self.deop_delay += 1
                self.irc.Kick(nick, reason, wait=1)

class Topic(CommandWithOp):
    description, usage = "Changes channel topic.", "[-delete | topic]"
    help = "Clear topic if '-delete' is the new topic."
    command = 'otopic'
    completion = '%(irc_channel_topic)||-delete'

    def execute_op(self):
        self.irc.queue(Message('/topic %s' %self.args))

class Voice(CommandWithOp):
    description, usage, help = "Gives voice to somebody.", "nick [nick ... ]", ""
    command = 'ovoice'
    completion = '%(nicks)|%*'

    prefix = '+'
    mode = 'v'

    def execute_op(self):
        for nick in self.args.split():
            if self.inChannel(nick) and not self.has_voice(nick):
                self.set_mode(nick)

class DeVoice(Voice):
    description = "Removes voice from somebody."
    command = 'odevoice'

    prefix = '-'

    def has_voice(self, nick):
        return not Voice.has_voice(self, nick)

class Mode(CommandWithOp):
    description, usage, help = "Changes channel modes.", "<channel modes>", ""
    command = 'omode'

    def execute_op(self):
        args = self.args.split()
        modes = args.pop(0)
        L = []
        p = ''
        for c in modes:
            if c in '+-':
                p = c
            elif args:
                L.append((p + c, args.pop(0)))
            else:
                L.append((p + c, None))
        if not L:
            return

        for mode, arg in L:
            self.irc.Mode(mode, arg)

class ShowBans(CommandChanop):
    description, usage, help = "Lists bans or quiets of a channel.", "(bans|quiets) [channel]", ""
    command = 'olist'
    completion = 'bans|quiets %(irc_server_channels)'
    showbuffer = ''

    padding = 40

    def parser(self, args):
        server = weechat.buffer_get_string(self.buffer, 'localvar_server')
        channel = weechat.buffer_get_string(self.buffer, 'localvar_channel')
        if server:
            self.server = server
        if channel:
            self.channel = channel
        type, _, args = args.partition(' ')
        if not type:
            raise ValueError('missing argument')
        try:
            mode = modeCache.map[type]
        except KeyError:
            raise ValueError('incorrect argument')

        self.mode = mode
        # fix self.type so is "readable" (ie, 'bans' instead of 'b')
        if mode == 'b':
            self.type = 'bans'
        elif mode == 'q':
            self.type = 'quiets'
        args = args.strip()
        if args:
            self.channel = args

    def get_buffer(self):
        if self.showbuffer:
            return self.showbuffer

        buffer = weechat.buffer_search('python', SCRIPT_NAME)
        if not buffer:
            buffer = weechat.buffer_new(SCRIPT_NAME, '', '', '', '')
            weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
            weechat.buffer_set(buffer, 'time_for_each_line', '0')
        self.showbuffer = buffer
        return buffer

    def prnt(self, s):
        weechat.prnt(self.get_buffer(), s)

    def prnt_ban(self, banmask, op, when, hostmask=None):
        padding = self.padding - len(banmask)
        if padding < 0:
            padding = 0
        self.prnt('%s%s%s %sset by %s%s%s %s' %(color_mask,
                                                banmask,
                                                color_reset,
                                                '.'*padding,
                                                color_chat_nick,
                                                op,
                                                color_reset,
                                                self.formatTime(when)))
        if hostmask:
            hostmasks = ' '.join(hostmask)
            self.prnt('  %s%s' % (color_chat_host, hostmasks))

    def clear(self):
        b = self.get_buffer()
        weechat.buffer_clear(b)
        weechat.buffer_set(b, 'display', '1')
        weechat.buffer_set(b, 'title', '%s' %SCRIPT_NAME)

    def set_title(self, s):
        weechat.buffer_set(self.get_buffer(), 'title', s)

    def formatTime(self, t):
        t = now() - int(t)
        elapsed = time_elapsed(t, level=3)
        return '%s ago' %elapsed

    def execute(self):
        self.showbuffer = ''
        if self.mode not in supported_modes(self.server):
            self.clear()
            self.prnt("\n%sNetwork '%s' doesn't support %s" % (color_channel,
                                                               self.server,
                                                               self.type))
            return

        maskCache = modeCache[self.mode]
        key = (self.server, self.channel)
        try:
            masklist = maskCache[key]
        except KeyError:
            if not (weechat.info_get('irc_is_channel', key[1]) and self.server):
                error("Command /%s must be used in an IRC buffer." % self.command)
                return

            masklist = None
        self.clear()
        mask_count = 0
        if masklist:
            mask_count = len(masklist)
            self.prnt('\n%s[%s %s]' %(color_channel, key[0], key[1]))
            masks = [ m for m in masklist.values() ]
            masks.sort(key=lambda x: x.date)
            for ban in masks:
                op = self.server
                if ban.operator:
                    try:
                        op = get_nick(ban.operator)
                    except:
                        pass
                self.prnt_ban(ban.mask, op, ban.date, ban.hostmask)
        else:
            self.prnt('No known %s for %s.%s' %(self.type, key[0], key[1]))
        if masklist is None or not masklist.synced:
            self.prnt("\n%sList not synced, please wait ..." %color_channel)
            maskSync.fetch(key[0], key[1], self.mode, lambda: self.execute())
        self.set_title('List of %s known by chanop in %s.%s (total: %s)' %(self.type,
                                                                           key[0],
                                                                           key[1],
                                                                           mask_count))

# -----------------------------------------------------------------------------
# Script callbacks

# Decorators
def signal_parse(f):
    @catchExceptions
    def decorator(data, signal, signal_data):
        server = signal[:signal.find(',')]
        channel = signal_data.split()[2]
        if channel[0] == ':':
            channel = channel[1:]
        if (server, channel) not in chanopChannels:
            # signals only processed for channels in watchlist
            return WEECHAT_RC_OK
        nick = get_nick(signal_data)
        hostmask = signal_data[1:signal_data.find(' ')]
        #debug('%s %s', signal, signal_data)
        return f(server, channel, nick, hostmask, signal_data)
    decorator.func_name = f.func_name
    return decorator

def signal_parse_no_channel(f):
    @catchExceptions
    def decorator(data, signal, signal_data):
        server = signal[:signal.find(',')]
        nick = get_nick(signal_data)
        channels = userCache.getChannels(server, nick)
        if channels:
            hostmask = signal_data[1:signal_data.find(' ')]
            #debug('%s %s', signal, signal_data)
            return f(server, channels, nick, hostmask, signal_data)
        return WEECHAT_RC_OK
    decorator.func_name = f.func_name
    return decorator

isupport = {}
def get_isupport_value(server, feature):
    #debug('isupport %s %s', server, feature)
    try:
        return isupport[server][feature]
    except KeyError:
        if not server:
            return ''
        elif server not in isupport:
            isupport[server] = {}
        v = weechat.info_get('irc_server_isupport_value', '%s,%s' %(server, feature.upper()))
        if v:
            isupport[server][feature] = v
        else:
            # old api
            v = weechat.config_get_plugin('isupport.%s.%s' %(server, feature))
            if not v:
                # lets do a /VERSION (it should be done only once.)
                if '/VERSION' in isupport[server]:
                    return ''
                buffer = weechat.buffer_search('irc', 'server.%s' %server)
                weechat_command(buffer, '/VERSION')
                isupport[server]['/VERSION'] = True
        return v

_supported_modes = set('bq') # the script only support b,q masks
def supported_modes(server):
    """Returns modes supported by server."""
    modes = get_isupport_value(server, 'chanmodes')
    if not modes:
        return 'b'
    modes = modes.partition(',')[0] # we only care about the first type
    modes = ''.join(_supported_modes.intersection(modes))
    return modes

def supported_maxmodes(server):
    """Returns max modes number supported by server."""
    max = get_isupport_value(server, 'modes')
    try:
        max = int(max)
        if max <= 0:
            max = 1
    except ValueError:
        return 1
    return max

def isupport_cb(data, signal, signal_data):
    """Callback used for catch isupport msg if current version of WeeChat doesn't
    support it."""
    data = signal_data.split(' ', 3)[-1]
    data, s, s = data.rpartition(' :')
    data = data.split()
    server = signal.partition(',')[0]
    d = {}
    #debug(data)
    for s in data:
        if '=' in s:
            k, v = s.split('=')
        else:
            k, v = s, True
        k = k.lower()
        if k in ('chanmodes', 'modes', 'prefix'):
            config = 'isupport.%s.%s' %(server, k)
            weechat.config_set_plugin(config, v)
            d[k] = v
    isupport[server] = d
    return WEECHAT_RC_OK

def print_affected_users(buffer, *hostmasks):
    """Print a list of users, max 8 hostmasks"""
    def format_user(hostmask):
        nick, host = hostmask.split('!', 1)
        return '%s%s%s(%s%s%s)' %(color_chat_nick,
                                  nick,
                                  color_delimiter,
                                  color_chat_host,
                                  host,
                                  color_delimiter)

    max = 8
    count = len(hostmasks)
    if count > max:
        hostmasks = hostmasks[:max]
    say('Affects (%s): %s%s' %(count, ' '.join(map(format_user,
        hostmasks)), count > max and ' %s...' %color_reset or ''), buffer=buffer)

# Masks list tracking
@signal_parse
def mode_cb(server, channel, nick, opHostmask, signal_data):
    """Keep the banmask list updated when somebody changes modes"""
    #:m4v!~znc@unaffiliated/m4v MODE #test -bo+v asd!*@* m4v dude
    pair = signal_data.split(' ', 4)[3:]
    if len(pair) != 2:
        # modes without argument, not interesting.
        return WEECHAT_RC_OK
    modes, args = pair

    # check if there are interesting modes
    servermodes = supported_modes(server)
    s = modes.translate(chars, '+-') # remove + and -
    if not set(servermodes).intersection(s):
        return WEECHAT_RC_OK

    # check if channel is in watchlist
    key = (server, channel)
    allkeys = CaseInsensibleSet()
    for maskCache in modeCache.values():
        allkeys.update(maskCache)
        if key not in allkeys and key not in chanopChannels:
            # from a channel we're not tracking
            return WEECHAT_RC_OK

    prefix = get_isupport_value(server, 'prefix')
    chanmodes = get_isupport_value(server, 'chanmodes')
    if not prefix or not chanmodes:
        # we don't have ISUPPORT data, can't continue
        return WEECHAT_RC_OK

    # split chanmodes into tuples like ('+', 'b', 'asd!*@*')
    action = ''
    chanmode_list = []
    args = args.split()

    # user channel mode, such as +v or +o, get only the letters and not the prefixes
    usermodes = ''.join(map(lambda c: c.isalpha() and c or '', prefix))
    chanmodes = chanmodes.split(',')
    # modes not supported by script, like +e +I
    notsupported = chanmodes[0].translate(chars, servermodes)
    modes_with_args = chanmodes[1] + usermodes + notsupported
    modes_with_args_when_set = chanmodes[2]
    for c in modes:
        if c in '+-':
            action = c
        elif c in servermodes:
            chanmode_list.append((action, c, args.pop(0)))
        elif c in modes_with_args:
            del args[0]
        elif c in modes_with_args_when_set and action == '+':
            del args[0]

    affected_users = []
    # update masks
    for action, mode, mask in chanmode_list:
        debug('MODE: %s%s %s %s', action, mode, mask, opHostmask)
        if action == '+':
            hostmask = hostmask_match_list(mask, userCache[key].hostmasks())
            if hostmask:
                affected_users.extend(hostmask)
            if mask != '*!*@*':
                # sending this signal with a *!*@* is annoying
                weechat.hook_signal_send("%s,chanop_mode_%s" % (server, mode),
                                         weechat.WEECHAT_HOOK_SIGNAL_STRING,
                                         "%s %s %s %s" % (opHostmask, channel,
                                                          mask, ','.join(hostmask)))
            modeCache.add(server, channel, mode, mask, operator=opHostmask, hostmask=hostmask)
        elif action == '-':
            modeCache.remove(server, channel, mode, mask)

    if affected_users and get_config_boolean('display_affected',
            get_function=get_config_specific, server=server, channel=channel):
        buffer = weechat.buffer_search('irc', '%s.%s' %key)
        print_affected_users(buffer, *set(affected_users))
    return WEECHAT_RC_OK

# User cache
@signal_parse
def join_cb(server, channel, nick, hostmask, signal_data):
    if weechat.info_get('irc_nick', server) == nick:
        # we're joining the channel, the cache is no longer valid
        #userCache.generateCache(server, channel)
        try:
            del userCache[server, channel]
        except KeyError:
            pass
        return WEECHAT_RC_OK
    user = userCache.remember(server, nick, hostmask)
    userCache[server, channel][nick] = user
    return WEECHAT_RC_OK

@signal_parse
def part_cb(server, channel, nick, hostmask, signal_data):
    userCache.remember(server, nick, hostmask)
    userCache[server, channel].part(nick)
    return WEECHAT_RC_OK

@signal_parse_no_channel
def quit_cb(server, channels, nick, hostmask, signal_data):
    userCache.remember(server, nick, hostmask)
    for channel in channels:
        userCache[server, channel].part(nick)
    return WEECHAT_RC_OK

@signal_parse_no_channel
def nick_cb(server, channels, oldNick, oldHostmask, signal_data):
    newNick = signal_data[signal_data.rfind(' ') + 2:]
    newHostmask = '%s!%s' % (newNick, oldHostmask[oldHostmask.find('!') + 1:])
    userCache.remember(server, oldNick, oldHostmask)
    user = userCache.remember(server, newNick, newHostmask)
    for channel in channels:
        userCache[server, channel].part(oldNick)
        userCache[server, channel][newNick] = user
    return WEECHAT_RC_OK

# Garbage collector
def garbage_collector_cb(data, counter):
    """This takes care of purging users and masks from channels not in watchlist, and
    expired users that parted.
    """
    debug('* flushing caches')
    modeCache.purge()
    userCache.purge()

    if weechat.config_get_plugin('debug'):
        # extra check that everything is right.
        for serv, chan in userCache:
            for nick in [ nick['name'] for nick in nick_infolist(serv, chan) ]:
                if nick not in userCache[serv, chan]:
                    error('User cache out of sync, unknown nick. (%s - %s.%s)' % (nick, serv, chan))

    return WEECHAT_RC_OK

# -----------------------------------------------------------------------------
# Config callbacks

def enable_multi_kick_conf_cb(data, config, value):
    global cmd_kick, cmd_bankick
    cmd_kick.unhook()
    cmd_bankick.unhook()
    if boolDict[value]:
        cmd_kick = MultiKick()
        cmd_bankick = MultiBanKick()
    else:
        cmd_kick = Kick()
        cmd_bankick = BanKick()
    cmd_kick.hook()
    cmd_bankick.hook()
    return WEECHAT_RC_OK

def update_chanop_watchlist_cb(data, config, value):
    #debug('CONFIG: %s' %(' '.join((data, config, value))))
    server = config[config.rfind('.')+1:]
    if value:
        L = value.split(',')
    else:
        L = []
    for serv, chan in list(chanopChannels):
        if serv == server:
            chanopChannels.remove((serv, chan))
    chanopChannels.update([ (server, channel) for channel in L ])
    return WEECHAT_RC_OK

def enable_bar_cb(data, config, value):
    if boolDict[value]:
        chanop_bar.new()
        weechat.bar_item_new('chanop_ban_matches', 'item_ban_matches_cb', '')
        weechat.bar_item_new('chanop_status', 'item_status_cb', '')
        weechat.hook_modifier('input_text_content', 'input_content_cb', '')
    else:
        chanop_bar.remove()
    return WEECHAT_RC_OK

def enable_debug_cb(data, config, value):
    global debug
    if value and boolDict[value]:
        try:
            # custom debug module I use, allows me to inspect script's objects.
            import pybuffer
            debug = pybuffer.debugBuffer(globals(), '%s_debug' % SCRIPT_NAME)
            weechat.buffer_set(debug._getBuffer(), 'localvar_set_no_log', '0')
        except:
            def debug(s, *args):
                if not isinstance(s, str):
                    s = str(s)
                if args:
                    s = s % args
                prnt('', '%s\t%s' % (script_nick, s))
    else:
        try:
            if hasattr(debug, 'close'):
                debug.close()
        except NameError:
            pass

        debug = _no_debug

    return WEECHAT_RC_OK

# -----------------------------------------------------------------------------
# Completers

def cmpl_get_irc_users(f):
    """Check if completion is done in a irc channel, and pass the buffer's user list."""
    @catchExceptions
    def decorator(data, completion_item, buffer, completion):
        key = irc_buffer(buffer)
        if not key:
            return WEECHAT_RC_OK
        users = userCache[key]
        return f(users, data, completion_item, buffer, completion)
    return decorator

def unban_mask_cmpl(mode, completion_item, buffer, completion):
    """Completion for applied banmasks, for commands like /ounban /ounquiet"""
    maskCache = modeCache[mode]
    key = irc_buffer(buffer)
    if not key:
        return WEECHAT_RC_OK
    server, channel = key

    def cmpl_unban(masklist):
        input = weechat.buffer_get_string(buffer, 'input')
        if input[-1] != ' ':
            input, _, pattern = input.rpartition(' ')
        else:
            pattern = ''
        #debug('%s %s', repr(input), repr(pattern))
        if pattern and not is_nick(pattern): # FIXME nick completer interferes.
                                             # NOTE masklist no longer accepts nicks.
            L = masklist.search(pattern)
            #debug('unban pattern %s => %s', pattern, L)
            if L:
                input = '%s %s ' % (input, ' '.join(L))
                weechat.buffer_set(buffer, 'input', input)
                weechat.buffer_set(buffer, 'input_pos', str(len(input)))
                return
        elif not masklist:
            return
        for mask in masklist.keys():
            #debug('unban mask: %s', mask)
            weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_END)

    if key not in maskCache or not maskCache[key].synced:
        # do completion after fetching marks
        if not maskSync.queue:
            def callback():
                masklist = maskCache[key]
                if chanop_bar:
                    global chanop_bar_status
                    if masklist:
                        chanop_bar_status = 'Got %s +%s masks.' % (len(masklist), mode)
                    else:
                        chanop_bar_status = 'No +%s masks found.' % mode
                    chanop_bar.popup()
                    weechat.bar_item_update('chanop_status')
                else:
                    if masklist:
                        say('Got %s +%s masks.' % (len(masklist), mode), buffer)
                    else:
                       say('No +%s masks found.' % mode, buffer)
                cmpl_unban(masklist)

            maskSync.fetch(server, channel, mode, callback)
            if chanop_bar:
                global chanop_bar_status
                chanop_bar_status = 'Fetching +%s masks in %s, please wait...' %(mode, channel)
                weechat.bar_item_update('chanop_status')
                chanop_bar.popup()
            else:
                say('Fetching +%s masks in %s, please wait...' %(mode, channel), buffer)
    else:
        # mask list is up to date, do completion
        cmpl_unban(maskCache[key])
    return WEECHAT_RC_OK

banmask_cmpl_list = []
@cmpl_get_irc_users
def ban_mask_cmpl(users, data, completion_item, buffer, completion):
    """Completion for banmasks, for commands like /oban /oquiet"""
    input = weechat.buffer_get_string(buffer, 'input')
    if input[-1] == ' ':
        # no pattern, return
        return WEECHAT_RC_OK

    input, _, pattern = input.rpartition(' ')

    global banmask_cmpl_list
    if is_hostmask(pattern):
        if not banmask_cmpl_list:
            maskList = pattern_match_list(pattern, users.hostmasks(sorted=True, all=True))
            if maskList:
                banmask_cmpl_list = [ pattern ]

            def add(mask):
                if mask not in banmask_cmpl_list:
                    banmask_cmpl_list.append(mask)

            for mask in maskList:
                #debug('ban_mask_cmpl: Generating variations for %s', mask)
                host = get_host(mask)
                add('*!*@%s' % host)
                add('%s!*@%s' % (get_nick(mask), host))
                if host.startswith('gateway/web/freenode'):
                    ip = host.partition('.')[2]
                    if is_ip(ip):
                        add('*!*@*%s' % ip)
                elif is_ip(host):
                    user = get_user(mask)
                    iprange = host.rsplit('.', 2)[0]
                    add('*!%s@%s.*' % (user, iprange))
                    add('*!*@%s.*' % iprange)
            #debug('ban_mask_cmpl: variations: %s', banmask_cmpl_list)

        if pattern in banmask_cmpl_list:
            i = banmask_cmpl_list.index(pattern) + 1
            if i == len(banmask_cmpl_list):
                i = 0
            mask = banmask_cmpl_list[i]
            input = '%s %s' % (input, mask)
            weechat.buffer_set(buffer, 'input', input)
            weechat.buffer_set(buffer, 'input_pos', str(len(input)))
            return WEECHAT_RC_OK

    banmask_cmpl_list = []

    if pattern[-1] != '*':
        search_pattern = pattern + '*'
    else:
        search_pattern = pattern

    if '@' in pattern:
        # complete *!*@hostname
        prefix = pattern[:pattern.find('@')]
        make_mask = lambda mask: '%s@%s' %(prefix, mask[mask.find('@') + 1:])
        get_list = users.hostmasks
    elif '!' in pattern:
        # complete *!username@*
        prefix = pattern[:pattern.find('!')]
        make_mask = lambda mask: '%s!%s@*' %(prefix, mask[mask.find('!') + 1:mask.find('@')])
        get_list = users.hostmasks
    else:
        # complete nick!*@*
        make_mask = lambda mask: '%s!*@*' %mask
        get_list = users.nicks

    for mask in pattern_match_list(search_pattern, get_list(sorted=True, all=True)):
        mask = make_mask(mask)
        weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_END)
    return WEECHAT_RC_OK

# Completions for nick, user and host parts of a usermask
@cmpl_get_irc_users
def nicks_cmpl(users, data, completion_item, buffer, completion):
    for nick in users.nicks():
        weechat.hook_completion_list_add(completion, nick, 0, weechat.WEECHAT_LIST_POS_END)
    return WEECHAT_RC_OK

@cmpl_get_irc_users
def hosts_cmpl(users, data, completion_item, buffer, completion):
    for hostmask in users.hostmasks(sorted=True, all=True):
        weechat.hook_completion_list_add(completion, get_host(hostmask), 0,
                weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK

@cmpl_get_irc_users
def users_cmpl(users, data, completion_item, buffer, completion):
    for hostmask in users.hostmasks(sorted=True, all=True):
        user = get_user(hostmask)
        weechat.hook_completion_list_add(completion, user, 0, weechat.WEECHAT_LIST_POS_END)
    return WEECHAT_RC_OK

# info hooks
def info_hostmask_from_nick(data, info_name, arguments):
    #debug('INFO: %s %s', info_name, arguments)
    args = arguments.split(',')
    channel = None
    try:
        nick, server, channel = args
    except ValueError:
        try:
            nick, server = args
        except ValueError:
            return ''
    try:
        hostmask = userCache.getHostmask(nick, server, channel)
    except KeyError:
        return ''
    return hostmask

def info_pattern_match(data, info_name, arguments):
    #debug('INFO: %s %s', info_name, arguments)
    pattern, string = arguments.split(',')
    if pattern_match(pattern, string):
        return '1'
    return ''

# -----------------------------------------------------------------------------
# Chanop bar callbacks

chanop_bar_current_buffer = ''

@catchExceptions
def item_ban_matches_cb(data, item, window):
    #debug('ban matches item: %s %s', item, window)
    global chanop_bar_current_buffer
    buffer = chanop_bar_current_buffer
    if not buffer:
        return ''

    input = weechat.buffer_get_string(buffer, 'input')
    if not input:
        return ''

    command, _, content = input.partition(' ')

    if command[1:] not in ('oban', 'oquiet'):
        return ''

    def format(s):
        return '%s affects: %s' % (command, s)

    channel = weechat.buffer_get_string(buffer, 'localvar_channel')
    if not channel or not is_channel(channel):
        return format('(not an IRC channel)')

    server = weechat.buffer_get_string(buffer, 'localvar_server')
    users = userCache[server, channel]
    content = content.split()
    masks = [ mask for mask in content if is_hostmask(mask) or is_nick(mask) ]
    if not masks:
        return format('(no valid user mask or nick)')

    #debug('ban matches item: %s', masks)

    affected = []
    hostmasks = users.hostmasks(all=True)
    for mask in masks:
        if is_hostmask(mask):
            affected.extend(hostmask_match_list(mask, hostmasks))
        elif mask in users:
            affected.append(mask)
    #debug('ban matches item: %s', affected)

    if not affected:
        return format('(nobody)')

    L = set([ get_nick(h) for h in affected ])
    return format('(%s) %s' % (len(L), ' '.join(L)))

chanop_bar_status = ''
def item_status_cb(data, item, window):
    global chanop_bar_status
    if chanop_bar_status:
        return "%s[%s%s%s]%s %s" % (COLOR_BAR_DELIM,
                                    COLOR_BAR_FG,
                                    SCRIPT_NAME,
                                    COLOR_BAR_DELIM,
                                    color_reset,
                                    chanop_bar_status)
    else:
        return "%s[%s%s%s]" % (COLOR_BAR_DELIM,
                               COLOR_BAR_FG,
                               SCRIPT_NAME,
                               COLOR_BAR_DELIM)

@catchExceptions
def input_content_cb(data, modifier, modifier_data, string):
    #debug('input_content_cb: %s %s %r', modifier, modifier_data, string)
    global chanop_bar_current_buffer, chanop_bar_status
    if not chanop_bar:
        return string

    if string and not weechat.string_input_for_buffer(string):
        command, _, content = string.partition(' ')
        content = content.strip()
        if content and command[1:] in ('oban', 'oquiet'):
            chanop_bar.show()
            chanop_bar_current_buffer = modifier_data
            weechat.bar_item_update('chanop_ban_matches')
            if chanop_bar_status:
                chanop_bar_status = ''
                weechat.bar_item_update('chanop_bar_status')
            return string

    if not chanop_bar._timer_hook:
        chanop_bar.hide()
    return string

# -----------------------------------------------------------------------------
# Main

def unload_chanop():
    if chanop_bar:
        # we don't remove it, so custom options configs aren't lost
        chanop_bar.hide()
    bar_item = weechat.bar_item_search('chanop_ban_matches')
    if bar_item:
        weechat.bar_item_remove(bar_item)
    return WEECHAT_RC_OK

# Register script
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, 'unload_chanop', ''):

    # colors
    color_delimiter = weechat.color('chat_delimiters')
    color_chat_nick = weechat.color('chat_nick')
    color_chat_host = weechat.color('chat_host')
    color_mask      = weechat.color('white')
    color_channel   = weechat.color('lightred')
    color_reset     = weechat.color('reset')
    COLOR_WHITE     = weechat.color('white')
    COLOR_DARKGRAY  = weechat.color('darkgray')
    COLOR_BAR_DELIM = weechat.color('bar_delim')
    COLOR_BAR_FG    = weechat.color('bar_fg')

    # pretty [chanop]
    script_nick = '%s[%s%s%s]%s' %(color_delimiter,
                                   color_chat_nick,
                                   SCRIPT_NAME,
                                   color_delimiter,
                                   color_reset)

    # -------------------------------------------------------------------------
    # Debug

    enable_debug_cb('', '', weechat.config_get_plugin('debug'))
    weechat.hook_config('plugins.var.python.%s.debug' % SCRIPT_NAME, 'enable_debug_cb', '')

    # -------------------------------------------------------------------------
    # Init

    # check weechat version
    try:
        version = int(weechat.info_get('version_number', ''))
    except:
        version = 0
    if version < WEECHAT_VERSION[0]:
        error("This version of WeeChat isn't supported. Use %s or later." % WEECHAT_VERSION[1])
        raise Exception('unsupported weechat version')
    if version < 0x30300: # prior to 0.3.3 didn't have support for ISUPPORT msg
        error('WeeChat < 0.3.3: using ISUPPORT workaround.')
        weechat.hook_signal('*,irc_in_005', 'isupport_cb', '')
    if version < 0x30400: # irc_nick flags changed in 0.3.4
        error('WeeChat < 0.3.4: using irc_nick infolist workaround.')
        Infolist._use_flags = True

    for opt, val in settings.items():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

    modeCache = ModeCache('chanop_mode_cache.dat')
    modeCache.registerMode('b', 'ban', 'bans')
    modeCache.registerMode('q', 'quiet', 'quiets')

    # -------------------------------------------------------------------------
    # remove old chanmask config and save them in shelf

    prefix = 'python.%s.chanmask' % SCRIPT_NAME
    infolist = Infolist('option', 'plugins.var.%s.*' % prefix)
    n = len(prefix)
    while infolist.next():
        option = infolist['option_name'][n + 1:]
        server, channel, mode, mask = option.split('.', 3)
        if mode in modeCache:
            cache = modeCache[mode]
            if (server, channel) in cache:
                masklist = cache[server, channel]
            else:
                masklist = cache[server, channel] = MaskList(server, channel)
        if mask in masklist:
            masklist[mask].deserialize(infolist['value'])
        else:
            obj = masklist[mask] = MaskObject(mask)
            obj.deserialize(infolist['value'])
        weechat.config_unset_plugin('chanmask.%s.%s.%s.%s' \
                % (server, channel, mode, mask))
    del infolist

    # hook /oop /odeop
    Op().hook()
    Deop().hook()
    # hook /okick /obankick
    if get_config_boolean('enable_multi_kick'):
        cmd_kick = MultiKick()
        cmd_bankick = MultiBanKick()
    else:
        cmd_kick = Kick()
        cmd_bankick = BanKick()
    cmd_kick.hook()
    cmd_bankick.hook()
    # hook /oban /ounban /olist
    Ban().hook()
    UnBan().hook()
    showBans = ShowBans()
    showBans.hook()
    # hook /oquiet /ounquiet
    Quiet().hook()
    UnQuiet().hook()
    # hook /otopic /omode /ovoive /odevoice
    Topic().hook()
    Mode().hook()
    Voice().hook()
    DeVoice().hook()

    maskSync.hook()

    weechat.hook_config('plugins.var.python.%s.enable_multi_kick' % SCRIPT_NAME,
            'enable_multi_kick_conf_cb', '')
    weechat.hook_config('plugins.var.python.%s.watchlist.*' % SCRIPT_NAME,
            'update_chanop_watchlist_cb', '')
    weechat.hook_config('plugins.var.python.%s.enable_bar' % SCRIPT_NAME,
            'enable_bar_cb', '')

    weechat.hook_completion('chanop_unban_mask', 'channelmode b masks', 'unban_mask_cmpl', 'b')
    weechat.hook_completion('chanop_unquiet_mask', 'channelmode q masks', 'unban_mask_cmpl', 'q')
    weechat.hook_completion('chanop_ban_mask', 'completes partial mask', 'ban_mask_cmpl', '')
    weechat.hook_completion('chanop_nicks', 'nicks in cache', 'nicks_cmpl', '')
    weechat.hook_completion('chanop_users', 'usernames in cache', 'users_cmpl', '')
    weechat.hook_completion('chanop_hosts', 'hostnames in cache', 'hosts_cmpl', '')

    weechat.hook_signal('*,irc_in_join', 'join_cb', '')
    weechat.hook_signal('*,irc_in_part', 'part_cb', '')
    weechat.hook_signal('*,irc_in_quit', 'quit_cb', '')
    weechat.hook_signal('*,irc_in_nick', 'nick_cb', '')
    weechat.hook_signal('*,irc_in_mode', 'mode_cb', '')

    # run our cleaner function every 30 min.
    weechat.hook_timer(1000 * 60 * 30, 0, 0, 'garbage_collector_cb', '')

    chanop_bar = PopupBar('chanop_bar', hidden=True,
            items='chanop_status,chanop_ban_matches')
    if get_config_boolean('enable_bar'):
        chanop_bar.new()
        weechat.bar_item_new('chanop_ban_matches', 'item_ban_matches_cb', '')
        weechat.bar_item_new('chanop_status', 'item_status_cb', '')
        weechat.hook_modifier('input_text_content', 'input_content_cb', '')
    else:
        chanop_bar.remove()

    weechat.hook_info("chanop_hostmask_from_nick",
            "Returns nick's hostmask if is known. Returns '' otherwise.",
            "nick,server[,channel]", "info_hostmask_from_nick", "")
    weechat.hook_info("chanop_pattern_match",
            "Test if pattern matches text, is case insensible with IRC case rules.",
            "pattern,text", "info_pattern_match", "")


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
