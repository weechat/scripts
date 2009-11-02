# -*- coding: utf-8 -*-
###
# Copyright (c) 2009 by Elián Hanisch <lambdae2@gmail.com>
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
#  Helper script for IRC operators
#
#   Inspired by auto_bleh.pl (irssi) and chanserv.py (xchat) scripts
#
#   Networks like Freenode and some channels encourage operators to not stay permanently with +o
#   privileges and only use it when needed. This script works along those lines, requesting op,
#   kick/ban/etc and deop automatically with a single command.
#   Still this script is very configurable and its behaviour can be configured in a per server or per
#   channel basis so it can fit most needs without changing its code.
#
#   Commands (see detailed help with /help in WeeChat):
#   * /oop   : Request op
#   * /odeop : Drops op
#   * /okick : Kicks user (or users)
#   * /oban  : Apply bans
#   * /ounban: Remove bans
#   * /omute : Silences user (disabled by default)
#   * /okban : Kicks and bans user (or users)
#
#
#   Settings:
#   Most configs (unless noted otherwise) can be defined for a server or a channel in particular, so
#   it is possible to request op in different networks, stay always op'ed in one channel while
#   auto-deop in another.
#
#   For define the option 'option' in server 'server_name' use:
#   /set plugins.var.python.operator.option.server_name "value"
#   For define it in the channel '#channel_name':
#   /set plugins.var.python.operator.option.server_name.#channel_name "value"
#
#   * plugins.var.python.operator.op_command:
#     Here you define the command the script must run for request op, normally
#     is a /msg to a bot, like chanserv in freenode or Q in quakenet.
#     It accepts the special vars $server, $channel and $nick
#
#     By default it ask op to chanserv, if your network doesn't use chanserv, then you must change
#     it.
#
#     Examples:
#     /set plugins.var.python.operator.op_command "/msg chanserv op $channel $nick"
#     (globally for all servers, like freenode and oftc)
#     /set plugins.var.python.operator.op_command.quakenet "/msg q op $channel $nick"
#     (for quakenet only)
#
#   * plugins.var.python.operator.deop_command:
#     Same as op_command but for deop, really not needed since /deop works anywhere, but it's there.
#     It accepts the special vars $server, $channel and $nick
#
#   * plugins.var.python.operator.deop_after_use:
#     Enables auto-deop'ing after using any of the ban or kick commands.
#     Note that if you got op manually (like with /oop) then the script won't deop you
#     Valid values 'on', 'off'
#
#   * plugins.var.python.operator.deop_delay:
#     Time it must pass (without using any commands) before auto-deop, in seconds.
#     Using zero causes to deop immediately.
#
#   * plugins.var.python.operator.default_banmask:
#     List of keywords separated by comas. Defines default banmask, when using /oban, /okban or
#     /omute
#     You can use several keywords for build a banmask, each keyword defines how the banmask will be
#     generated for a given hostmask.
#     Valid keywords are: nick, user, host, exact
#
#     Examples:
#     /set plugins.var.python.operator.default_banmask host (bans with *!*@host)
#     /set plugins.var.python.operator.default_banmask host,user (bans with *!user@host)
#     /set plugins.var.python.operator.default_banmask exact
#     (bans with nick!user@host, same as using 'nick,user,host')
#
#   * plugins.var.python.operator.kick_reason:
#     Default kick reason if none was given in the command.
#
#   * plugins.var.python.operator.enable_remove:
#     If enabled, it will use "/quote remove" command instead of /kick, enable it only in
#     networks that support it, like freenode.
#     Valid values 'on', 'off'
#
#   * plugins.var.python.operator.enable_mute:
#     Mute is disabled by default, this means /omute will ban instead of silence a user, this is
#     because not all networks support "/mode +q" and it should be enabled only for those that do.
#     Valid values 'on', 'off'
#
#
#   The following configs are global and can't be defined per server or channel.
#
#   * plugins.var.python.operator.enable_multi_kick:
#     Enables kicking multiple users with /okick command.
#     Be careful with this as you can kick somebody by accident if
#     you're not careful when writting the kick reason.
#
#     This also applies to /okban command, multiple kickbans would be enabled.
#     Valid values 'on', 'off'
#
#   * plugins.var.python.operator.merge_bans:
#     Only if you want to reduce flooding when applying (or removing) several bans and
#     if the IRC server supports it. Every 4 bans will be merged in a
#     single command. Valid values 'on', 'off'
#
#   * plugins.var.python.operator.invert_kickban_order:
#     /okban kicks first, then bans, this inverts the order.
#     Valid values 'on', 'off'
#
#
#  TODO
#  * make /ounban more useful
#  * use dedicated config file like in urlgrab.py
#   (win free config value validation by WeeChat)
#  * ban expire time
#  * add completions
#  * command for switch channel moderation on/off
#  * implement ban with channel forward
#  * user tracker (for ban even when they already /part'ed)
#  * ban by realname
#  * bantracker (keeps a record of ban and kicks) (?)
#  * smart banmask (?)
#  * multiple-channel ban (?)
#  * Add unittests (?)
#
#
#   History:
#   2009-10-31
#   version 0.1: Initial release
###

