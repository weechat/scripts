# -*- coding: utf-8 -*-
###
# Copyright (c) 2009-2010 by Elián Hanisch <lambdae2@gmail.com>
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
#   * plugins.var.python.chanop.deop_command:
#     Same as op_command but for deop.
#     It accepts the special vars $server, $channel and $nick
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
#     Same as chanop_nicks, but with the host part of the hostmask.
#
#
#   TODO
#   * use dedicated config file like in urlgrab.py
#    (win free config value validation by WeeChat)
#   * ban expire time
#   * save ban.mask and ban.hostmask across reloads
#   * allow to override quiet command (for quiet with ChanServ)
#   * multiple-channel ban (?)
#   * freenode:
#    - support for bans with channel forward
#    - support for extbans (?)
#   * Sort completions by user activity
#
#
#   History:
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

SCRIPT_NAME    = "chanop"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.2.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Helper script for IRC Channel Operators"

### default settings ###
settings = {
'op_command'            :'/msg chanserv op $channel $nick',
'autodeop'              :'on',
'autodeop_delay'        :'180',
'default_banmask'       :'host',
'enable_remove'         :'off',
'kick_reason'           :'KTHXBYE',
'enable_multi_kick'     :'off',
'display_affected'      :'on',
}


try:
    import weechat
    from weechat import WEECHAT_RC_OK, prnt
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import getopt, re
from time import time

################
### Messages ###

script_nick = SCRIPT_NAME
def error(s, buffer=''):
    """Error msg"""
    prnt(buffer, '%s%s %s' %(weechat.prefix('error'), script_nick, s))
    if weechat.config_get_plugin('debug'):
        import traceback
        if traceback.sys.exc_type:
            trace = traceback.format_exc()
            prnt('', trace)

def say(s, buffer=''):
    """normal msg"""
    prnt(buffer, '%s\t%s' %(script_nick, s))

def debug(s, *args):
    if not isinstance(s, basestring):
        s = str(s)
    if args:
        s = s %args
    prnt('', '%s\t%s' %(script_nick, s))


##############
### Config ###

# TODO Need to refactor all this too

boolDict = {'on':True, 'off':False}
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


#############
### Utils ###

now = lambda: int(time())

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


#################
### IRC utils ###

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

_valid_label = re.compile(r'^[a-z\d\-]+$', re.I)
def is_hostname(s):
    """Checks if 's' is a valid hostname."""
    if not s:
        return False
    for label in s.split('.'):
        if not label or not _valid_label.match(label):
            return False
    return True

def hostmask_pattern_match(pattern, strings):
    if is_hostmask(pattern): # is this good at all? XXX
        return pattern_match(pattern, strings)
    return []

_regexp_cache = {}
def pattern_match(pattern, strings):
    # we will take the trouble of using regexps, since they
    # match faster than fnmatch once compiled
    if pattern in _regexp_cache:
        regexp = _regexp_cache[pattern]
    else:
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
            elif c in '^~':
                s += '[~^]'
            else:
                s += re.escape(c)
        s += '$'
        regexp = re.compile(s, re.I)
        _regexp_cache[pattern] = regexp

    if isinstance(strings, str):
        strings = [strings]
    # FIXME don't always return a list
    return [ s for s in strings if s and regexp.match(s) ]

def get_nick(s):
    """':nick!user@host' => 'nick'"""
    #assert is_hostmask(s) # not all are valid hostmasks, like server.freenode.net
    return weechat.info_get('irc_nick_from_host', s)

def get_user(s, trim=False):
    """'nick!user@host' => 'user'"""
    assert is_hostmask(s)
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
    assert is_hostmask(s)
    if ' ' in s:
        return s[s.find('@') + 1:s.find(' ')]
    return s[s.find('@') + 1:]

def is_channel(s):
    return weechat.info_get('irc_is_channel', s)

def is_nick(s):
    return weechat.info_get('irc_is_nick', s)

# for old WeeChat
_nickchars = re.escape(r'[]\`_^{|}')
_nickRe = re.compile(r'^[A-Za-z%s][-0-9A-Za-z%s]*$' %(_nickchars, _nickchars))
def _is_nick(s):
    return bool(_nickRe.match(s))

def hex_to_ip(s):
    """'7f000001' => '127.0.0.1'"""
    try:
        ip = map(lambda n: s[n:n+2], range(0, len(s), 2))
        ip = map(lambda n: int(n, 16), ip)
        return '.'.join(map(str, ip))
    except:
        return ''

def irc_buffer(buffer):
    """Returns pair (server, channel) or None if buffer isn't an irc channel"""
    get_string = weechat.buffer_get_string
    if get_string(buffer, 'plugin') == 'irc' \
            and get_string(buffer, 'localvar_type') == 'channel':
        channel = get_string(buffer, 'localvar_channel')
        server = get_string(buffer, 'localvar_server')
        return (server, channel)


#######################
### WeeChat classes ###

def callback(method):
    """This function will take a bound method or function and make it a callback."""
    # try to create a descriptive and unique name.
    func = method.func_name
    try:
        im_self = method.im_self
        try:
            inst = im_self.__name__
        except AttributeError:
            inst = im_self.__class__.__name__
        name = '%s_%s' %(inst, func)
    except AttributeError:
        # not a bound method
        name = func
    # set our callback
    import __main__
    setattr(__main__, name, method)
    #debug('callback: %s', name)
    return name

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
            }

    _use_flags = False

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


def nick_infolist(server, channel):
    return Infolist('irc_nick', '%s,%s' %(server, channel))


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


############################
### Per buffer variables ###

