# -*- coding: utf-8 -*-
"""otr - WeeChat script for Off-the-Record IRC messaging

DISCLAIMER: To the best of my knowledge this script securely provides OTR
messaging in WeeChat, but I offer no guarantee. Please report any security
holes you find.

Copyright (c) 2012-2015 Matthew M. Boedicker <matthewm@boedicker.org>
                        Nils Görs <weechatter@arcor.de>
                        Daniel "koolfy" Faucon <koolfy@koolfy.be>
                        Felix Eckhofer <felix@tribut.de>

Report issues at https://github.com/mmb/weechat-otr

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# pylint: disable=too-many-lines

from __future__ import unicode_literals

import collections
import glob
import io
import os
import platform
import re
import traceback
import shlex
import shutil
import sys

import potr
import weechat

class PythonVersion2(object):
    """Python 2 version of code that must differ between Python 2 and 3."""

    def __init__(self):
        import cgi
        self.cgi = cgi

        import HTMLParser
        self.html_parser = HTMLParser
        self.html_parser_init_kwargs = {}

        import htmlentitydefs
        self.html_entities = htmlentitydefs

    def html_escape(self, strng):
        """Escape HTML characters in a string."""
        return self.cgi.escape(strng)

    def unicode(self, *args, **kwargs):
        """Return the Unicode version of a string."""
        return unicode(*args, **kwargs)

    def unichr(self, *args, **kwargs):
        """Return the one character string of a Unicode character number."""
        return unichr(*args, **kwargs)

    def to_unicode(self, strng):
        """Convert a utf-8 encoded string to a Unicode."""
        if isinstance(strng, unicode):
            return strng
        return strng.decode('utf-8', 'replace')

    def to_str(self, strng):
        """Convert a Unicode to a utf-8 encoded string."""
        return strng.encode('utf-8', 'replace')

class PythonVersion3(object):
    """Python 3 version of code that must differ between Python 2 and 3."""

    def __init__(self, minor):
        self.minor = minor

        import html
        self.html = html

        import html.parser
        self.html_parser = html.parser
        if self.minor >= 4:
            self.html_parser_init_kwargs = {'convert_charrefs' : True}
        else:
            self.html_parser_init_kwargs = {}

        import html.entities
        self.html_entities = html.entities

    def html_escape(self, strng):
        """Escape HTML characters in a string."""
        return self.html.escape(strng, quote=False)

    def unicode(self, *args, **kwargs):
        """Return the Unicode version of a string."""
        return str(*args, **kwargs)

    def unichr(self, *args, **kwargs):
        """Return the one character string of a Unicode character number."""
        return chr(*args, **kwargs)

    def to_unicode(self, strng):
        """Convert a utf-8 encoded string to unicode."""
        if isinstance(strng, bytes):
            return strng.decode('utf-8', 'replace')
        return strng

    def to_str(self, strng):
        """Convert a Unicode to a utf-8 encoded string."""
        return strng

# We cannot use version_info.major as this is only supported on python >= 2.7
if sys.version_info[0] >= 3:
    PYVER = PythonVersion3(sys.version_info.minor)
else:
    PYVER = PythonVersion2()

SCRIPT_NAME = 'otr'
SCRIPT_DESC = 'Off-the-Record messaging for IRC'
SCRIPT_HELP = """{description}

Quick start:

Add an OTR item to the status bar by adding '[otr]' to the config setting
weechat.bar.status.items. This will show you whether your current conversation
is encrypted, authenticated and logged. /set otr.* for OTR status bar
customization options.

Start a private conversation with a friend who has OTR: /query yourpeer hi

In the private chat buffer: /otr start

If you have not authenticated your peer yet, follow the instructions for
authentication.

You can, at any time, see the current OTR session status and fingerprints with:
/otr status

View OTR policies for your peer: /otr policy

View default OTR policies: /otr policy default

Start/Stop log recording for the current OTR session: /otr log [start|stop]
This will be reverted back to the previous log setting at the end of the session.

To refresh the OTR session: /otr refresh

To end your private conversation: /otr finish