SCRIPT_NAME    = "operator"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Helper script for IRC operators"

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    #WEECHAT_RC_ERROR = weechat.WEECHAT_RC_ERROR
    import_ok = True
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://weechat.flashtux.org/"
    import_ok = False

import getopt, time, fnmatch

### messages
def debug(s, prefix='', buffer=''):
    """Debug msg"""
    weechat.prnt(buffer, 'debug:\t%s %s' %(prefix, s))

def error(s, prefix=SCRIPT_NAME, buffer=''):
    """Error msg"""
    weechat.prnt(buffer, '%s%s: %s' %(weechat.prefix('error'), prefix, s))

def say(s, prefix='', buffer=''):
    """Normal msg"""
    weechat.prnt(buffer, '%s\t%s' %(prefix, s))

### config and value validation
boolDict = {'on':True, 'off':False}
def get_config_boolean(config, get_function=None):
    if get_function and callable(get_function):
        value = get_function(config)
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
    values = value.split(',')
    for value in values:
        if value not in valid_banmask:
            default = settings[config]
            error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
            error("'%s' is an invalid value, allowed: %s." %(value, ', '.join(valid_banmask)))
            return default
    #debug("default banmask: %s" %values)
    return values


### irc utils
def is_hostmask(s):
    """Returns whether or not the string s is a valid User hostmask."""
    n = s.find('!')
    m = s.find('@')
    if n < m-1 and n >= 1 and m >= 3 and len(s) > m+1:
        return True
    else:
        return False

def hostmask_pattern_match(pattern, hostmask):
    # FIXME fnmatch is not a good option for hostmaks matching
    # I should replace it with a regexp, but I'm lazy now
    return fnmatch.fnmatch(hostmask, pattern)

### WeeChat Classes
class Infolist(object):
    """Class for reading WeeChat's infolists."""

    fields = {
            'name':'string',
            'host':'string',
            'flags':'integer',
            }

    def __init__(self, name, args=''):
        self.cursor = 0
        self.pointer = weechat.infolist_get(name, '', args)
        if self.pointer == '':
            raise Exception('Infolist initialising failed')

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
        type = self.fields[name]
        return getattr(self, 'get_%s' %type)(name)

    def get_string(self, name):
        return weechat.infolist_string(self.pointer, name)

    def get_integer(self, name):
        return weechat.infolist_integer(self.pointer, name)

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