class EnviromentVars(dict):
    def __init__(self, buffer):
        self.buffer = buffer
        self.irc = IrcCommands(buffer)
        self.autodeop = True
        self.deopHook = self.opHook = self.opTimeout = None
        self.server = weechat.buffer_get_string(buffer, 'localvar_server')
        self.channel = weechat.buffer_get_string(buffer, 'localvar_channel')
        self.nick = weechat.info_get('irc_nick', self.server)

    def __getattr__(self, k):
        return self[k]

    def __setattr__(self, k, v):
        self[k] = v


class ConfigOptions(object):
    buffer = ''
    _env = {}
    def __getattr__(self, k):
        return self._env[self.buffer][k]

    def setup(self, buffer):
        self.buffer = buffer
        if buffer not in self._env:
            self._env[buffer] = EnviromentVars(buffer)

    @property
    def env(self):
        return self._env[self.buffer]

    def envOf(self, buffer):
        return self._env[buffer]

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


##########################
### IRC messages queue ###

class Message(ConfigOptions):
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
        self.send(cmd)

    def send(self, cmd):
        if weechat.config_get_plugin('debug'):
            debug('sending: %r', cmd)
        weechat.command(self.buffer, cmd)

    def __repr__(self):
        return '<Message(%s, %s)>' %(self.command, self.args)


class IrcCommands(ConfigOptions):
    """Class that manages and sends the script's commands to WeeChat."""

    # Special message classes
    class OpMessage(Message):
        def send(self, cmd):
            if self.irc.checkOp():
                # nothing to do
                return

            self.irc.interrupt = True
            Message.send(self, cmd)

            def modeOpCallback(data, signal, signal_data):
                signal = signal_data.split(None, 1)[1]
                if signal == data:
                    #debug('We got op')
                    # add this channel to our watchlist
                    config = 'watchlist.%s' %self.server
                    channels = CaseInsensibleSet(get_config_list(config))
                    if self.channel not in channels:
                        channels.add(self.channel)
                        value = ','.join(channels)
                        weechat.config_set_plugin(config, value)
                    weechat.unhook(self.opHook)
                    weechat.unhook(self.opTimeout)
                    self.env.opTimeout = self.env.opHook = None
                    self.irc.interrupt = False
                    self.irc.run()
                return WEECHAT_RC_OK

            def timeoutCallback(channel, count):
                error("Couldn't get op in '%s', purging command queue..." %channel)
                weechat.unhook(self.opHook)
                if self.deopHook:
                    weechat.unhook(self.deopHook)
                    self.env.deopHook = None
                self.env.opTimeout = self.env.opHook = None
                self.irc.interrupt = False
                self.irc.clear()
                return WEECHAT_RC_OK

            # wait for a while before timing out.
            data = '%s.%s' %(self.server, self.channel)
            self.env.opTimeout = weechat.hook_timer(30*1000, 0, 1, callback(timeoutCallback), data)

            data = 'MODE %s +o %s' %(self.channel, self.nick)
            self.env.opHook = weechat.hook_signal('%s,irc_in2_MODE' %self.server,
                    callback(modeOpCallback), data)


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
                    args.append(a)
                if m[0] != prefix:
                    prefix = m[0]
                    modeChar.append(prefix)
                modeChar.append(m[1])
            args.insert(0, ''.join(modeChar))
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
            raise Exception, "No command defined for get op."
        msg = self.OpMessage(value)
        self.queue(msg)

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

    def queue(self, message):
        #debug('queuing: %s', message)
        # merge /modes
        if self.commands and message.command == 'mode':
            max_modes = supported_maxmodes(self.server)
            msg = self.commands[-1]
            if msg.command == 'mode' and len(msg.chars) < max_modes:
                msg.chars.append(message.chars[0])
                msg.charargs.append(message.charargs[0])
                return
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
        self.commands = []


#########################
### User/Mask classes ###

class CaseInsensibleString(str):
    def __init__(self, s=''):
        self.lowered = s.lower()
    
    lower    = lambda self: self.lowered
    __eq__   = lambda self, s: self.lowered == s.lower()
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
        for k, v in kwargs.iteritems():
            self[k] = v

    def __setitem__(self, k, v):
        dict.__setitem__(self, self.key(k), v)

    def __getitem__(self, k):
        return dict.__getitem__(self, self.key(k))

    def __delitem__(self, k):
        dict.__delitem__(self, self.key(k))

    def __contains__(self, k):
        return dict.__contains__(self, self.key(k))


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
                #debug('Removing %s.%s list, not in watchlist. (%s items)', key[0], key[1], len(self[key]))
                del self[key]
        for data in self.itervalues():
            data.purge()

# Masks
class MaskObject(object):
    __slots__ = ('mask', 'hostmask', 'operator', 'date')#, 'expires')
    def __init__(self, mask, hostmask=None, operator=None, date=None):#, expires=None):
        self.mask = mask
        self.hostmask = hostmask
        self.operator = operator
        if date:
            date = int(date)
        else:
            date = now()
        self.date = date
#        self.expires = expires

    def __repr__(self):
        return "<MaskObject(%s)>" %self.mask