This script supports only OTR protocol version 2.
""".format(description=SCRIPT_DESC)

SCRIPT_AUTHOR = 'Matthew M. Boedicker'
SCRIPT_LICENCE = 'GPL3'
SCRIPT_VERSION = '1.9.2'

OTR_DIR_NAME = 'otr'

OTR_QUERY_RE = re.compile(r'\?OTR(\?|\??v[a-z\d]*\?)')

POLICIES = {
    'allow_v2' : 'allow OTR protocol version 2, effectively enable OTR '
                 'since v2 is the only supported version',
    'require_encryption' : 'refuse to send unencrypted messages when OTR is '
                           'enabled',
    'log' : 'enable logging of OTR conversations',
    'send_tag' : 'advertise your OTR capability using the whitespace tag',
    'html_escape' : 'escape HTML special characters in outbound messages',
    'html_filter' : 'filter HTML in incoming messages',
    }

READ_ONLY_POLICIES = {
    'allow_v1' : False,
    }

ACTION_PREFIX = '/me '
IRC_ACTION_RE = re.compile('^\x01ACTION (?P<text>.*)\x01$')
PLAIN_ACTION_RE = re.compile('^'+ACTION_PREFIX+'(?P<text>.*)$')

IRC_SANITIZE_TABLE = dict((ord(char), None) for char in '\n\r\x00')

# Patch potr.proto.TaggedPlaintext to not end plaintext tags in a space.
#
# When POTR adds OTR tags to plaintext it puts them at the end of the message.
# The tags end in a space which gets stripped off by WeeChat because it
# strips trailing spaces from commands. This causes OTR initiation to fail so
# the following code adds an extra tab at the end of the plaintext tags if
# they end in a space.
#
# The patched version also skips OTR tagging for CTCP messages because it
# breaks the CTCP format.
def patched__bytes__(self):
    """Patched potr.proto.TaggedPlainText.__bytes__."""
    # Do not tag CTCP messages.
    if self.msg.startswith(b'\x01') and \
        self.msg.endswith(b'\x01'):
        return self.msg

    data = self.msg + potr.proto.MESSAGE_TAG_BASE
    for v in self.versions:
        data += potr.proto.MESSAGE_TAGS[v]
    if data.endswith(b' '):
        data += b'\t'
    return data

potr.proto.TaggedPlaintext.__bytes__ = patched__bytes__

def command(buf, command_str):
    """Wrap weechat.command() with utf-8 encode."""
    debug(command_str)
    weechat.command(buf, PYVER.to_str(command_str))

def privmsg(server, nick, message):
    """Send a private message to a nick."""
    for line in message.splitlines():
        command('', '/quote -server {server} PRIVMSG {nick} :{line}'.format(
            server=irc_sanitize(server),
            nick=irc_sanitize(nick),
            line=irc_sanitize(line)))

def build_privmsg_in(fromm, target, msg):
    """Build inbound IRC PRIVMSG command."""
    return ':{user} PRIVMSG {target} :{msg}'.format(
        user=irc_sanitize(fromm),
        target=irc_sanitize(target),
        msg=irc_sanitize(msg))

def build_privmsgs_in(fromm, target, msg, prefix=''):
    """Build an inbound IRC PRIVMSG command for each line in msg.
    If prefix is supplied, prefix each line of msg with it."""
    cmd = []
    for line in msg.splitlines():
        cmd.append(build_privmsg_in(fromm, target, prefix+line))
    return '\r\n'.join(cmd)

def build_privmsg_out(target, msg):
    """Build outbound IRC PRIVMSG command(s)."""
    cmd = []
    for line in msg.splitlines():
        cmd.append('PRIVMSG {target} :{line}'.format(
            target=irc_sanitize(target),
            line=irc_sanitize(line)))
    return '\r\n'.join(cmd)

def irc_sanitize(msg):
    """Remove NUL, CR and LF characters from msg.
    The (utf-8 encoded version of a) string returned from this function
    should be safe to use as an argument in an irc command."""
    return PYVER.unicode(msg).translate(IRC_SANITIZE_TABLE)

def prnt(buf, message):
    """Wrap weechat.prnt() with utf-8 encode."""
    weechat.prnt(buf, PYVER.to_str(message))

def print_buffer(buf, message, level='info'):
    """Print message to buf with prefix,
    using color according to level."""
    prnt(buf, '{prefix}\t{msg}'.format(
        prefix=get_prefix(),
        msg=colorize(message, 'buffer.{0}'.format(level))))

def get_prefix():
    """Returns configured message prefix."""
    return weechat.string_eval_expression(
        config_string('look.prefix'),
        {}, {}, {})

def debug(msg):
    """Send a debug message to the OTR debug buffer."""
    debug_option = config_get_prefixed('general.debug')

    if not weechat.config_boolean(debug_option):
        return

    debug_buffer = weechat.buffer_search('python', 'OTR Debug')
    if not debug_buffer:
        debug_buffer = weechat.buffer_new('OTR Debug', '', '', '', '')
        weechat.buffer_set(debug_buffer, 'title', 'OTR Debug')
        weechat.buffer_set(debug_buffer, 'localvar_set_no_log', '1')

    prnt(debug_buffer, ('{script} debug\t{text}'.format(
        script=SCRIPT_NAME, text=PYVER.unicode(msg))))

def current_user(server_name):
    """Get the nick and server of the current user on a server."""
    return irc_user(info_get('irc_nick', server_name), server_name)

def irc_user(nick, server):
    """Build an IRC user string from a nick and server."""
    return '{nick}@{server}'.format(
        nick=nick.lower(),
        server=server)

def isupport_value(server, feature):
    """Get the value of an IRC server feature."""
    args = '{server},{feature}'.format(server=server, feature=feature)
    return info_get('irc_server_isupport_value', args)

def is_a_channel(channel, server):
    """Return true if a string has an IRC channel prefix."""
    prefixes = \
        tuple(isupport_value(server, 'CHANTYPES')) + \
        tuple(isupport_value(server, 'STATUSMSG'))

    # If the server returns nothing for CHANTYPES and STATUSMSG use
    # default prefixes.
    if not prefixes:
        prefixes = ('#', '&', '+', '!', '@')

    return channel.startswith(prefixes)

class PrivmsgParseException(Exception):
    """Exception class for PRIVMSG parsing exceptions."""
    pass

def parse_irc_privmsg(message, server):
    """Parse an IRC PRIVMSG command and return a dictionary.

    Either the to_channel key or the to_nick key will be set depending on
    whether the message is to a nick or a channel. The other will be None.

    Example input:

    :nick!user@host PRIVMSG #weechat :message here

    Output:

    {'from': 'nick!user@host',
    'from_nick': 'nick',
    'to': '#weechat',
    'to_channel': '#weechat',
    'to_nick': None,
    'text': 'message here'}
    """

    weechat_result = weechat.info_get_hashtable(
        'irc_message_parse', dict(message=message))

    if weechat_result['command'].upper() == 'PRIVMSG':
        target, text = PYVER.to_unicode(
            weechat_result['arguments']).split(' ', 1)
        if text.startswith(':'):
            text = text[1:]

        result = {
            'from': PYVER.to_unicode(weechat_result['host']),
            'to' : target,
            'text': text,
            }

        if weechat_result['host']:
            result['from_nick'] = PYVER.to_unicode(weechat_result['nick'])
        else:
            result['from_nick'] = ''

        if is_a_channel(target, server):
            result['to_channel'] = target
            result['to_nick'] = None
        else:
            result['to_channel'] = None
            result['to_nick'] = target

        return result
    else:
        raise PrivmsgParseException(message)

def has_otr_end(msg):
    """Return True if the message is the end of an OTR message."""
    return msg.endswith('.') or msg.endswith(',')

def first_instance(objs, klass):
    """Return the first object in the list that is an instance of a class."""
    for obj in objs:
        if isinstance(obj, klass):
            return obj

def config_prefix(option):
    """Add the config prefix to an option and return the full option name."""
    return '{script}.{option}'.format(
        script=SCRIPT_NAME,
        option=option)

def config_color(option):
    """Get the color of a color config option."""
    return weechat.color(weechat.config_color(config_get_prefixed(
        'color.{0}'.format(option))))

def config_string(option):
    """Get the string value of a config option with utf-8 decode."""
    return PYVER.to_unicode(weechat.config_string(
        config_get_prefixed(option)))

def config_get(option):
    """Get the value of a WeeChat config option."""
    return weechat.config_get(PYVER.to_str(option))

def config_get_prefixed(option):
    """Get the value of a script prefixed WeeChat config option."""
    return config_get(config_prefix(option))

def buffer_get_string(buf, prop):
    """Wrap weechat.buffer_get_string() with utf-8 encode/decode."""
    if buf is not None:
        encoded_buf = PYVER.to_str(buf)
    else:
        encoded_buf = None

    return PYVER.to_unicode(weechat.buffer_get_string(
        encoded_buf, PYVER.to_str(prop)))

def buffer_is_private(buf):
    """Return True if a buffer is private."""
    return buffer_get_string(buf, 'localvar_type') == 'private'

def info_get(info_name, arguments):
    """Wrap weechat.info_get() with utf-8 encode/decode."""
    return PYVER.to_unicode(weechat.info_get(
        PYVER.to_str(info_name), PYVER.to_str(arguments)))

def msg_irc_from_plain(msg):
    """Transform a plain-text message to irc format.
    This will replace lines that start with /me with the respective
    irc command."""
    return PLAIN_ACTION_RE.sub('\x01ACTION \g<text>\x01', msg)

def msg_plain_from_irc(msg):
    """Transform an irc message to plain-text.
    Any ACTION found will be rewritten as /me <text>."""
    return IRC_ACTION_RE.sub(ACTION_PREFIX + r'\g<text>', msg)

def default_peer_args(args, buf):
    """Get the nick and server of a remote peer from command arguments or
    a buffer.

    args is the [nick, server] slice of arguments from a command.
    If these are present, return them. If args is empty and the buffer buf
    is private, return the remote nick and server of buf."""
    result = None, None

    if len(args) == 2:
        result = tuple(args)
    else:
        if buffer_is_private(buf):
            result = (
                buffer_get_string(buf, 'localvar_channel'),
                buffer_get_string(buf, 'localvar_server'))

    return result

def format_default_policies():
    """Return current default policies formatted as a string for the user."""
    buf = io.StringIO()

    buf.write('Current default OTR policies:\n')

    for policy, desc in sorted(POLICIES.items()):
        buf.write('  {policy} ({desc}) : {value}\n'.format(
            policy=policy,
            desc=desc,
            value=config_string('policy.default.{0}'.format(policy))))

    buf.write('Change default policies with: /otr policy default NAME on|off')

    return buf.getvalue()

def to_bytes(strng):
    """Convert a python str or unicode to bytes."""
    return strng.encode('utf-8', 'replace')

def colorize(msg, color):
    """Colorize each line of msg using color."""
    result = []
    colorstr = config_color(color)

    for line in msg.splitlines():
        result.append('{color}{msg}'.format(
            color=colorstr,
            msg=line))

    return '\r\n'.join(result)

def accounts():
    """Return a list of all IrcOtrAccounts sorted by name."""
    result = []
    for key_path in glob.iglob(os.path.join(OTR_DIR, '*.key3')):
        key_name, _ = os.path.splitext(os.path.basename(key_path))
        result.append(ACCOUNTS[key_name])

    return sorted(result, key=lambda account: account.name)

def show_account_fingerprints():
    """Print all account names and their fingerprints to the core buffer."""
    table_formatter = TableFormatter()
    for account in accounts():
        table_formatter.add_row([
            account.name,
            str(account.getPrivkey())])
    print_buffer('', table_formatter.format())

def show_peer_fingerprints(grep=None):
    """Print peer names and their fingerprints to the core buffer.

    If grep is passed in, show all peer names containing that substring."""
    trust_descs = {
        '' : 'unverified',
        'smp' : 'SMP verified',
        'verified' : 'verified',
        }

    table_formatter = TableFormatter()
    for account in accounts():
        for peer, peer_data in sorted(account.trusts.items()):
            for fingerprint, trust in sorted(peer_data.items()):
                if grep is None or grep in peer:
                    table_formatter.add_row([
                        peer,
                        account.name,
                        potr.human_hash(fingerprint),
                        trust_descs[trust],
                    ])
    print_buffer('', table_formatter.format())

def private_key_file_path(account_name):
    """Return the private key file path for an account."""
    return os.path.join(OTR_DIR, '{0}.key3'.format(account_name))

def read_private_key(key_file_path):
    """Return the private key in a private key file."""
    debug(('read private key', key_file_path))

    with open(key_file_path, 'rb') as key_file:
        return potr.crypt.PK.parsePrivateKey(key_file.read())[0]

def get_context(account_name, context_name):
    """Return a context from an account."""
    return ACCOUNTS[account_name].getContext(context_name)

def get_server_context(server, peer_nick):
    """Return the context for the current server user and peer."""
    return get_context(current_user(server), irc_user(peer_nick, server))

class AccountDict(collections.defaultdict):
    """Dictionary that adds missing keys as IrcOtrAccount instances."""

    def __missing__(self, key):
        debug(('add account', key))
        self[key] = IrcOtrAccount(key)

        return self[key]

class Assembler(object):
    """Reassemble fragmented OTR messages.

    This does not deal with OTR fragmentation, which is handled by potr, but
    fragmentation of received OTR messages that are too large for IRC.
    """
    def __init__(self):
        self.clear()

    def add(self, data):
        """Add data to the buffer."""
        self.value += data

    def clear(self):
        """Empty the buffer."""
        self.value = ''

    def is_done(self):
        """Return True if the buffer is a complete message."""
        return self.is_query() or \
            not to_bytes(self.value).startswith(potr.proto.OTRTAG) or \
            has_otr_end(self.value)

    def get(self):
        """Return the current value of the buffer and empty it."""
        result = self.value
        self.clear()

        return result

    def is_query(self):
        """Return true if the buffer is an OTR query."""
        return OTR_QUERY_RE.search(self.value)

class IrcContext(potr.context.Context):
    """Context class for OTR over IRC."""

    def __init__(self, account, peername):
        super(IrcContext, self).__init__(account, peername)

        self.peer_nick, self.peer_server = peername.split('@', 1)
        self.in_assembler = Assembler()
        self.in_otr_message = False
        self.in_smp = False
        self.smp_question = False

    def policy_config_option(self, policy):
        """Get the option name of a policy option for this context."""
        return config_prefix('.'.join([
            'policy', self.peer_server, self.user.nick, self.peer_nick,
            policy.lower()]))

    def getPolicy(self, key):
        """Get the value of a policy option for this context."""
        key_lower = key.lower()

        if key_lower in READ_ONLY_POLICIES:
            result = READ_ONLY_POLICIES[key_lower]
        elif key_lower == 'send_tag' and self.no_send_tag():
            result = False
        else:
            option = config_get(self.policy_config_option(key))

            if option == '':
                option = config_get(self.user.policy_config_option(key))

            if option == '':
                option = config_get_prefixed('.'.join(
                    ['policy', self.peer_server, key_lower]))

            if option == '':
                option = config_get_prefixed(
                    'policy.default.{0}'.format(key_lower))

            result = bool(weechat.config_boolean(option))

        debug(('getPolicy', key, result))

        return result

    def inject(self, msg, appdata=None):
        """Send a message to the remote peer."""
        if isinstance(msg, potr.proto.OTRMessage):
            msg = PYVER.unicode(msg)
        else:
            msg = PYVER.to_unicode(msg)

        debug(('inject', msg, 'len {0}'.format(len(msg)), appdata))

        privmsg(self.peer_server, self.peer_nick, msg)

    def setState(self, newstate):
        """Handle state transition."""
        debug(('state', self.state, newstate))

        if self.is_encrypted():
            if newstate == potr.context.STATE_ENCRYPTED:
                self.print_buffer(
                    'Private conversation has been refreshed.', 'success')
            elif newstate == potr.context.STATE_FINISHED:
                self.print_buffer(
                    '{peer} has ended the private conversation. You should do '
                    'the same:\n/otr finish'.format(peer=self.peer_nick))
        elif newstate == potr.context.STATE_ENCRYPTED:
            # unencrypted => encrypted
            trust = self.getCurrentTrust()

            # Disable logging before any proof of OTR activity is generated.
            # This is necessary when the session is started automatically, and
            # not by /otr start.
            if not self.getPolicy('log'):
                self.previous_log_level = self.disable_logging()
            else:
                self.previous_log_level = self.get_log_level()
                if self.is_logged():
                    self.hint(
                        'You have enabled the recording to disk of OTR '
                        'conversations. By doing this you are potentially '
                        'putting yourself and your correspondent in danger. '
                        'Please consider disabling this policy with '
                        '"/otr policy default log off". To disable logging '
                        'for this OTR session, use "/otr log stop"')

            if trust is None:
                fpr = str(self.getCurrentKey())
                self.print_buffer('New fingerprint: {0}'.format(fpr), 'warning')
                self.setCurrentTrust('')

            if bool(trust):
                self.print_buffer(
                    'Authenticated secured OTR conversation started.',
                    'success')
            else:
                self.print_buffer(
                    'Unauthenticated secured OTR conversation started.',
                    'warning')
                self.hint(self.verify_instructions())

        if self.state != potr.context.STATE_PLAINTEXT and \
                newstate == potr.context.STATE_PLAINTEXT:
            self.print_buffer('Private conversation ended.')

            # If we altered the logging value, restore it.
            if self.previous_log_level is not None:
                self.restore_logging(self.previous_log_level)

        super(IrcContext, self).setState(newstate)

    def maxMessageSize(self, appdata=None):
        """Return the max message size for this context."""
        # remove 'PRIVMSG <nick> :' from max message size
        result = self.user.maxMessageSize - 10 - len(self.peer_nick)
        debug('max message size {0}'.format(result))

        return result

    def buffer(self):
        """Get the buffer for this context."""
        return info_get(
            'irc_buffer', '{server},{nick}'.format(
                server=self.peer_server,
                nick=self.peer_nick
                ))

    def print_buffer(self, msg, level='info'):
        """Print a message to the buffer for this context.
        level is used to colorize the message."""
        buf = self.buffer()

        # add [nick] prefix if we have only a server buffer for the query
        if self.peer_nick and not buffer_is_private(buf):
            msg = '[{nick}] {msg}'.format(
                nick=self.peer_nick,
                msg=msg)

        print_buffer(buf, msg, level)

    def hint(self, msg):
        """Print a message to the buffer but only when hints are enabled."""
        hints_option = config_get_prefixed('general.hints')

        if weechat.config_boolean(hints_option):
            self.print_buffer(msg, 'hint')

    def smp_finish(self, message=False, level='info'):
        """Reset SMP state and send a message to the user."""
        self.in_smp = False
        self.smp_question = False

        self.user.saveTrusts()
        if message:
            self.print_buffer(message, level)

    def handle_tlvs(self, tlvs):
        """Handle SMP states."""
        if tlvs:
            smp1q = first_instance(tlvs, potr.proto.SMP1QTLV)
            smp3 = first_instance(tlvs, potr.proto.SMP3TLV)
            smp4 = first_instance(tlvs, potr.proto.SMP4TLV)

            if first_instance(tlvs, potr.proto.SMPABORTTLV):
                debug('SMP aborted by peer')
                self.smp_finish('SMP aborted by peer.', 'warning')
            elif self.in_smp and not self.smpIsValid():
                debug('SMP aborted')
                self.smp_finish('SMP aborted.', 'error')
            elif first_instance(tlvs, potr.proto.SMP1TLV):
                debug('SMP1')
                self.in_smp = True

                self.print_buffer(
                    """Peer has requested SMP verification.