class Command(object):
    """Class for hook WeeChat commands."""
    help = ("WeeChat command.", "[define usage template]", "detailed help here")

    def __init__(self, command, callback, completion=''):
        self._command = command
        self.callback = callback
        self.completion = completion
        self.pointer = ''
        self.hook()

    def __call__(self, *args):
        """Called by WeeChat when /command is used."""
        self.parse_args(*args)
        self.command()
        return WEECHAT_RC_OK

    def parse_args(self, data, buffer, args):
        """Do argument parsing here."""
        self.buffer = buffer
        self.args = args

    def _parse_doc(self):
        """Parsing of the command help strings."""
        desc, usage, help = self.help
        # format fix for help
        help = help.strip('\n').splitlines()
        if help:
            n = 0
            for c in help[0]:
                if c in ' \t':
                    n += 1
                else:
                    break

            def trim(s):
                return s[n:]

            help = '\n'.join(map(trim, help))
        else:
            help = ''
        return desc, usage, help

    def command(self):
        """This method is called when the command is run, override this."""
        pass

    def hook(self):
        assert self._command and self.callback
        assert not self.pointer, "There's already a hook pointer, unhook first"
        desc, usage, help = self._parse_doc()
        self.pointer = weechat.hook_command(self._command, desc, usage, help, self.completion,
                self.callback, '')
        if self.pointer == '':
            raise Exception, "hook_command failed"

    def unhook(self):
        if self.pointer:
            weechat.unhook(self.pointer)
            self.pointer = ''


### Operator Classes
class Message(object):
    """Class that stores the command for scheduling in CommandQueue."""
    def __init__(self, cmd, buffer='', wait=0):
        assert cmd
        self.command = cmd
        self.wait = wait
        self.buffer = buffer

    def __call__(self):
        if self.wait:
            weechat.command(self.buffer, '/wait %s %s' %(self.wait, self.command))
        else:
            weechat.command(self.buffer, self.command)
        return True


class CommandQueue(object):
    """Class that manages and sends the script's commands to WeeChat."""
    commands = []
    wait = 0

    class Normal(Message):
        """Normal message"""
        def __str__(self):
            return "<Normal(%s)>" \
                    %', '.join((self.command, self.buffer, str(self.wait)))


    class WaitForOp(Message):
        """This message interrupts the command queue until user is op'ed."""
        def __init__(self, cmd, server='*', channel='', nick='', **kwargs):
            Message.__init__(self, cmd, **kwargs)
            self.server = server
            self.channel = channel
            self.nick = nick

        def __call__(self):
            """Interrupt queue and wait until our user gets op."""
            global hook_timeout, hook_signal
            if hook_timeout:
                weechat.unhook(hook_timeout)
            if hook_signal:
                weechat.unhook(hook_signal)

            data = 'MODE %s +o %s' %(self.channel, self.nick)
            hook_signal = weechat.hook_signal('%s,irc_in2_MODE' %self.server,
                    'queue_continue_cb', data)

            data = '%s.%s' %(self.server, self.channel)
            hook_timeout = weechat.hook_timer(5000, 0, 1, 'queue_timeout_cb', data)

            Message.__call__(self)
            return False # returning false interrupts the queue execution

        def __str__(self):
            return "<WaitForOp(%s)>" \
                    %', '.join((self.command, self.buffer, self.server, self.channel, self.nick,
                        str(self.wait)))


    def queue(self, cmd, type='Normal', wait=1, **kwargs):
        #debug('queue: wait %s' %wait)
        pack = getattr(self, type)(cmd, wait=self.wait, **kwargs)
        self.wait += wait
        #debug('queue: %s' %pack)
        self.commands.append(pack)

    # it happened once and it wasn't pretty
    def safe_check(f):
        def abort_if_too_many_commands(self):
            if len(self.commands) > 20:
                error("Limit of 20 commands in queue reached, aborting.")
                self.clear()
            else:
                f(self)
        return abort_if_too_many_commands

    @safe_check
    def run(self):
        while self.commands:
            pack = self.commands.pop(0)
            #debug('running: %s' %pack)
            if not pack():
                return
        self.wait = 0

    def clear(self):
        self.commands = []
        self.wait = 0


weechat_queue = CommandQueue()
hook_signal = hook_timeout = None