class MaskList(CaseInsensibleDict):
    def __init__(self, server, channel):
        self.server = CaseInsensibleString(server)
        self.channel = CaseInsensibleString(channel)
        self.synced = 0

    def add(self, mask, **kwargs):
        if mask in self:
            # mask exists, update it
            ban = self[mask]
            for attr, value in kwargs.iteritems():
                if value:
                    setattr(ban, attr, value)
        else:
            self[mask] = MaskObject(mask, **kwargs)

    def searchByHostmask(self, hostmask):
        return [ mask for mask in self if hostmask_pattern_match(mask, hostmask) ]

    def searchByPattern(self, pattern):
        return pattern_match(pattern, self.iterkeys())

    def searchByNick(self, nick):
        try:
            hostmask = userCache.getHostmask(nick, self.server, self.channel)
            if callable(hostmask):
                # can't wait for /userhost
                return []
            return self.searchByHostmask(hostmask)
        except KeyError:
            return []

    def search(self, s):
        if is_nick(s):
            masks = self.searchByNick(s)
        elif is_hostmask(s):
            masks = self.searchByHostmask(s)
        else:
            masks = self.searchByPattern(s)
        return masks

    def purge(self):
        pass


class MaskCache(ServerChannelDict):
    """Keeps a list of our bans for quick look up."""
    def __init__(self, mode='b'):
        self.mode = mode

    def add(self, server, channel, mask, **kwargs):
        """Adds a ban to (server, channel) banlist."""
        key = (server, channel)
        if key not in self:
            self[key] = MaskList(*key)
        self[key].add(mask, **kwargs)

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


class MaskHandler(ServerChannelDict):
    _hook_mask = ''
    _hook_end = ''
    _hide_msg = False

    caches = {}
    _modeTranslation = CaseInsensibleDict()
    queue = []
    _execute = CaseInsensibleDict()

    def hook(self):
        if not self._hook_mask:
            self._hook_mask = \
                    weechat.hook_modifier('irc_in_367', callback(self._maskCallback), '')
        if not self._hook_end:
            self._hook_end = \
                    weechat.hook_modifier('irc_in_368', callback(self._endCallback), '')

    def unhook(self):
        if self._hook_mask:
            weechat.unhook(self._hook_mask)
            self._hook_mask = ''
        if self._hook_end:
            weechat.unhook(self._hook_end)
            self._hook_end = ''

    def __setitem__(self, key, value):
        try:
            self[key].append(value)
        except:
            ServerChannelDict.__setitem__(self, key, [value])

    def addCache(self, mode, *args):
        def fetch(server, channel, execute=None):
            self.fetch(server, channel, mode, execute)

        cache = MaskCache(mode)
        cache.fetch = fetch

        self.caches[mode] = cache
        for name in args:
            self._modeTranslation[name] = cache

    def getCache(self, mode):
        try:
            return self.caches[mode]
        except KeyError:
            return self._modeTranslation[mode]

    def fetch(self, server, channel, mode, execute=None):
        """Fetches masks for a given server and channel."""
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        if not buffer or not weechat.info_get('irc_is_channel', channel):
            # invalid server or channel
            return 

        # check modes
        if mode not in supported_modes(server):
            return
        maskCache = self.caches[mode]
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
            self._fetch(server, channel, mode)
        elif (server, channel, mode) not in self.queue:
            self.queue.append((server, channel, mode))

        if execute:
            self._execute[server, channel] = execute

    def _fetch(self, server, channel, mode):
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        if not buffer:
            return
        cmd = '/mode %s %s' %(channel, mode)
        #say('Fetching %s masks (+%s channelmode).' %(channel, mode))
        self._hide_msg = True
        weechat.command(buffer, cmd)

    def _maskCallback(self, data, modifier, modifier_data, string):
        """callback for irc_in_367 modifier, a single ban."""
        #debug(string)
        channel, banmask, op, date = string.split()[-4:]
        self[modifier_data, channel] = (banmask, op, date) # store temporally until irc_368 msg
        if self._hide_msg:
            return ''
        else:
            return string
    
    def _endCallback(self, data, modifier, modifier_data, string):
        """callback for irc_in_368 modifier that marks the end of channel's ban list."""
        #debug(string)
        L = string.split()
        channel, mode = L[3], L[7]
        server = modifier_data

        try:
            maskCache = self.getCache(mode)
            for banmask, op, date in self[server, channel]:
                maskCache.add(server, channel, banmask, operator=op, date=date)
            masklist = maskCache[server, channel]
        except KeyError:
            masklist = maskCache[server, channel] = MaskList(server, channel)
        finally:
            if (server, channel) in self:
                del self[server, channel]

        masklist.synced = now()

        # run finishing functions if any
        if (server, channel) in self._execute:
            self._execute[server, channel]()
            del self._execute[server, channel]

        try:
            if self._hide_msg:
                return ''
            else:
                return string
        finally:
            if self.queue:
                next = self.queue.pop(0)
                self._fetch(*next)
            else:
                self._hide_msg = False


maskHandler = MaskHandler()
maskHandler.addCache('b', 'ban', 'bans')
maskHandler.addCache('q', 'quiet', 'quiets')


# Users
class UserObject(object):
    __slots__ = ('nick', 'hostmask', 'seen', 'channels')
    def __init__(self, nick, hostmask):
        self.nick = nick
        self.hostmask = hostmask
        self.seen = now()
        self.channels = 0

    def update(self, hostmask=None):
        if hostmask:
            self.hostmask = hostmask
        self.seen = now()

    def __len__(self):
        return len(self.hostmask)

    def __repr__(self):
        return '<UserObject(%s)>' %(self.hostmask or self.nick)


class ServerUserList(CaseInsensibleDict):
    def __init__(self, server):
        self.server = server
        self._purge_time = 3600*4 # 4 hours

    def getHostmask(self, nick):
        user = self[nick]
        if not user.hostmask:
            userCache.userhost(self.server, nick)
            return lambda: user.hostmask or user.nick
        return user.hostmask

    def purge(self):
        """Purge old nicks"""
        n = now()
        for nick, user in self.items():
            if user.channels < 1 and (n - user.seen) > self._purge_time:
                #debug('purging user: %s' %user)
                del self[nick]