Respond with: /otr smp respond <secret>""")
            elif smp1q:
                debug(('SMP1Q', smp1q.msg))
                self.in_smp = True
                self.smp_question = True

                self.print_buffer(
                    """Peer has requested SMP verification: {msg}
Respond with: /otr smp respond <answer>""".format(
    msg=PYVER.to_unicode(smp1q.msg)))
            elif first_instance(tlvs, potr.proto.SMP2TLV):
                if not self.in_smp:
                    debug('Received unexpected SMP2')
                    self.smp_finish()
                else:
                    debug('SMP2')
                    self.print_buffer('SMP progressing.')
            elif smp3 or smp4:
                if smp3:
                    debug('SMP3')
                elif smp4:
                    debug('SMP4')

                if self.smpIsSuccess():

                    if self.smp_question:
                        self.smp_finish(
                            'SMP verification succeeded.', 'success')
                        if not self.is_verified:
                            self.print_buffer(
                                'You may want to authenticate your peer by '
                                'asking your own question:\n'
                                "/otr smp ask <'question'> 'secret'")
                    else:
                        self.smp_finish(
                            'SMP verification succeeded.', 'success')

                else:
                    self.smp_finish('SMP verification failed.', 'error')

    def verify_instructions(self):
        """Generate verification instructions for user."""
        return """You can verify that this contact is who they claim to be in
one of the following ways:

1) Verify each other's fingerprints using a secure channel:
  Your fingerprint : {your_fp}
  {peer}'s fingerprint : {peer_fp}
  then use the command: /otr trust {peer_nick} {peer_server}

2) SMP pre-shared secret that you both know:
  /otr smp ask {peer_nick} {peer_server} 'secret'

3) SMP pre-shared secret that you both know with a question:
  /otr smp ask {peer_nick} {peer_server} <'question'> 'secret'

Note: You can safely omit specifying the peer and server when
      executing these commands from the appropriate conversation
      buffer
""".format(
    your_fp=self.user.getPrivkey(),
    peer=self.peer,
    peer_nick=self.peer_nick,
    peer_server=self.peer_server,
    peer_fp=potr.human_hash(self.crypto.theirPubkey.cfingerprint()))

    def is_encrypted(self):
        """Return True if the conversation with this context's peer is
        currently encrypted."""
        return self.state == potr.context.STATE_ENCRYPTED

    def is_verified(self):
        """Return True if this context's peer is verified."""
        return bool(self.getCurrentTrust())

    def format_policies(self):
        """Return current policies for this context formatted as a string for
        the user."""
        buf = io.StringIO()

        buf.write('Current OTR policies for {peer}:\n'.format(
            peer=self.peer))

        for policy, desc in sorted(POLICIES.items()):
            buf.write('  {policy} ({desc}) : {value}\n'.format(
                policy=policy,
                desc=desc,
                value='on' if self.getPolicy(policy) else 'off'))

        buf.write('Change policies with: /otr policy NAME on|off')

        return buf.getvalue()

    def is_logged(self):
        """Return True if conversations with this context's peer are currently
        being logged to disk."""
        infolist = weechat.infolist_get('logger_buffer', '', '')

        buf = self.buffer()

        result = False

        while weechat.infolist_next(infolist):
            if weechat.infolist_pointer(infolist, 'buffer') == buf:
                result = bool(weechat.infolist_integer(infolist, 'log_enabled'))
                break

        weechat.infolist_free(infolist)

        return result

    def get_log_level(self):
        """Return the current logging level for this context's peer
        or -1 if the buffer uses the default log level of weechat."""
        infolist = weechat.infolist_get('logger_buffer', '', '')

        buf = self.buffer()

        if not config_get(self.get_logger_option_name()):
            result = -1
        else:
            result = 0

            while weechat.infolist_next(infolist):
                if weechat.infolist_pointer(infolist, 'buffer') == buf:
                    result = weechat.infolist_integer(infolist, 'log_level')
                    break

            weechat.infolist_free(infolist)

        return result

    def get_logger_option_name(self):
        """Returns the logger config option for this context's buffer."""
        buf = self.buffer()
        name = buffer_get_string(buf, 'name')
        plugin = buffer_get_string(buf, 'plugin')

        return 'logger.level.{plugin}.{name}'.format(
            plugin=plugin, name=name)

    def disable_logging(self):
        """Return the previous logger level and set the buffer logger level
        to 0. If it was already 0, return None."""
        # If previous_log_level has not been previously set, return the level
        # we detect now.
        if not hasattr(self, 'previous_log_level'):
            previous_log_level = self.get_log_level()

            if self.is_logged():
                weechat.command(self.buffer(), '/mute logger disable')
                self.print_buffer(
                    'Logs have been temporarily disabled for the session. '
                    'They will be restored upon finishing the OTR session.')

            return previous_log_level

        # If previous_log_level was already set, it means we already altered it
        # and that we just detected an already modified logging level.
        # Return the pre-existing value so it doesn't get lost, and we can
        # restore it later.
        else:
            return self.previous_log_level

    def restore_logging(self, previous_log_level):
        """Restore the log level of the buffer."""
        buf = self.buffer()

        if (previous_log_level >= 0) and (previous_log_level < 10):
            self.print_buffer(
                'Restoring buffer logging value to: {0}'.format(
                    previous_log_level), 'warning')
            weechat.command(buf, '/mute logger set {0}'.format(
                previous_log_level))

        if previous_log_level == -1:
            logger_option_name = self.get_logger_option_name()
            self.print_buffer(
                'Restoring buffer logging value to default', 'warning')
            weechat.command(buf, '/mute unset {0}'.format(
                logger_option_name))

        del self.previous_log_level

    def msg_convert_in(self, msg):
        """Transform incoming OTR message to IRC format.
        This includes stripping html, converting plain-text ACTIONs
        and character encoding conversion.
        Only character encoding is changed if context is unencrypted."""
        msg = PYVER.to_unicode(msg)

        if not self.is_encrypted():
            return msg

        if self.getPolicy('html_filter'):
            try:
                msg = IrcHTMLParser.parse(msg)
            except PYVER.html_parser.HTMLParseError:
                pass

        return msg_irc_from_plain(msg)

    def msg_convert_out(self, msg):
        """Convert an outgoing IRC message to be sent over OTR.
        This includes escaping html, converting ACTIONs to plain-text
        and character encoding conversion
        Only character encoding is changed if context is unencrypted."""
        if self.is_encrypted():
            msg = msg_plain_from_irc(msg)

            if self.getPolicy('html_escape'):
                msg = PYVER.html_escape(msg)

        # potr expects bytes to be returned
        return to_bytes(msg)

    def no_send_tag(self):
        """Skip OTR whitespace tagging to bots and services.

        Any nicks matching the otr.general.no_send_tag_regex config setting
        will not be tagged.
        """
        no_send_tag_regex = config_string('general.no_send_tag_regex')
        debug(('no_send_tag', no_send_tag_regex, self.peer_nick))
        if no_send_tag_regex:
            return re.match(no_send_tag_regex, self.peer_nick, re.IGNORECASE)

    def __repr__(self):
        return PYVER.to_str((
            '<{0} {1:x} peer_nick={c.peer_nick} peer_server={c.peer_server}>'
            ).format(self.__class__.__name__, id(self), c=self))

class IrcOtrAccount(potr.context.Account):
    """Account class for OTR over IRC."""

    contextclass = IrcContext

    PROTOCOL = 'irc'
    MAX_MSG_SIZE = 415

    def __init__(self, name):
        super(IrcOtrAccount, self).__init__(
            name, IrcOtrAccount.PROTOCOL, IrcOtrAccount.MAX_MSG_SIZE)

        self.nick, self.server = self.name.split('@', 1)

        # IRC messages cannot have newlines, OTR query and "no plugin" text
        # need to be one message
        self.defaultQuery = self.defaultQuery.replace("\n", ' ')

        self.key_file_path = private_key_file_path(name)
        self.fpr_file_path = os.path.join(OTR_DIR, '{0}.fpr'.format(name))

        self.load_trusts()

    def load_trusts(self):
        """Load trust data from the fingerprint file."""
        if os.path.exists(self.fpr_file_path):
            with open(self.fpr_file_path) as fpr_file:
                for line in fpr_file:
                    debug(('load trust check', line))

                    context, account, protocol, fpr, trust = \
                        PYVER.to_unicode(line[:-1]).split('\t')

                    if account == self.name and \
                            protocol == IrcOtrAccount.PROTOCOL:
                        debug(('set trust', context, fpr, trust))
                        self.setTrust(context, fpr, trust)

    def loadPrivkey(self):
        """Load key file.

        If no key file exists, load the default key. If there is no default
        key, a new key will be generated automatically by potr."""
        debug(('load private key', self.key_file_path))

        if os.path.exists(self.key_file_path):
            return read_private_key(self.key_file_path)
        else:
            default_key = config_string('general.defaultkey')
            if default_key:
                default_key_path = private_key_file_path(default_key)

                if os.path.exists(default_key_path):
                    shutil.copyfile(default_key_path, self.key_file_path)
                    return read_private_key(self.key_file_path)

    def savePrivkey(self):
        """Save key file."""
        debug(('save private key', self.key_file_path))

        with open(self.key_file_path, 'wb') as key_file:
            key_file.write(self.getPrivkey().serializePrivateKey())

    def saveTrusts(self):
        """Save trusts."""
        with open(self.fpr_file_path, 'w') as fpr_file:
            for uid, trusts in self.trusts.items():
                for fpr, trust in trusts.items():
                    debug(('trust write', uid, self.name,
                           IrcOtrAccount.PROTOCOL, fpr, trust))
                    fpr_file.write(PYVER.to_str('\t'.join(
                        (uid, self.name, IrcOtrAccount.PROTOCOL, fpr, trust))))
                    fpr_file.write('\n')

    def end_all_private(self):
        """End all currently encrypted conversations."""
        for context in self.ctxs.values():
            if context.is_encrypted():
                context.disconnect()

    def policy_config_option(self, policy):
        """Get the option name of a policy option for this account."""
        return config_prefix('.'.join([
            'policy', self.server, self.nick, policy.lower()]))