def queue_continue_cb(data, signal, signal_data):
    global hook_timeout, hook_signal
    signal = signal_data.split(' ', 1)[1].strip()
    if signal == data:
        # we got op'ed
        #debug("We got op")
        weechat.unhook(hook_signal)
        weechat.unhook(hook_timeout)
        hook_signal = hook_timeout = None
        weechat_queue.run()
    return WEECHAT_RC_OK

def queue_timeout_cb(channel, count):
    global hook_timeout, hook_signal
    error("Couldn't get op in '%s', purging command queue..." %channel)
    weechat.unhook(hook_signal)
    hook_signal = hook_timeout = None
    weechat_queue.clear()
    return WEECHAT_RC_OK


class CommandOperator(Command):
    """Base class for our commands, with config and general functions."""
    infolist = None
    def __call__(self, *args):
        """Called by WeeChat when /command is used."""
        #debug("command __call__ args: %s" %(args, ))
        self.parse_args(*args)  # argument parsing
        self.command()          # call our command and queue messages for WeeChat
        weechat_queue.run()     # run queued messages
        self.infolist = None    # free irc_nick infolist
        return WEECHAT_RC_OK    # make WeeChat happy

    def parse_args(self, data, buffer, args):
        self.buffer = buffer
        self.args = args
        self.server = weechat.buffer_get_string(self.buffer, 'localvar_server')
        self.channel = weechat.buffer_get_string(self.buffer, 'localvar_channel')
        self.nick = weechat.info_get('irc_nick', self.server)

    def replace_vars(self, s):
        if '$channel' in s:
            s = s.replace('$channel', self.channel)
        if '$nick' in s:
            s = s.replace('$nick', self.nick)
        if '$server' in s:
            s = s.replace('$server', self.server)
        return s

    def get_config(self, config):
        string = '%s.%s.%s' %(config, self.server, self.channel)
        value = weechat.config_get_plugin(string)
        if not value:
            string = '%s.%s' %(config, self.server)
            value = weechat.config_get_plugin(string)
            if not value:
                value = weechat.config_get_plugin(config)
        return value

    def get_config_boolean(self, config):
        return get_config_boolean(config, self.get_config)

    def get_config_int(self, config):
        return get_config_int(config, self.get_config)

    def _nick_infolist(self):
        # reuse the same infolist instead of creating it many times
        # per __call__() (like with MultiKick)
        if not self.infolist:
            #debug('Creating Infolist')
            self.infolist = Infolist('irc_nick', '%s,%s' %(self.server, self.channel))
            return self.infolist
        else:
            self.infolist.reset()
            return self.infolist

    def is_op(self):
        try:
            nicks = self._nick_infolist()
            while nicks.next():
                if nicks['name'] == self.nick:
                    if nicks['flags'] & 8:
                        return True
                    else:
                        return False
        except:
            error('Not in a IRC channel.')

    def is_nick(self, nick):
        nicks = self._nick_infolist()
        while nicks.next():
            if nicks['name'] == nick:
                return True
        return False

    def get_host(self, name):
        nicks = self._nick_infolist()
        while nicks.next():
            if nicks['name'] == name:
                return '%s!%s' % (name, nicks['host'])

    def queue(self, cmd, **kwargs):
        weechat_queue.queue(cmd, buffer=self.buffer, **kwargs)

    def queue_clear(self):
        weechat_queue.clear()

    def get_op(self):
        op = self.is_op()
        if op is False:
            value = self.get_config('op_command')
            if not value:
                raise Exception, "No command defined for get op."
            self.queue(self.replace_vars(value), type='WaitForOp', server=self.server,
                    channel=self.channel, nick=self.nick, wait=0)
        return op

    def drop_op(self):
        op = self.is_op()
        if op is True:
            value = self.get_config('deop_command')
            if not value:
                value = '/deop'
            self.queue(self.replace_vars(value))