class UserList(ServerUserList):
    def __init__(self, server, channel):
        self.server = server
        self.channel = channel
        self._purge_list = {}
        self._purge_time = 3600*2 # 2 hours

    def remove(self, nick):
        try:
            user = self[nick]
            self._purge_list[nick] = user
            user.channels -= 1
        except KeyError:
            pass

    def values(self):
        if not all(self.itervalues()):
            userCache.who(self.server, self.channel)
        L = list(self.itervalues())
        L.sort(key=lambda x:x.seen)
        return reversed(L)
    
    def hostmasks_sorted(self):
        return [ user.hostmask for user in self.values() if user ]

    def hostmasks(self):
        return [ user.hostmask for user in self.itervalues() if user ]

    def nicks(self):
#        if not all(self.itervalues()):
#            userCache.who(self.server, self.channel)
        L = list(self.iteritems())
        L.sort(key=lambda x:x[1].seen)
        return reversed([x[0] for x in L])

    def getHostmask(self, nick):
        try:
            user = self[nick]
        except KeyError:
            user = userCache[self.server][nick]
        if not user.hostmask:
            userCache.userhost(self.server, nick)
            return lambda: user.hostmask or user.nick
        return user.hostmask

    def purge(self):
        """Purge old nicks"""
        n = now()
        for nick, user in self._purge_list.items():
            if (n - user.seen) > self._purge_time:
                try:
                    del self._purge_list[nick]
                    del self[nick]
                except KeyError:
                    pass


class UserCache(ServerChannelDict):
    servercache = CaseInsensibleDict()
    _hook_who = _hook_who_end = None
    _hook_userhost = None
    _hook_userhost_nick = []
    _channels = CaseInsensibleSet()

    def generateCache(self, server, channel):
        #debug('generateCache: %s %s', server, channel)
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
            user = self.addUser(server, nick, hostmask)
            user.channels += 1
            users[nick] = user
        self[server, channel] = users
        return users

    def addUser(self, server, nick, hostmask):
        cache = self[server]
        try:
            user = cache[nick]
            if hostmask:
                user.update(hostmask)
        except KeyError:
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
        # when we delete a channel, we need to reduce user.channels count
        # so they can be purged later.
        for user in self[k].itervalues():
            user.channels -= 1
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

        #debug('WHO: %s', channel)
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        weechat.command(buffer, '/WHO %s' %channel)

    def _whoCallback(self, data, modifier, modifier_data, string):
        #debug('%s %s %s', modifier, modifier_data, string)
        args = string.split()
        server, channel = modifier_data, args[3]
        key = ('%s.%s' %(server, channel)).lower()
        if key != data:
            return string

        nick, user, host = args[7], args[4], args[5]
        hostmask = '%s!%s@%s' %(nick, user, host)
        #debug('WHO: %s', hostmask)
        self.addUser(server, nick, hostmask)
        return ''

    def _endWhoCallback(self, data, modifier, modifier_data, string):
        args = string.split()
        server, channel = modifier_data, args[3]
        key = ('%s.%s' %(server, channel)).lower()
        if key != data:
            return string

        #debug('end WHO')
        weechat.unhook(self._hook_who)
        weechat.unhook(self._hook_who_end)
        self._hook_who = self._hook_who_end = None
        return ''

    def hookUserhost(self):
        self._hook_userhost = weechat.hook_modifier(
                'irc_in_302', callback(self._userhostCallback), '')

    def userhost(self, server, nick):
        if nick in self._hook_userhost_nick:
            return
        if not self._hook_userhost_nick:
            self._userhost(server, nick)
        self._hook_userhost_nick.append(nick)

    def _userhost(self, server, nick):
        #debug('USERHOST: %s', nick)
        buffer = weechat.buffer_search('irc', 'server.%s' %server)
        weechat.command(buffer, '/USERHOST %s' %nick)

    def _userhostCallback(self, data, modifier, modifier_data, string):
        nick, host = string.rsplit(None, 1)[1].split('=')
        nick, host = nick.strip(':*'), host[1:]
        hostmask = '%s!%s' %(nick, host)
        #debug('USERHOST: %s %s', nick, hostmask)
        self.addUser(modifier_data, nick, hostmask)
        if nick in self._hook_userhost_nick:
            del self._hook_userhost_nick[0]
            if self._hook_userhost_nick:
                nick = self._hook_userhost_nick[0]
                self._userhost(modifier_data, nick)
            return ''
        return string

    def purge(self):
        ServerChannelDict.purge(self)
        for cache in self.servercache.itervalues():
            cache.purge()

userCache = UserCache()

##############################
### Chanop Command Classes ###

# Base classes for chanop commands
class CommandChanop(Command, ConfigOptions):
    """Base class for our commands, with config and general functions."""
    infolist = None

    def parser(self, args):
        if not args:
            weechat.command('', '/help %s' %self.command)
            raise NoArguments
        self.setup(self.buffer)

    def execute(self):
        self.users = userCache[self.server, self.channel]
        self.execute_chanop()   # call our command and queue messages for WeeChat
        self.irc.run()          # run queued messages
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
        try:
            nicks = self.nick_infolist()
            while nicks.next():
                if nicks['name'] == nick:
                    return '@' in nicks['prefixes']
        except:
            error('Not in a IRC channel.')

    def has_voice(self, nick):
        try:
            nicks = self.nick_infolist()
            while nicks.next():
                if nicks['name'] == nick:
                    return '+' in nicks['prefixes']
        except:
            error('Not in a IRC channel.')

    def is_nick(self, nick):
        return nick in self.users

    def get_host(self, name):
        try:
            return self.users.getHostmask(name)
        except KeyError:
            pass

    def set_mode(self, *nicks):
        mode = self.prefix + self.mode
        for nick in nicks:
            self.irc.Mode(mode, nick)