class IrcHTMLParser(PYVER.html_parser.HTMLParser):
    """A simple HTML parser that throws away anything but newlines and links"""

    @staticmethod
    def parse(data):
        """Create a temporary IrcHTMLParser and parse a single string"""
        parser = IrcHTMLParser(**PYVER.html_parser_init_kwargs)
        parser.feed(data)
        parser.close()
        return parser.result

    def reset(self):
        """Forget all state, called from __init__"""
        PYVER.html_parser.HTMLParser.reset(self)
        self.result = ''
        self.linktarget = ''
        self.linkstart = 0

    def handle_starttag(self, tag, attrs):
        """Called when a start tag is encountered"""
        if tag == 'br':
            self.result += '\n'
        elif tag == 'a':
            attrs = dict(attrs)
            if 'href' in attrs:
                self.result += '['
                self.linktarget = attrs['href']
                self.linkstart = len(self.result)

    def handle_endtag(self, tag):
        """Called when an end tag is encountered"""
        if tag == 'a':
            if self.linktarget:
                if self.result[self.linkstart:] == self.linktarget:
                    self.result += ']'
                else:
                    self.result += ']({0})'.format(self.linktarget)
                self.linktarget = ''

    def handle_data(self, data):
        """Called for character data (i.e. text)"""
        self.result += data

    def handle_entityref(self, name):
        """Called for entity references, such as &amp;"""
        try:
            self.result += PYVER.unichr(
                PYVER.html_entities.name2codepoint[name])
        except KeyError:
            self.result += '&{0};'.format(name)

    def handle_charref(self, name):
        """Called for character references, such as &#39;"""
        try:
            if name.startswith('x'):
                self.result += PYVER.unichr(int(name[1:], 16))
            else:
                self.result += PYVER.unichr(int(name))
        except ValueError:
            self.result += '&#{0};'.format(name)

class TableFormatter(object):
    """Format lists of string into aligned tables."""

    def __init__(self):
        self.rows = []
        self.max_widths = None

    def add_row(self, row):
        """Add a row to the table."""
        self.rows.append(row)
        row_widths = [len(s) for s in row]
        if self.max_widths is None:
            self.max_widths = row_widths
        else:
            self.max_widths = list(map(max, self.max_widths, row_widths))

    def format(self):
        """Return the formatted table as a string."""
        return '\n'.join([self.format_row(row) for row in self.rows])

    def format_row(self, row):
        """Format a single row as a string."""
        return ' |'.join(
            [s.ljust(self.max_widths[i]) for i, s in enumerate(row)])

def message_in_cb(data, modifier, modifier_data, string):
    """Incoming message callback"""
    debug(('message_in_cb', data, modifier, modifier_data, string))

    parsed = parse_irc_privmsg(
        PYVER.to_unicode(string), PYVER.to_unicode(modifier_data))
    debug(('parsed message', parsed))

    # skip processing messages to public channels
    if parsed['to_channel']:
        return string

    server = PYVER.to_unicode(modifier_data)

    context = get_server_context(server, parsed['from_nick'])

    context.in_assembler.add(parsed['text'])

    result = ''

    if context.in_assembler.is_done():
        try:
            msg, tlvs = context.receiveMessage(
                # potr expects bytes
                to_bytes(context.in_assembler.get()))

            debug(('receive', msg, tlvs))

            if msg:
                result = PYVER.to_str(build_privmsgs_in(
                    parsed['from'], parsed['to'],
                    context.msg_convert_in(msg)))

            context.handle_tlvs(tlvs)
        except potr.context.ErrorReceived as err:
            context.print_buffer('Received OTR error: {0}'.format(
                PYVER.to_unicode(err.args[0])), 'error')
        except potr.context.NotEncryptedError:
            context.print_buffer(
                'Received encrypted data but no private session established.',
                'warning')
        except potr.context.NotOTRMessage:
            result = string
        except potr.context.UnencryptedMessage as err:
            result = PYVER.to_str(build_privmsgs_in(
                parsed['from'], parsed['to'], PYVER.to_unicode(
                    msg_plain_from_irc(err.args[0])),
                'Unencrypted message received: '))

    weechat.bar_item_update(SCRIPT_NAME)

    return result

def message_out_cb(data, modifier, modifier_data, string):
    """Outgoing message callback."""
    result = ''

    # If any exception is raised in this function, WeeChat will not send the
    # outgoing message, which could be something that the user intended to be
    # encrypted. This paranoid exception handling ensures that the system
    # fails closed and not open.
    try:
        debug(('message_out_cb', data, modifier, modifier_data, string))

        parsed = parse_irc_privmsg(
            PYVER.to_unicode(string), PYVER.to_unicode(modifier_data))
        debug(('parsed message', parsed))

        # skip processing messages to public channels
        if parsed['to_channel']:
            return string

        server = PYVER.to_unicode(modifier_data)

        context = get_server_context(server, parsed['to_nick'])
        is_query = OTR_QUERY_RE.search(parsed['text'])

        parsed_text_bytes = to_bytes(parsed['text'])

        is_otr_message = \
            parsed_text_bytes[:len(potr.proto.OTRTAG)] == potr.proto.OTRTAG

        if is_otr_message and not is_query:
            if not has_otr_end(parsed['text']):
                debug('in OTR message')
                context.in_otr_message = True
            else:
                debug('complete OTR message')
            result = string
        elif context.in_otr_message:
            if has_otr_end(parsed['text']):
                context.in_otr_message = False
                debug('in OTR message end')
            result = string
        else:
            debug(('context send message', parsed['text'], parsed['to_nick'],
                   server))

            if context.policyOtrEnabled() and \
                not context.is_encrypted() and \
                not is_query and \
                context.getPolicy('require_encryption'):
                context.print_buffer(
                    'Your message will not be sent, because policy requires an '
                    'encrypted connection.', 'error')
                context.hint(
                    'Wait for the OTR connection or change the policy to allow '
                    'clear-text messages:\n'
                    '/otr policy require_encryption off')

            try:
                ret = context.sendMessage(
                    potr.context.FRAGMENT_SEND_ALL,
                    context.msg_convert_out(parsed['text']))

                if ret:
                    debug(('sendMessage returned', ret))
                    result = PYVER.to_str(
                        build_privmsg_out(
                            parsed['to_nick'], PYVER.to_unicode(ret)
                            ))

            except potr.context.NotEncryptedError as err:
                if err.args[0] == potr.context.EXC_FINISHED:
                    context.print_buffer(
                        'Your message was not sent. End your private '
                        'conversation:\n/otr finish',
                        'error')
                else:
                    raise

        weechat.bar_item_update(SCRIPT_NAME)
    # pylint: disable=bare-except
    except:
        try:
            print_buffer('', traceback.format_exc(), 'error')
            print_buffer('', 'Versions: {versions}'.format(
                versions=dependency_versions()), 'error')
            context.print_buffer(
                'Failed to send message. See core buffer for traceback.',
                'error')
        # pylint: disable=bare-except
        except:
            pass

    return result

def shutdown():
    """Script unload callback."""
    debug('shutdown')

    weechat.config_write(CONFIG_FILE)

    for account in ACCOUNTS.values():
        account.end_all_private()

    free_all_config()

    weechat.bar_item_remove(OTR_STATUSBAR)

    return weechat.WEECHAT_RC_OK