manual_op = False
class CommandNeedsOp(CommandOperator):
    """Base class for all the commands that requires op status for work."""

    def parse_args(self, data, buffer, args):
        """Show help if nothing to parse."""
        CommandOperator.parse_args(self, data, buffer, args)
        if not self.args:
            weechat.command('', '/help %s' %self._command)

    def command(self, *args):
        if not self.args:
            return # don't pointless op and deop it no arguments given
        op = self.get_op()
        global manual_op
        if op is None:
            return WEECHAT_RC_OK # not a channel
        elif op is False:
            manual_op = False
        else:
            # don't deop if we weren't auto-op'ed
            manual_op = True
        self.command_op(*args)
        if not manual_op and self.get_config_boolean('deop_after_use'):
            delay = self.get_config_int('deop_delay')
            if delay > 0:
                buffer = self.buffer
                global deop_hook
                if buffer in deop_hook:
                    weechat.unhook(deop_hook[buffer])

                deop_hook[buffer] = weechat.hook_timer(delay * 1000, 0, 1, 'deop_callback', buffer)
            else:
                self.drop_op()

    def command_op(self, *args):
        """Commands in this method will be run with op privileges."""
        pass


deop_hook = {}
def deop_callback(buffer, count):
    global deop_hook
    cmd_deop('', buffer, '')
    del deop_hook[buffer]
    return WEECHAT_RC_OK

class BanObject(object):
    def __init__(self, banmask, hostmask):
        self.banmask = banmask
        self.hostmask = hostmask
        self.time = int(time.time())

    def __str__(self):
        #return "<BanObject(%s, %s, %s)>" %(self.banmask, self.hostmask, self.time)
        return "Banmask:'%s' Hostmask:'%s' Date: %s" %(self.banmask,
                self.hostmask, time.strftime('%d/%m/%y %H:%M', time.localtime(self.time)))
                #XXX change date string to something more meanfull


class BanList(object):
    """Keeps a list of our bans for quick look up."""
    bans = {}
    def __len__(self):
        return len(self.bans)

    def add_ban(self, server, channel, banmask, hostmask):
        ban = BanObject(banmask, hostmask)
        #debug("adding ban: %s" %ban)
        key = (server, channel)
        if key in self.bans:
            self.bans[key][banmask] = ban
        else:
            self.bans[key] = { banmask:ban }

    def remove_ban(self, server, channel, banmask=None, hostmask=None):
        key = (server, channel)
        if key not in self.bans:
            return
        if banmask is None:
            del self.bans[key]
            return
        bans = self.bans[key]
        if banmask in bans:
            #debug("removing ban: %s" %banmask)
            del bans[banmask]

    def hostmask_match(self, server, channel, hostmask):
        if not hostmask: return []
        try:
            bans = self.bans[(server, channel)]
            ban_list = []
            for ban in bans.itervalues():
                if ban.hostmask == hostmask:
                    ban_list.append(ban)
                elif hostmask_pattern_match(ban.banmask, hostmask):
                    ban_list.append(ban)
                else:
                    pass
                    #debug("not match: '%s' '%s'" %(hostmask, ban.banmask))
            return ban_list
        except KeyError:
            return []


operator_banlist = BanList()

################################
### Operator Command Classes ###

class Op(CommandOperator):
    help = ("Request operator privileges.", "",
            """
            The command used for ask op is defined globally in plugins.var.python.%(name)s.op_command,
            it can be defined per server or per channel in:
              plugins.var.python.%(name)s.op_command.server_name
              plugins.var.python.%(name)s.op_command.server_name.#channel_name""" %{'name':SCRIPT_NAME})

    def command(self):
        self.get_op()


class Deop(CommandOperator):
    help = ("Drops operator privileges.", "", "")

    def command(self):
        self.drop_op()


class Kick(CommandNeedsOp):
    help = ("Kick nick.", "<nick> [<reason>]", "")

    def command_op(self, args=None):
        if not args:
            args = self.args
        if ' ' in args:
            nick, reason = args.split(' ', 1)
        else:
            nick, reason = args, ''
        if not reason:
            reason = self.get_config('kick_reason')
        self.kick(nick, reason)

    def kick(self, nick, reason, **kwargs):
        if self.get_config_boolean('enable_remove'):
            cmd = '/quote remove %s %s :%s' %(self.channel, nick, reason)
        else:
            cmd = '/kick %s %s' %(nick, reason)
        self.queue(cmd, **kwargs)