class CommandWithOp(CommandChanop):
    """Base class for all the commands that requires op status for work."""
    def setup(self, buffer):
        self.deopNow = False
        CommandChanop.setup(self, buffer)
    
    def parser(self, args):
        CommandChanop.parser(self, args)
        args = args.split()
        if '-o' in args:
            self.deopNow = True
            del args[args.index('-o')]
            self.args = ' '.join(args)
        if not self.args:
            raise NoArguments

    def execute_chanop(self, *args):
        self.irc.Op()
        self.execute_op(*args)

        if self.autodeop and self.get_config_boolean('autodeop'):
            delay = self.get_config_int('autodeop_delay')
            if delay > 0 and not self.deopNow:
                if self.deopHook:
                    weechat.unhook(self.deopHook)
                self.env.deopHook = weechat.hook_timer(delay * 1000, 0, 1,
                        callback(self.deopCallback), self.buffer)
            else:
                self.irc.Deop()

    def execute_op(self, *args):
        """Commands in this method will be run with op privileges."""
        pass

    def deopCallback(self, buffer, count):
        #debug('deop %s', buffer)
        env = self.envOf(buffer)
        if env.autodeop:
            if env.irc.commands:
                # there are commands in queue yet, wait some more
                env.deopHook = weechat.hook_timer(1000, 0, 1,
                        callback(self.deopCallback), buffer)
                return WEECHAT_RC_OK
            else:
                env.irc.Deop()
                env.irc.run()
        env.deopHook = None
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
        self.env.autodeop = False
        if self.args:
            for nick in self.args.split():
                if self.is_nick(nick) and not self.has_op(nick):
                    self.set_mode(nick)


class Deop(Op, CommandWithOp):
    description, usage, help = \
    "Removes operator privileges from yourself or users.", "[nick [nick ... ]]", ""
    command = 'odeop'
    completion = '%(nicks)'
    
    prefix = '-'

    def execute_chanop(self):
        if self.args:
            nicks = []
            for nick in self.args.split():
                if is_nick(nick) and self.has_op(nick):
                    nicks.append(nick)
            if nicks:
                CommandWithOp.execute_chanop(self, nicks)
        else:
            self.env.autodeop = True
            if self.has_op(self.nick):
                self.irc.Deop()

    def execute_op(self, nicks):
        self.set_mode(*nicks)


class Kick(CommandWithOp):
    description, usage = "Kick nick.", "<nick> [<reason>] [-o]"
    help = \
    "On freenode, you can set this command to use /remove instead of /kick, users"\
    " will see it as if the user parted and it can bypass autojoin-on-kick scripts."\
    " See plugins.var.python.%s.enable_remove config option." %SCRIPT_NAME
    command = 'okick'
    completion = '%(nicks)'

    def execute_op(self):
        nick, s, reason = self.args.partition(' ')
        self.irc.Kick(nick, reason)


class MultiKick(Kick):
    description, usage = "Kick one or more nicks.", "<nick> [<nick> ... ] [:] [<reason>] [-o]"
    help = Kick.help + "\n\n"\
    "Note: Is not needed, but use ':' as a separator between nicks and "\
    "the reason. Otherwise, if there's a nick in the channel matching the "\
    "first word in reason it will be kicked."
    completion = '%(nicks)|%*'

    def execute_op(self):
        args = self.args.split()
        nicks = []
        #debug('multikick: %s' %str(args))
        while(args):
            nick = args[0]
            if nick[0] == ':' or not self.is_nick(nick):
                break
            nicks.append(args.pop(0))
        #debug('multikick: %s, %s' %(nicks, args))
        reason = ' '.join(args).lstrip(':')
        if nicks:
            for nick in nicks:
                self.irc.Kick(nick, reason)
        else:
            say("Sorry, found nothing to kick.", buffer=self.buffer)
            self.irc.clear()


class Ban(CommandWithOp):
    description = "Ban user or hostmask."
    usage = \
    "<nick|mask> [<nick|mask> ... ] [ [--host] [--user] [--nick] | --exact ] [-o]"
    help = \
    "Mask options:\n"\
    " -h  --host: Match hostname (*!*@host)\n"\
    " -n  --nick: Match nick     (nick!*@*)\n"\
    " -u  --user: Match username (*!user@*)\n"\
    " -e --exact: Use exact hostmask. Can't be combined with other options.\n"\
    "\n"\
    "If no mask options are supplied, configured defaults are used.\n"\
    " -o: Forces deop immediately (without configured delay).\n"\
    "\n"\
    "Example:\n"\
    "/oban somebody --user --host\n"\
    "  will ban with *!user@hostname mask.\n"
    command = 'oban'
    completion = '%(chanop_nicks)|%(chanop_ban_mask)|%*'

    banmask = []
    mode = 'b'
    prefix = '+'
    maskCache = maskHandler.caches[mode]

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
        except getopt.GetoptError, e:
            raise ArgumentError, e
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
            s = '%s!%s@%s' %(nick, user, host)
            assert is_hostmask(s), "Invalid banmask: %s" %s
            return s
        if callable(hostmask):
            return lambda: banmask(hostmask())
        return banmask(hostmask)

    def execute_op(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            mask = arg
            if not is_hostmask(arg):
                hostmask = self.get_host(arg)
                if hostmask:
                    mask = self.make_banmask(hostmask)
            if self.has_voice(arg):
                self.irc.Devoice(arg)
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
    description, usage = "Remove bans.", "<nick|mask> [<nick|mask> ... ] [-o]"
    command = 'ounban'
    help = \
    "Autocompletion will use channel's bans, patterns allowed for autocomplete multiple"\
    " bans.\n"\
    " -o: Forces deop immediately (without configured delay).\n"\
    "\n"\
    "Example:\n"\
    "/%(cmd)s *192.168*<tab>\n"\
    "  Will autocomplete with all bans matching *192.168*" %{'cmd':command}
    completion = '%(chanop_unban_mask)|%(chanop_nicks)|%*'
    prefix = '-'

    def search_masks(self, s):
        try:
            masklist = self.maskCache[self.server, self.channel]
        except KeyError:
            return []
        if is_nick(s):
            return masklist.searchByNick(s)
        elif is_hostmask(s):
            return masklist.searchByHostmask(s)
        return []

    def execute_op(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            masks = self.search_masks(arg)
            if masks:
                banmasks.extend(masks)
            else:
                banmasks.append(arg)
        self.ban(*banmasks)


class Quiet(Ban):
    description = "Silence user or hostmask."
    help = "This command is only for networks that support channel mode 'q'. See /help oban as well."
    command = 'oquiet'
    completion = '%(chanop_nicks)|%(chanop_ban_mask)|%*'

    mode = 'q'
    maskCache = maskHandler.caches[mode]


class UnQuiet(UnBan):
    command = 'ounquiet'
    description = "Remove quiets."
    help = "Works exactly like /ounban, but only for quiets. See /help ounban"
    completion = '%(chanop_unquiet_mask)|%(chanop_nicks)|%*'

    mode = 'q'
    maskCache = maskHandler.caches[mode]


class BanKick(Ban, Kick):
    description = "Bankicks nick."
    usage = "<nick> [<reason>] [ [--host] [--user] [--nick] | --exact ]"
    help = "Combines /oban and /okick commands. See /help oban and /help okick."
    command = 'obankick'
    completion = '%(chanop_nicks)'

    def execute_op(self):
        nick, s, reason = self.args.partition(' ')
        if not self.is_nick(nick):
            say("Sorry, found nothing to bankick.", buffer=self.buffer)
            self.irc.clear()
            return

        hostmask = self.get_host(nick)
        if hostmask:
            banmask = self.make_banmask(hostmask)
            self.ban(banmask)
        else:
            self.ban(nick)
        self.irc.Kick(nick, reason, wait=1)


class MultiBanKick(BanKick):
    description = "Bankicks one or more nicks."
    usage = \
    "<nick> [<nick> ... ] [:] [<reason>] [ [--host)] [--user] [--nick] | --exact ] [-o]"
    completion = '%(chanop_nicks)|%*'

    def execute_op(self):
        args = self.args.split()
        nicks = []
        while(args):
            nick = args[0]
            if nick[0] == ':' or not self.is_nick(nick):
                break
            nicks.append(args.pop(0))
        reason = ' '.join(args).lstrip(':')
        if not nicks:
            say("Sorry, found nothing to bankick.", buffer=self.buffer)
            self.irc.clear()
            return

        for nick in nicks:
            hostmask = self.get_host(nick)
            if hostmask:
                banmask = self.make_banmask(hostmask)
                self.ban(banmask)
            else:
                self.ban(nick)
        for nick in nicks:
            self.irc.Kick(nick, reason, wait=1)


class Topic(CommandWithOp):
    description, usage = "Changes channel topic.", "[-delete | topic] [-o]"
    help = "Clear topic if '-delete' is the new topic."
    command = 'otopic'
    completion = '%(irc_channel_topic)||-delete'

    def execute_op(self):
        self.irc.queue(Message('/topic %s' %self.args))


class Voice(CommandWithOp):
    description, usage = "Gives voice to somebody.", "nick [nick ... ] [-o]"
    help = " -o: Forces deop immediately (without configured delay)."
    command = 'ovoice'
    completion = '%(nicks)|%*'

    prefix = '+'
    mode = 'v'

    def execute_op(self):
        for nick in self.args.split():
            if self.is_nick(nick) and not self.has_voice(nick):
                self.set_mode(nick)


class DeVoice(Voice):
    description = "Removes voice from somebody."
    command = 'odevoice'

    prefix = '-'

    def has_voice(self, nick):
        return not Voice.has_voice(self, nick)


class Mode(CommandWithOp):
    description, usage = "Changes channel modes.", "<channel modes> [-o]"
    help = " -o: Forces deop immediately (without configured delay)."
    command = 'omode'

    def execute_op(self):
        mode, _, args = self.args.partition(' ')
        self.irc.Mode(mode, args)


class ShowBans(CommandChanop):
    description, usage, help = "Lists bans or quiets of a channel.", "(bans|quiets) [channel]", ""
    command = 'olist'
    completion = 'bans|quiets %(irc_server_channels)'
    showbuffer = ''

    padding = 40

    def parser(self, args):
        self.server = weechat.buffer_get_string(self.buffer, 'localvar_server')
        self.channel = weechat.buffer_get_string(self.buffer, 'localvar_channel')
        type, _, args = args.partition(' ')
        if not type:
            raise ValueError, 'missing argument'
        try:
            self.maskCache = maskHandler.getCache(type)
            if type == 'b':
                self.type = 'bans'
            elif type == 'q':
                self.type = 'quiets'
            else:
                self.type = type
        except KeyError:
            raise ValueError, 'incorrect argument'
        self.args = args.strip()

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
            if not isinstance(hostmask, str):
                hostmask = ' '.join(hostmask)
            self.prnt('  %s%s' %(color_chat_host, hostmask))

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
        if self.maskCache.mode not in supported_modes(self.server):
            self.clear()
            self.prnt("\n%sNetwork '%s' doesn't support %s" %(color_channel, self.server,
                self.type))
            return
        if self.args:
            key = (self.server, self.args)
        else:
            key = (self.server, self.channel)
        try:
            masklist = self.maskCache[key]
        except KeyError:
            if not (weechat.info_get('irc_is_channel', key[1]) and self.server):
                error("Command /%s must be used in an IRC buffer." %self.command)
                return
            masklist = None
        self.clear()
        mask_count = 0
        if masklist:
            mask_count = len(masklist)
            self.prnt('\n%s[%s %s]' %(color_channel, key[0], key[1]))
            masks = [ m for m in masklist.itervalues() ]
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
            self.maskCache.fetch(key[0], key[1], lambda: self.execute())
        self.set_title('List of %s known by chanop in %s.%s (total: %s)' %(self.type,
                                                                           key[0],
                                                                           key[1],
                                                                           mask_count))


########################
### Script callbacks ###

# Decorators
def signal_parse(f):
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
        #debug('%s %s %s', data, signal, signal_data)
        return f(server, channel, nick, hostmask, signal_data)
    decorator.func_name = f.func_name
    return decorator

def signal_parse_no_channel(f):
    def decorator(data, signal, signal_data):
        server = signal[:signal.find(',')]
        nick = get_nick(signal_data)
        channels = userCache.getChannels(server, nick)
        if channels:
            hostmask = signal_data[1:signal_data.find(' ')]
            #debug('%s %s %s', data, signal, signal_data)
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
                weechat.command(buffer, '/VERSION')
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
    s = modes.translate(None, '+-') # remove + and -
    if not set(servermodes).intersection(s):
        return WEECHAT_RC_OK

    # check if channel is in watchlist
    key = (server, channel)
    allkeys = CaseInsensibleSet()
    for maskCache in maskHandler.caches.itervalues():
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
    notsupported = chanmodes[0].translate(None, servermodes)
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
        maskCache = maskHandler.caches[mode]
        #debug('MODE: %s%s %s %s', action, mode, mask, op)
        if action == '+':
            hostmask = hostmask_pattern_match(mask, userCache[key].hostmasks())
            if hostmask:
                affected_users.extend(hostmask)
            maskCache.add(server, channel, mask, operator=opHostmask, hostmask=hostmask)
        elif action == '-':
            maskCache.remove(server, channel, mask)
    if affected_users and get_config_boolean('display_affected',
            get_function=get_config_specific, server=server, channel=channel):
        buffer = weechat.buffer_search('irc', '%s.%s' %key)
        print_affected_users(buffer, *set(affected_users))
    return WEECHAT_RC_OK


# User cache
@signal_parse
def join_cb(server, channel, nick, hostmask, signal_data):
    user = userCache.addUser(server, nick, hostmask)
    user.channels += 1
    userCache[server, channel][nick] = user
    return WEECHAT_RC_OK

@signal_parse
def part_cb(server, channel, nick, hostmask, signal_data):
    userCache.addUser(server, nick, hostmask)
    userCache[server, channel].remove(nick)
    return WEECHAT_RC_OK

@signal_parse_no_channel
def quit_cb(server, channels, nick, hostmask, signal_data):
    userCache.addUser(server, nick, hostmask)
    for channel in channels:
        userCache[server, channel].remove(nick)
    return WEECHAT_RC_OK

@signal_parse_no_channel
def nick_cb(server, channels, nick, hostmask, signal_data):
    newnick = signal_data[signal_data.rfind(' ')+2:]
    newhostmask = '%s!%s' %(newnick, hostmask[hostmask.find('!')+1:])
    userCache.addUser(server, nick, hostmask)
    user = userCache.addUser(server, newnick, newhostmask)
    for channel in channels:
        userCache[server, channel].remove(nick)
        user.channels += 1
        userCache[server, channel][nick] = user
    return WEECHAT_RC_OK


# Garbage collector
def garbage_collector_cb(data, counter):
    """
    This takes care of purging users and masks from channels not in watchlist, and
    expired users that parted.
    """
    for maskCache in maskHandler.caches.itervalues():
        maskCache.purge()
    userCache.purge()
    if weechat.config_get_plugin('debug'):
        print_chanop_stats()
    return WEECHAT_RC_OK

def print_chanop_stats():
    purge_users = mask_count = mask_chan = 0
    for maskCache in maskHandler.caches.itervalues():
        mask_count += sum(map(len, maskCache.itervalues()))
        mask_chan += len(maskCache)
    for server in userCache.servercache.itervalues():
        purge_users += len([ u for u in server.itervalues() if not u.channels ]) 
    user_count = sum(map(len, userCache.servercache.itervalues()))
    temp_user_count = sum(map(lambda x: len(x._purge_list), userCache.itervalues()))
    debug("%s cached masks in %s channels", mask_count, mask_chan)
    debug('%s cached users in %s servers', user_count - purge_users, len(userCache.servercache))
    debug('%s users not in channel', temp_user_count)
    debug('%s users to be purged', purge_users)
    debug('%s cached regexps', len(_regexp_cache))


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


# WeeChat completions
def cmpl_get_irc_users(f):
    """
    Decorator for check if completion is done in a irc channel, and pass the buffer's user list
    if so."""
    def decorator(data, completion_item, buffer, completion):
        key = irc_buffer(buffer)
        if not key:
            return WEECHAT_RC_OK
        users = userCache[key]
        return f(users, data, completion_item, buffer, completion)
    return decorator

def unban_mask_cmpl(mode, completion_item, buffer, completion):
    """Completion for applied banmasks, for commands like /ounban /ounquiet"""
    maskCache = maskHandler.caches[mode]
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
        if pattern:
            L = masklist.search(pattern)
            if L:
                input = '%s %s ' %(input, ' '.join(L))
                weechat.buffer_set(buffer, 'input', input)
                weechat.buffer_set(buffer, 'input_pos', str(len(input)))
                return
        elif not masklist:
            return
        for mask in masklist.iterkeys():
            weechat.hook_completion_list_add(completion, mask, 0, weechat.WEECHAT_LIST_POS_END)

    if key not in maskCache or not maskCache[key].synced:
        # do completion after fetching marks
        if not maskHandler.queue:
            def execute():
                masklist = maskCache[key]
                if masklist:
                    say('Got %s +%s masks.' %(len(masklist), maskCache.mode), buffer)
                else:
                    say('No +%s masks found.' %maskCache.mode, buffer)
                cmpl_unban(masklist)

            maskCache.fetch(server, channel, execute)
            say('Fetching +%s masks in %s, please wait...' %(mode, channel), buffer)
    else:
        # mask list is up to date, do completion
        cmpl_unban(maskCache[key])
    return WEECHAT_RC_OK

@cmpl_get_irc_users
def ban_mask_cmpl(users, data, completion_item, buffer, completion):
    """Completion for banmasks, for commands like /oban /oquiet"""
    input = weechat.buffer_get_string(buffer, 'input')
    if input[-1] == ' ':
        # no pattern, return
        return WEECHAT_RC_OK

    input, _, pattern = input.rpartition(' ')
    if pattern[-1] != '*':
        search_pattern = pattern + '*'
    else:
        search_pattern = pattern

    if '@' in pattern:
        # complete *!*@hostname
        prefix = pattern[:pattern.find('@')]
        make_mask = lambda mask: '%s@%s' %(prefix, mask[mask.find('@') + 1:])
        get_list = users.hostmasks_sorted
    elif '!' in pattern:
        # complete *!username@*
        prefix = pattern[:pattern.find('!')]
        make_mask = lambda mask: '%s!%s@*' %(prefix, mask[mask.find('!') + 1:mask.find('@')])
        get_list = users.hostmasks_sorted
    else:
        # complete nick!*@*
        make_mask = lambda mask: '%s!*@*' %mask
        get_list = users.nicks

    for mask in pattern_match(search_pattern, get_list()):
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
    for hostmask in users.hostmasks_sorted():
        weechat.hook_completion_list_add(completion, get_host(hostmask), 0,
                weechat.WEECHAT_LIST_POS_SORT)
    return WEECHAT_RC_OK

@cmpl_get_irc_users
def users_cmpl(users, data, completion_item, buffer, completion):
    for hostmask in users.hostmasks_sorted():
        user = get_user(hostmask)
        weechat.hook_completion_list_add(completion, user, 0, weechat.WEECHAT_LIST_POS_END)
    return WEECHAT_RC_OK


# Register script
if __name__ == '__main__' and import_ok and \
        weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

    try:
        # custom debug module I use, allows me to inspect script's objects.
        from weeutils import DebugBuffer
        debug = DebugBuffer('chanop_debugging', globals())
        if weechat.config_get_plugin('debug'):
            debug.create()
    except:
        pass

    # colors
    color_delimiter = weechat.color('chat_delimiters')
    color_chat_nick = weechat.color('chat_nick')
    color_chat_host = weechat.color('chat_host')
    color_mask      = weechat.color('white')
    color_channel   = weechat.color('lightred')
    color_reset     = weechat.color('reset')

    # pretty [chanop]
    script_nick = '%s[%s%s%s]%s' %(color_delimiter,
                                   color_chat_nick,
                                   SCRIPT_NAME,
                                   color_delimiter,
                                   color_reset)

    # check weechat version
    try:
        version = int(weechat.info_get('version_number', ''))
    except:
        version = 0
    #debug(version)
    if version < 0x30200:
        error('WeeChat < 0.3.2: using irc_is_nick workaround.')
        is_nick = _is_nick # prior to 0.3.2 didn't have irc_is_nick info
    if version < 0x30300: # prior to 0.3.3 didn't have support for ISUPPORT msg
        error('WeeChat < 0.3.3: using ISUPPORT workaround.')
        weechat.hook_signal('*,irc_in_005', 'isupport_cb', '')
    if version < 0x30400: # irc_nick flags changed in 0.3.4
        error('WeeChat < 0.3.4: using irc_nick infolist workaround.')
        Infolist._use_flags = True

    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)

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

    maskHandler.hook()
    userCache.hookUserhost()

    weechat.hook_config('plugins.var.python.%s.enable_multi_kick' %SCRIPT_NAME,
            'enable_multi_kick_conf_cb', '')
    weechat.hook_config('plugins.var.python.%s.watchlist.*' %SCRIPT_NAME,
            'update_chanop_watchlist_cb', '')

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
    weechat.hook_timer(30*60*1000, 0, 0, 'garbage_collector_cb', '')


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