def command_cb(data, buf, args):
    """Parse and dispatch WeeChat OTR commands."""
    result = weechat.WEECHAT_RC_ERROR

    arg_parts = [PYVER.to_unicode(arg) for arg in shlex.split(args)]

    if len(arg_parts) in (1, 3) and arg_parts[0] in ('start', 'refresh'):
        nick, server = default_peer_args(arg_parts[1:3], buf)

        if nick is not None and server is not None:
            context = get_server_context(server, nick)
            # We need to wall disable_logging() here so that no OTR-related
            # buffer messages get logged at any point. disable_logging() will
            # be called again when effectively switching to encrypted, but
            # the previous_log_level we set here will be preserved for later
            # restoring.
            if not context.getPolicy('log'):
                context.previous_log_level = context.disable_logging()
            else:
                context.previous_log_level = context.get_log_level()

            context.hint(
                'Sending OTR query... Please await confirmation of the OTR '
                'session being started before sending a message.')
            if not context.getPolicy('send_tag'):
                context.hint(
                    'To try OTR on all conversations with {peer}: /otr '
                    'policy send_tag on'.format(peer=context.peer))

            privmsg(server, nick, '?OTR?')

            result = weechat.WEECHAT_RC_OK
    elif len(arg_parts) in (1, 3) and arg_parts[0] in ('finish', 'end'):
        nick, server = default_peer_args(arg_parts[1:3], buf)

        if nick is not None and server is not None:
            context = get_server_context(server, nick)
            context.disconnect()

            result = weechat.WEECHAT_RC_OK

    elif len(arg_parts) in (1, 3) and arg_parts[0] == 'status':
        nick, server = default_peer_args(arg_parts[1:3], buf)

        if nick is not None and server is not None:
            context = get_server_context(server, nick)
            if context.is_encrypted():
                context.print_buffer(
                    'This conversation is encrypted.', 'success')
                context.print_buffer("Your fingerprint is: {0}".format(
                    context.user.getPrivkey()))
                context.print_buffer("Your peer's fingerprint is: {0}".format(
                    potr.human_hash(context.crypto.theirPubkey.cfingerprint())))
                if context.is_verified():
                    context.print_buffer(
                        "The peer's identity has been verified.",
                        'success')
                else:
                    context.print_buffer(
                        "You have not verified the peer's identity yet.",
                        'warning')
            else:
                context.print_buffer(
                    "This current conversation is not encrypted.",
                    'warning')

            result = weechat.WEECHAT_RC_OK

    elif len(arg_parts) in range(2, 7) and arg_parts[0] == 'smp':
        action = arg_parts[1]

        if action == 'respond':
            # Check if nickname and server are specified
            if len(arg_parts) == 3:
                nick, server = default_peer_args([], buf)
                secret = arg_parts[2]
            elif len(arg_parts) == 5:
                nick, server = default_peer_args(arg_parts[2:4], buf)
                secret = arg_parts[4]
            else:
                return weechat.WEECHAT_RC_ERROR

            if secret:
                secret = PYVER.to_str(secret)

            context = get_server_context(server, nick)
            context.smpGotSecret(secret)

            result = weechat.WEECHAT_RC_OK

        elif action == 'ask':
            question = None
            secret = None

            # Nickname and server are not specified
            # Check whether it's a simple challenge or a question/answer request
            if len(arg_parts) == 3:
                nick, server = default_peer_args([], buf)
                secret = arg_parts[2]
            elif len(arg_parts) == 4:
                nick, server = default_peer_args([], buf)
                secret = arg_parts[3]
                question = arg_parts[2]

            # Nickname and server are specified
            # Check whether it's a simple challenge or a question/answer request
            elif len(arg_parts) == 5:
                nick, server = default_peer_args(arg_parts[2:4], buf)
                secret = arg_parts[4]
            elif len(arg_parts) == 6:
                nick, server = default_peer_args(arg_parts[2:4], buf)
                secret = arg_parts[5]
                question = arg_parts[4]
            else:
                return weechat.WEECHAT_RC_ERROR

            context = get_server_context(server, nick)

            if secret:
                secret = PYVER.to_str(secret)
            if question:
                question = PYVER.to_str(question)

            try:
                context.smpInit(secret, question)
            except potr.context.NotEncryptedError:
                context.print_buffer(
                    'There is currently no encrypted session with {0}.'.format(
                        context.peer), 'error')
            else:
                if question:
                    context.print_buffer('SMP challenge sent...')
                else:
                    context.print_buffer('SMP question sent...')
                context.in_smp = True
                result = weechat.WEECHAT_RC_OK

        elif action == 'abort':
            # Nickname and server are not specified
            if len(arg_parts) == 2:
                nick, server = default_peer_args([], buf)
            # Nickname and server are specified
            elif len(arg_parts) == 4:
                nick, server = default_peer_args(arg_parts[2:4], buf)
            else:
                return weechat.WEECHAT_RC_ERROR

            context = get_server_context(server, nick)

            if context.in_smp:
                try:
                    context.smpAbort()
                except potr.context.NotEncryptedError:
                    context.print_buffer(
                        'There is currently no encrypted session with {0}.'
                        .format(context.peer), 'error')
                else:
                    debug('SMP aborted')
                    context.smp_finish('SMP aborted.')
                    result = weechat.WEECHAT_RC_OK

    elif len(arg_parts) in (1, 3) and arg_parts[0] == 'trust':
        nick, server = default_peer_args(arg_parts[1:3], buf)

        if nick is not None and server is not None:
            context = get_server_context(server, nick)

            if context.crypto.theirPubkey is not None:
                context.setCurrentTrust('verified')
                context.print_buffer('{peer} is now authenticated.'.format(
                    peer=context.peer))

                weechat.bar_item_update(SCRIPT_NAME)
            else:
                context.print_buffer(
                    'No fingerprint for {peer}. Start an OTR conversation '
                    'first: /otr start'.format(peer=context.peer),
                    'error')

            result = weechat.WEECHAT_RC_OK
    elif len(arg_parts) in (1, 3) and arg_parts[0] == 'distrust':
        nick, server = default_peer_args(arg_parts[1:3], buf)

        if nick is not None and server is not None:
            context = get_server_context(server, nick)

            if context.crypto.theirPubkey is not None:
                context.setCurrentTrust('')
                context.print_buffer(
                    '{peer} is now de-authenticated.'.format(
                        peer=context.peer))

                weechat.bar_item_update(SCRIPT_NAME)
            else:
                context.print_buffer(
                    'No fingerprint for {peer}. Start an OTR conversation '
                    'first: /otr start'.format(peer=context.peer), 'error')

            result = weechat.WEECHAT_RC_OK

    elif len(arg_parts) in (1, 2) and arg_parts[0] == 'log':
        nick, server = default_peer_args([], buf)
        if len(arg_parts) == 1:
            if nick is not None and server is not None:
                context = get_server_context(server, nick)

                if context.is_encrypted():
                    if context.is_logged():
                        context.print_buffer(
                            'This conversation is currently being logged.',
                            'warning')
                        result = weechat.WEECHAT_RC_OK

                    else:
                        context.print_buffer(
                            'This conversation is currently NOT being logged.')
                        result = weechat.WEECHAT_RC_OK
                else:
                    context.print_buffer(
                        'OTR LOG: Not in an OTR session', 'error')
                    result = weechat.WEECHAT_RC_OK

            else:
                print_buffer('', 'OTR LOG: Not in an OTR session', 'error')
                result = weechat.WEECHAT_RC_OK

        if len(arg_parts) == 2:
            if nick is not None and server is not None:
                context = get_server_context(server, nick)

                if arg_parts[1] == 'start' and \
                        not context.is_logged() and \
                        context.is_encrypted():
                    if context.previous_log_level is None:
                        context.previous_log_level = context.get_log_level()
                    context.print_buffer(
                        'From this point on, this conversation will be '
                        'logged. Please keep in mind that by doing so you '
                        'are potentially putting yourself and your '
                        'interlocutor at risk. You can disable this by doing '
                        '/otr log stop',
                        'warning')
                    weechat.command(buf, '/mute logger set 9')
                    result = weechat.WEECHAT_RC_OK

                elif arg_parts[1] == 'stop' and \
                        context.is_logged() and \
                        context.is_encrypted():
                    if context.previous_log_level is None:
                        context.previous_log_level = context.get_log_level()
                    weechat.command(buf, '/mute logger set 0')
                    context.print_buffer(
                        'From this point on, this conversation will NOT be '
                        'logged ANYMORE.')
                    result = weechat.WEECHAT_RC_OK

                elif not context.is_encrypted():
                    context.print_buffer(
                        'OTR LOG: Not in an OTR session', 'error')
                    result = weechat.WEECHAT_RC_OK

                else:
                    # Don't need to do anything.
                    result = weechat.WEECHAT_RC_OK

            else:
                print_buffer('', 'OTR LOG: Not in an OTR session', 'error')

    elif len(arg_parts) in (1, 2, 3, 4) and arg_parts[0] == 'policy':
        if len(arg_parts) == 1:
            nick, server = default_peer_args([], buf)

            if nick is not None and server is not None:
                context = get_server_context(server, nick)

                context.print_buffer(context.format_policies())
            else:
                prnt('', format_default_policies())

            result = weechat.WEECHAT_RC_OK

        elif len(arg_parts) == 2 and arg_parts[1].lower() == 'default':
            nick, server = default_peer_args([], buf)

            if nick is not None and server is not None:
                context = get_server_context(server, nick)

                context.print_buffer(format_default_policies())
            else:
                prnt('', format_default_policies())

            result = weechat.WEECHAT_RC_OK

        elif len(arg_parts) == 3 and arg_parts[1].lower() in POLICIES:
            nick, server = default_peer_args([], buf)

            if nick is not None and server is not None:
                context = get_server_context(server, nick)

                policy_var = context.policy_config_option(arg_parts[1].lower())

                command('', '/set {policy} {value}'.format(
                    policy=policy_var,
                    value=arg_parts[2]))

                context.print_buffer(context.format_policies())

                result = weechat.WEECHAT_RC_OK

        elif len(arg_parts) == 4 and \
            arg_parts[1].lower() == 'default' and \
            arg_parts[2].lower() in POLICIES:
            nick, server = default_peer_args([], buf)

            policy_var = "otr.policy.default." + arg_parts[2].lower()

            command('', '/set {policy} {value}'.format(
                policy=policy_var,
                value=arg_parts[3]))

            if nick is not None and server is not None:
                context = get_server_context(server, nick)

                context.print_buffer(format_default_policies())
            else:
                prnt('', format_default_policies())

            result = weechat.WEECHAT_RC_OK
    elif len(arg_parts) in (1, 2) and arg_parts[0] == 'fingerprint':
        if len(arg_parts) == 1:
            show_account_fingerprints()
            result = weechat.WEECHAT_RC_OK
        elif len(arg_parts) == 2:
            if arg_parts[1] == 'all':
                show_peer_fingerprints()
            else:
                show_peer_fingerprints(grep=arg_parts[1])
            result = weechat.WEECHAT_RC_OK

    return result

def otr_statusbar_cb(data, item, window):
    """Update the statusbar."""
    if window:
        buf = weechat.window_get_pointer(window, 'buffer')
    else:
        # If the bar item is in a root bar that is not in a window, window
        # will be empty.
        buf = weechat.current_buffer()

    if not buffer_is_private(buf):
        return ''

    local_user = irc_user(
        buffer_get_string(buf, 'localvar_nick'),
        buffer_get_string(buf, 'localvar_server'))

    remote_user = irc_user(
        buffer_get_string(buf, 'localvar_channel'),
        buffer_get_string(buf, 'localvar_server'))

    context = get_context(local_user, remote_user)

    encrypted_str = config_string('look.bar.state.encrypted')
    unencrypted_str = config_string('look.bar.state.unencrypted')
    authenticated_str = config_string('look.bar.state.authenticated')
    unauthenticated_str = config_string('look.bar.state.unauthenticated')
    logged_str = config_string('look.bar.state.logged')
    notlogged_str = config_string('look.bar.state.notlogged')

    bar_parts = []

    if context.is_encrypted():
        if encrypted_str:
            bar_parts.append(''.join([
                config_color('status.encrypted'),
                encrypted_str,
                config_color('status.default')]))

        if context.is_verified():
            if authenticated_str:
                bar_parts.append(''.join([
                    config_color('status.authenticated'),
                    authenticated_str,
                    config_color('status.default')]))
        elif unauthenticated_str:
            bar_parts.append(''.join([
                config_color('status.unauthenticated'),
                unauthenticated_str,
                config_color('status.default')]))

        if context.is_logged():
            if logged_str:
                bar_parts.append(''.join([
                    config_color('status.logged'),
                    logged_str,
                    config_color('status.default')]))
        elif notlogged_str:
            bar_parts.append(''.join([
                config_color('status.notlogged'),
                notlogged_str,
                config_color('status.default')]))

    elif unencrypted_str:
        bar_parts.append(''.join([
            config_color('status.unencrypted'),
            unencrypted_str,
            config_color('status.default')]))

    result = config_string('look.bar.state.separator').join(bar_parts)

    if result:
        result = '{color}{prefix}{result}'.format(
            color=config_color('status.default'),
            prefix=config_string('look.bar.prefix'),
            result=result)

    if context.is_encrypted():
        weechat.buffer_set(buf, 'localvar_set_otr_encrypted', 'true')
    else:
        weechat.buffer_set(buf, 'localvar_set_otr_encrypted', 'false')

    if context.is_verified():
        weechat.buffer_set(buf, 'localvar_set_otr_authenticated', 'true')
    else:
        weechat.buffer_set(buf, 'localvar_set_otr_authenticated', 'false')

    if context.is_logged():
        weechat.buffer_set(buf, 'localvar_set_otr_logged', 'true')
    else:
        weechat.buffer_set(buf, 'localvar_set_otr_logged', 'false')

    return result

def bar_config_update_cb(data, option):
    """Callback for updating the status bar when its config changes."""
    weechat.bar_item_update(SCRIPT_NAME)

    return weechat.WEECHAT_RC_OK

def policy_completion_cb(data, completion_item, buf, completion):
    """Callback for policy tab completion."""
    for policy in POLICIES:
        weechat.hook_completion_list_add(
            completion, policy, 0, weechat.WEECHAT_LIST_POS_SORT)

    return weechat.WEECHAT_RC_OK

def policy_create_option_cb(data, config_file, section, name, value):
    """Callback for creating a new policy option when the user sets one
    that doesn't exist."""
    weechat.config_new_option(
        config_file, section, name, 'boolean', '', '', 0, 0, value, value, 0,
        '', '', '', '', '', '')

    return weechat.WEECHAT_CONFIG_OPTION_SET_OK_CHANGED

def logger_level_update_cb(data, option, value):
    """Callback called when any logger level changes."""
    weechat.bar_item_update(SCRIPT_NAME)

    return weechat.WEECHAT_RC_OK

def buffer_switch_cb(data, signal, signal_data):
    """Callback for buffer switched.

    Used for updating the status bar item when it is in a root bar.
    """
    weechat.bar_item_update(SCRIPT_NAME)

    return weechat.WEECHAT_RC_OK

def buffer_closing_cb(data, signal, signal_data):
    """Callback for buffer closed.

    It closes the OTR session when the buffer is about to be closed.
    """
    result = weechat.WEECHAT_RC_ERROR
    nick, server = default_peer_args([], signal_data)

    if nick is not None and server is not None:
        context = get_server_context(server, nick)
        context.disconnect()

        result = weechat.WEECHAT_RC_OK
    return result

def init_config():
    """Set up configuration options and load config file."""
    global CONFIG_FILE
    CONFIG_FILE = weechat.config_new(SCRIPT_NAME, '', '')

    global CONFIG_SECTIONS
    CONFIG_SECTIONS = {}

    CONFIG_SECTIONS['general'] = weechat.config_new_section(
        CONFIG_FILE, 'general', 0, 0, '', '', '', '', '', '', '', '', '', '')

    for option, typ, desc, default in [
            ('debug',
             'boolean',
             'OTR script debugging',
             'off'),
            ('hints',
             'boolean',
             'Give helpful hints how to use this script and how to stay '
             'secure while using OTR (recommended)',
             'on'),
            ('defaultkey',
             'string',
             'default private key to use for new accounts (nick@server)',
             ''),
            ('no_send_tag_regex',
             'string',
             'do not OTR whitespace tag messages to nicks matching this regex '
             '(case insensitive)',
             '^(alis|chanfix|global|.+serv|\*.+)$'),
        ]:
        weechat.config_new_option(
            CONFIG_FILE, CONFIG_SECTIONS['general'], option, typ, desc, '', 0,
            0, default, default, 0, '', '', '', '', '', '')

    CONFIG_SECTIONS['color'] = weechat.config_new_section(
        CONFIG_FILE, 'color', 0, 0, '', '', '', '', '', '', '', '', '', '')

    for option, desc, default, update_cb in [
            ('status.default',
             'status bar default color',
             'default',
             'bar_config_update_cb'),
            ('status.encrypted',
             'status bar encrypted indicator color',
             'green',
             'bar_config_update_cb'),
            ('status.unencrypted',
             'status bar unencrypted indicator color',
             'lightred',
             'bar_config_update_cb'),
            ('status.authenticated',
             'status bar authenticated indicator color',
             'green',
             'bar_config_update_cb'),
            ('status.unauthenticated',
             'status bar unauthenticated indicator color',
             'lightred',
             'bar_config_update_cb'),
            ('status.logged',
             'status bar logged indicator color',
             'lightred',
             'bar_config_update_cb'),
            ('status.notlogged',
             'status bar not logged indicator color',
             'green',
             'bar_config_update_cb'),
            ('buffer.hint',
             'text color for hints',
             'lightblue',
             ''),
            ('buffer.info',
             'text color for informational messages',
             'default',
             ''),
            ('buffer.success',
             'text color for success messages',
             'lightgreen',
             ''),
            ('buffer.warning',
             'text color for warnings',
             'yellow',
             ''),
            ('buffer.error',
             'text color for errors',
             'lightred',
             ''),
        ]:
        weechat.config_new_option(
            CONFIG_FILE, CONFIG_SECTIONS['color'], option, 'color', desc, '', 0,
            0, default, default, 0, '', '', update_cb, '', '', '')

    CONFIG_SECTIONS['look'] = weechat.config_new_section(
        CONFIG_FILE, 'look', 0, 0, '', '', '', '', '', '', '', '', '', '')

    for option, desc, default, update_cb in [
            ('bar.prefix',
             'prefix for OTR status bar item',
             'OTR:',
             'bar_config_update_cb'),
            ('bar.state.encrypted',
             'shown in status bar when conversation is encrypted',
             'SEC',
             'bar_config_update_cb'),
            ('bar.state.unencrypted',
             'shown in status bar when conversation is not encrypted',
             '!SEC',
             'bar_config_update_cb'),
            ('bar.state.authenticated',
             'shown in status bar when peer is authenticated',
             'AUTH',
             'bar_config_update_cb'),
            ('bar.state.unauthenticated',
             'shown in status bar when peer is not authenticated',
             '!AUTH',
             'bar_config_update_cb'),
            ('bar.state.logged',
             'shown in status bar when peer conversation is being logged to '
             'disk',
             'LOG',
             'bar_config_update_cb'),
            ('bar.state.notlogged',
             'shown in status bar when peer conversation is not being logged '
             'to disk',
             '!LOG',
             'bar_config_update_cb'),
            ('bar.state.separator',
             'separator for states in the status bar',
             ',',
             'bar_config_update_cb'),
            ('prefix',
             'prefix used for messages from otr (note: content is evaluated, '
             'see /help eval)',
             '${color:default}:! ${color:brown}otr${color:default} !:',
             ''),
        ]:
        weechat.config_new_option(
            CONFIG_FILE, CONFIG_SECTIONS['look'], option, 'string', desc, '',
            0, 0, default, default, 0, '', '', update_cb, '', '', '')

    CONFIG_SECTIONS['policy'] = weechat.config_new_section(
        CONFIG_FILE, 'policy', 1, 1, '', '', '', '', '', '',
        'policy_create_option_cb', '', '', '')

    for option, desc, default in [
            ('default.allow_v2',
             'default allow OTR v2 policy',
             'on'),
            ('default.require_encryption',
             'default require encryption policy',
             'off'),
            ('default.log',
             'default enable logging to disk',
             'off'),
            ('default.send_tag',
             'default send tag policy',
             'off'),
            ('default.html_escape',
             'default HTML escape policy',
             'off'),
            ('default.html_filter',
             'default HTML filter policy',
             'on'),
        ]:
        weechat.config_new_option(
            CONFIG_FILE, CONFIG_SECTIONS['policy'], option, 'boolean', desc, '',
            0, 0, default, default, 0, '', '', '', '', '', '')

    weechat.config_read(CONFIG_FILE)

def free_all_config():
    """Free all config options, sections and config file."""
    for section in CONFIG_SECTIONS.values():
        weechat.config_section_free_options(section)
        weechat.config_section_free(section)

    weechat.config_free(CONFIG_FILE)

def create_dir():
    """Create the OTR subdirectory in the WeeChat config directory if it does
    not exist."""
    if not os.path.exists(OTR_DIR):
        weechat.mkdir_home(OTR_DIR_NAME, 0o700)

def git_info():
    """If this script is part of a git repository return the repo state."""
    result = None
    script_dir = os.path.dirname(os.path.realpath(__file__))
    git_dir = os.path.join(script_dir, '.git')
    if os.path.isdir(git_dir):
        import subprocess
        try:
            # We can't use check_output here without breaking compatibility
            # for Python 2.6, but we ignore the return value anyway, so Popen
            # is only slightly more complicated:
            process = subprocess.Popen([
                'git',
                '--git-dir', git_dir,
                '--work-tree', script_dir,
                'describe', '--dirty', '--always',
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = process.communicate()[0]
            if output:
                result = PYVER.to_unicode(output).lstrip('v').rstrip()
        except OSError:
            pass

    return result

def weechat_version_ok():
    """Check if the WeeChat version is compatible with this script.

    If WeeChat version < 0.4.2 log an error to the core buffer and return
    False. Otherwise return True.
    """
    weechat_version = weechat.info_get('version_number', '') or 0
    if int(weechat_version) < 0x00040200:
        error_message = (
            '{script_name} requires WeeChat version >= 0.4.2. The current '
            'version is {current_version}.').format(
                script_name=SCRIPT_NAME,
                current_version=weechat.info_get('version', ''))
        prnt('', error_message)
        return False
    return True

SCRIPT_VERSION = git_info() or SCRIPT_VERSION

def dependency_versions():
    """Return a string containing the versions of all dependencies."""
    return ('weechat-otr {script_version}, '
            'potr {potr_major}.{potr_minor}.{potr_patch}-{potr_sub}, '
            'Python {python_version}, '
            'WeeChat {weechat_version}'
           ).format(
               script_version=SCRIPT_VERSION,
               potr_major=potr.VERSION[0],
               potr_minor=potr.VERSION[1],
               potr_patch=potr.VERSION[2],
               potr_sub=potr.VERSION[3],
               python_version=platform.python_version(),
               weechat_version=weechat.info_get('version', ''))

def excepthook(typ, value, tracebak):
    """Add dependency versions to tracebacks."""
    sys.stderr.write('Versions: ')
    sys.stderr.write(dependency_versions())
    sys.stderr.write('\n')

    sys.__excepthook__(typ, value, tracebak)

sys.excepthook = excepthook

if weechat.register(
        SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENCE, SCRIPT_DESC,
        'shutdown', ''):
    if weechat_version_ok():
        init_config()

        OTR_DIR = os.path.join(info_get('weechat_dir', ''), OTR_DIR_NAME)
        create_dir()

        ACCOUNTS = AccountDict()

        weechat.hook_modifier('irc_in_privmsg', 'message_in_cb', '')
        weechat.hook_modifier('irc_out_privmsg', 'message_out_cb', '')

        weechat.hook_command(
            SCRIPT_NAME, SCRIPT_HELP,
            'start [NICK SERVER] || '
            'refresh [NICK SERVER] || '
            'finish [NICK SERVER] || '
            'end [NICK SERVER] || '
            'status [NICK SERVER] || '
            'smp ask [NICK SERVER] [QUESTION] SECRET || '
            'smp respond [NICK SERVER] SECRET || '
            'smp abort [NICK SERVER] || '
            'trust [NICK SERVER] || '
            'distrust [NICK SERVER] || '
            'log [start|stop] || '
            'policy [POLICY on|off] || '
            'fingerprint [SEARCH|all]',
            '',
            'start %(nick) %(irc_servers) %-||'
            'refresh %(nick) %(irc_servers) %-||'
            'finish %(nick) %(irc_servers) %-||'
            'end %(nick) %(irc_servers) %-||'
            'status %(nick) %(irc_servers) %-||'
            'smp ask|respond %(nick) %(irc_servers) %-||'
            'smp abort %(nick) %(irc_servers) %-||'
            'trust %(nick) %(irc_servers) %-||'
            'distrust %(nick) %(irc_servers) %-||'
            'log start|stop %-||'
            'policy %(otr_policy) on|off %-||'
            'fingerprint all %-||',
            'command_cb',
            '')

        weechat.hook_completion(
            'otr_policy', 'OTR policies', 'policy_completion_cb', '')

        weechat.hook_config('logger.level.irc.*', 'logger_level_update_cb', '')

        weechat.hook_signal('buffer_switch', 'buffer_switch_cb', '')
        weechat.hook_signal('buffer_closing', 'buffer_closing_cb', '')

        OTR_STATUSBAR = weechat.bar_item_new(
            SCRIPT_NAME, 'otr_statusbar_cb', '')
        weechat.bar_item_update(SCRIPT_NAME)