class MultiKick(Kick):
    help = ("Kick one or more nicks.",
            "<nick> [<nick> ..] [:] [<reason>]",
            """
            Note: Is not needed, but use ':' as a separator between nicks and the reason.
                  Otherwise, if there's a nick in the channel matching the first word in
                  reason it will be kicked.""")

    def command_op(self, args=None):
        if not args:
            args = self.args
        args = args.split()
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
            if not reason:
                reason = self.get_config('kick_reason')
            for nick in nicks:
                self.kick(nick, reason)
        else:
            say("Sorry, found nothing to kick.", buffer=self.buffer)
            self.queue_clear()


class Ban(CommandNeedsOp):
    help = ("Ban user or hostmask.",
            "<nick|banmask> [<nick|banmask> ..] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            """
            Banmask options:
                -h --host: Use *!*@hostname banmask
                -n --nick: Use nick!*@* banmask
                -u --user: Use *!user@* banmask
                -e --exact: Use exact hostmask, same as using --nick --user --host
                            simultaneously.

            If no banmask options are supplied, configured defaults are used.

            Example:
            /oban somebody --user --host : will use a *!user@hostname banmask.""")

    banmask = []
    def parse_args(self, *args):
        CommandNeedsOp.parse_args(self, *args)
        #if self.args == 'list':
        #    return
        args = self.args.split()
        (opts, args) = getopt.gnu_getopt(args, 'hune', ('host', 'user', 'nick', 'exact'))
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
        assert self.banmask # really, if there isn't any banmask by now there's something wrong
        if 'exact' in self.banmask:
            return hostmask
        nick = user = host = '*'
        if 'nick' in self.banmask:
            nick = hostmask[:hostmask.find('!')]
        if 'user' in self.banmask:
            user = hostmask.split('!',1)[1].split('@')[0]
        if 'host' in self.banmask:
            host = hostmask[hostmask.find('@') + 1:]
        banmask = '%s!%s@%s' %(nick, user, host)
        return banmask

    def add_ban(self, banmask, hostmask=None):
        operator_banlist.add_ban(self.server, self.channel, banmask, hostmask)

    def show_ban_list(self):
        if not operator_banlist:
            say("No bans known.")
            return
        # XXX should add methods in BanList for this
        for server, channel in operator_banlist.bans.iterkeys():
            say('%s %s' %(server, channel))
            for ban in operator_banlist.bans[server, channel].itervalues():
                say(ban)

    def command_op(self):
        #if self.args == 'list':
        #    self.queue_clear()
        #    self.show_ban_list()
        #    return
        args = self.args.split()
        banmasks = []
        for arg in args:
            mask = arg
            hostmask = None
            if not is_hostmask(arg):
                hostmask = self.get_host(arg)
                if hostmask:
                    mask = self.make_banmask(hostmask)
            self.add_ban(mask, hostmask)
            banmasks.append(mask)
        if banmasks:
            self.ban(*banmasks)
        else:
            say("Sorry, found nothing to ban.", buffer=self.buffer)
            self.queue_clear()

    def ban(self, *banmask, **kwargs):
        cmd = '/ban %s' %' '.join(banmask)
        self.queue(cmd, **kwargs)


class UnBan(Ban):
    help = ("Remove bans.",
            "<nick|banmask> [<nick|banmask> ..]",
            """
            Note: Unbaning with <nick> is not very useful at the momment, only the bans known by the
                  script (bans that were applied with this script) will be removed and only *if*
                  <nick> is present in the channel.""")

    def search_bans(self, hostmask):
        return operator_banlist.hostmask_match(self.server, self.channel, hostmask)

    def remove_ban(self, *banmask):
        for mask in banmask:
            operator_banlist.remove_ban(self.server, self.channel, mask)

    def command_op(self):
        args = self.args.split()
        banmasks = []
        for arg in args:
            if is_hostmask(arg):
                banmasks.append(arg)
            else:
                hostmask = self.get_host(arg)
                bans = self.search_bans(hostmask)
                if bans:
                    #debug('found %s' %(bans, ))
                    banmasks.extend([ban.banmask for ban in bans])
        if banmasks:
            self.remove_ban(*banmasks)
            self.unban(*banmasks)
        else:
            say("Sorry, found nothing to unban. Write the exact banmask.", buffer=self.buffer)
            self.queue_clear()

    def unban(self, *banmask):
        cmd = '/unban %s' %' '.join(banmask)
        self.queue(cmd)


class Mute(Ban):
    help = ("Silence user or hostmask.",
            Ban.help[1],
            """
            Use /ounban <nick> for remove the mute.

            Note: This command is disabled by default and should be enabled for networks that
                  support "/mode +q hostmask", use:
                  /set plugins.var.python.operator.enable_mute.your_server_name on""")
    # I need a way for disable mute per network, since networks that not recognise /mode +q will do
    # nasty stuff with the channel modes, but I can't do it in the Ban class because then KickBan
    # will mute instead of banning, hence this decorator
    def fallback_Ban(function_name):
        def decorator(mute_function):
            def new_method(self, *args, **kwargs):
                if self.get_config_boolean('enable_mute'):
                    return mute_function(self, *args, **kwargs)
                else:
                    #debug('Mute is disabled, falling back to ban')
                    ban_function = getattr(Ban, function_name)
                    return ban_function(self, *args, **kwargs)
            return new_method
        return decorator

    @fallback_Ban('add_ban')
    def add_ban(self, banmask, hostmask=None):
        # add '%' to banmask so /ounban can remove it
        operator_banlist.add_ban(self.server, self.channel, '%' + banmask, hostmask)

    @fallback_Ban('ban')
    def ban(self, *banmask, **kwargs):
        cmd = '/mode +%s %s' %('q'*len(banmask), ' '.join(banmask))
        self.queue(cmd, **kwargs)


class MergedBan(Ban):
    """several bans are merged in a "/mode +bb banmask banmask" fashion."""
    unban = False
    def ban(self, *args):
        c = self.unban and '-' or '+'
        # do 4 bans per command
        for n in range(0, len(args), 4):
            slice = args[n:n+4]
            hosts = ' '.join(slice)
            cmd = '/mode %s%s %s' %(c, 'b'*len(slice), hosts)
            self.queue(cmd)


class MergedUnBan(MergedBan, UnBan):
    unban = True
    def unban(self, *banmask):
        self.ban(*banmask)


class KickBan(Ban, Kick):
    help = ("Kickban nick.",
            "<nick> [<reason>] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            "Combines /okick and /oban commands.")

    invert = False
    def command_op(self):
        if ' ' in self.args:
            nick, reason = self.args.split(' ', 1)
        else:
            nick, reason = self.args, ''
        hostmask = self.get_host(nick)
        if hostmask:
            if not reason:
                reason = self.get_config('kick_reason')
            banmask = self.make_banmask(hostmask)
            self.add_ban(banmask, hostmask)
            if not self.invert:
                self.kick(nick, reason, wait=0)
                self.ban(banmask)
            else:
                self.ban(banmask, wait=0)
                self.kick(nick, reason)
        else:
            say("Sorry, found nothing to kickban.", buffer=self.buffer)
            self.queue_clear()


class MultiKickBan(KickBan):
    help = ("Kickban one or more nicks.",
            "<nick> [<nick> ..] [:] [<reason>] [(-h|--host)] [(-u|--user)] [(-n|--nick)] [(-e|--exact)]",
            KickBan.help[2])

    def command_op(self):
        args = self.args.split()
        nicks = []
        while(args):
            nick = args[0]
            if nick[0] == ':' or not self.is_nick(nick):
                break
            nicks.append(args.pop(0))
        reason = ' '.join(args).lstrip(':')
        if nicks:
            if not reason:
                reason = self.get_config('kick_reason')
            for nick in nicks:
                hostmask = self.get_host(nick)
                if hostmask:
                    banmask = self.make_banmask(hostmask)
                    self.add_ban(banmask, hostmask)
                    if not self.invert:
                        self.kick(nick, reason, wait=0)
                        self.ban(banmask)
                    else:
                        self.ban(banmask, wait=0)
                        self.kick(nick, reason)
        else:
            say("Sorry, found nothing to kickban.", buffer=self.buffer)
            self.queue_clear()


### config callbacks ###
def enable_multi_kick_conf_cb(data, config, value):
    global cmd_kick, cmd_kban
    cmd_kick.unhook()
    cmd_kban.unhook()
    if boolDict[value]:
        cmd_kick = MultiKick('okick', 'cmd_kick')
        cmd_kban = MultiKickBan('okban', 'cmd_kban')
    else:
        cmd_kick = Kick('okick', 'cmd_kick')
        cmd_kban = KickBan('okban', 'cmd_kban')
    return WEECHAT_RC_OK

def merge_bans_conf_cb(data, config, value):
    global cmd_ban, cmd_unban
    cmd_ban.unhook()
    cmd_unban.unhook()
    if boolDict[value]:
        cmd_ban   = MergedBan('oban', 'cmd_ban')
        cmd_unban = MergedUnBan('ounban', 'cmd_unban')
    else:
        cmd_ban   = Ban('oban', 'cmd_ban')
        cmd_unban = UnBan('ounban', 'cmd_unban')
    return WEECHAT_RC_OK

def invert_kickban_order_conf_cb(data, config, value):
    global cmd_kban
    if boolDict[value]:
        cmd_kban.invert = True
    else:
        cmd_kban.invert = False
    return WEECHAT_RC_OK


### Register Script and set configs ###
if import_ok and weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):

    # default settings
    settings = {
            'op_command'        :'/msg chanserv op $channel $nick',
            'deop_command'      :'/deop',
            'deop_after_use'    :'on',
            'deop_delay'        :'180',
            'default_banmask'   :'host',
            'enable_remove'     :'off',
            'kick_reason'       :'kthxbye!',
            'enable_multi_kick' :'off',
            'merge_bans'        :'off',
            'enable_mute'       :'off',
            'invert_kickban_order':'off'}

    for opt, val in settings.iteritems():
        if not weechat.config_is_set_plugin(opt):
                weechat.config_set_plugin(opt, val)

    # hook /oop /odeop
    cmd_op         = Op('oop', 'cmd_op')
    cmd_deop       = Deop('odeop', 'cmd_deop')
    # hook /okick /okban
    if get_config_boolean('enable_multi_kick'):
        cmd_kick   = MultiKick('okick', 'cmd_kick')
        cmd_kban   = MultiKickBan('okban', 'cmd_kban')
    else:
        cmd_kick   = Kick('okick', 'cmd_kick')
        cmd_kban   = KickBan('okban', 'cmd_kban')
    # hook /oban /ounban
    if get_config_boolean('merge_bans'):
        cmd_ban    = MergedBan('oban', 'cmd_ban')
        cmd_unban  = MergedUnBan('ounban', 'cmd_unban')
    else:
        cmd_ban    = Ban('oban', 'cmd_ban')
        cmd_unban  = UnBan('ounban', 'cmd_unban')
    # hook /omute
    cmd_mute = Mute('omute', 'cmd_mute')

    if get_config_boolean('invert_kickban_order'):
        cmd_kban.invert = True

    weechat.hook_config('plugins.var.python.%s.enable_multi_kick' %SCRIPT_NAME, 'enable_multi_kick_conf_cb', '')
    weechat.hook_config('plugins.var.python.%s.merge_bans' %SCRIPT_NAME, 'merge_bans_conf_cb', '')
    weechat.hook_config('plugins.var.python.%s.invert_kickban_order' %SCRIPT_NAME, 'invert_kickban_order_conf_cb', '')


# vim:set shiftwidth=4 tabstop=4 softtabstop=4 expandtab textwidth=100:
