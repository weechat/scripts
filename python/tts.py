# -*- coding: utf-8 -*-
#
# Project:     weechat-tts
# Homepage:    https://git.hashtagueule.fr/raspbeguy/weechat-tts
# Description: Text-to-speech script.
#              Requires a TTS engine such as espeak or picospeaker.
# License:     MIT (see below)
#
# Copyright (c) 2017 by raspbeguy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import subprocess
import sys
import time


# Ensure that we are running under WeeChat.
try:
    import weechat
except ImportError:
    print('This script has to run under WeeChat (https://weechat.org/).')
    sys.exit(1)


# Name of the script.
SCRIPT_NAME = 'tts'

# Author of the script.
SCRIPT_AUTHOR = 'raspbeguy'

# Version of the script.
SCRIPT_VERSION = '0.2.1'

# License under which the script is distributed.
SCRIPT_LICENSE = 'MIT'

# Description of the script.
SCRIPT_DESC = 'Uses a TTS engine to pronounce messages'

# Name of a function to be called when the script is unloaded.
SCRIPT_SHUTDOWN_FUNC = ''

# Used character set (utf-8 by default).
SCRIPT_CHARSET = ''

# Script options.
OPTIONS = {
    'tts_engine': (
        'espeak',
        'TTS engine to use.'
        'Valid values: espeak, festival, picospeaker'
    ),
    'language': (
        '',
        'Language used by the TTS engine'
    ),
    'tts_on_highlights': (
        'on',
        'Pronounce on highlights.'
    ),
    'tts_on_privmsgs': (
        'on',
        'Pronounce private messages.'
    ),
    'tts_on_filtered_messages': (
        'off',
        'Pronounce also filtered (hidden) messages.'
    ),
    'tts_when_away': (
        'on',
        'Pronounce also when away.'
    ),
    'tts_for_current_buffer': (
        'on',
        'Pronounce also for the currently active buffer.'
    ),
    'tts_on_all_messages_in_buffers': (
        '',
        'A comma-separated list of buffers in which you want to '
        'pronounce all messages that appear in them.'
    ),
    'min_notification_delay': (
        '500',
        'A minimal delay between successive spoken message from the same '
        'buffer (in milliseconds; set to 0 to show all notifications).'
    ),
    'ignore_messages_tagged_with': (
        # irc_join:      Joined IRC
        # irc_quit:      Quit IRC
        # irc_part:      Parted a channel
        # irc_status:    Status messages
        # irc_nick_back: A nick is back on server
        # irc_401:       No such nick/channel
        # irc_402:       No such server
        'irc_join,irc_quit,irc_part,irc_status,irc_nick_back,irc_401,irc_402',
        'A comma-separated list of message tags for which no text '
        'should be said.'
    ),
    'ignore_buffers': (
        '',
        'A comma-separated list of buffers from which no text should be said.'
    ),
    'ignore_buffers_starting_with': (
        '',
        'A comma-separated list of buffer prefixes from which no '
        'text should be said'
    ),
    'ignore_nicks': (
        '',
        'A comma-separated list of nicks from which no text should '
        'be said.'
    ),
    'ignore_nicks_starting_with': (
        '',
        'A comma-separated list of nick prefixes from which no '
        'text should be said.'
    ),
    'tts_url': (
        'off',
        "Pronounce URLs."
    ),
    'format_chan_message': (
         '%(nick)s says in %(chan)s: %(body)s.',
         'Text spoken for a message in a regular channel.'
    ),
    'format_priv_message': (
         '%(nick)s says: %(body)s.',
         'Text spoken for a message in a private conversation.'
    ),
}

def default_value_of(option):
    """Returns the default value of the given option."""
    return OPTIONS[option][0]


def add_default_value_to(description, default_value):
    """Adds the given default value to the given option description."""
    # All descriptions end with a period, so do not add another period.
    return '{} Default: {}.'.format(
        description,
        default_value if default_value else '""'
    )


def nick_that_sent_message(tags, prefix):
    """Returns a nick that sent the message based on the given data passed to
    the callback.
    """
    # 'tags' is a comma-separated list of tags that WeeChat passed to the
    # callback. It should contain a tag of the following form: nick_XYZ, where
    # XYZ is the nick that sent the message.
    for tag in tags:
        if tag.startswith('nick_'):
            return tag[5:]

    # There is no nick in the tags, so check the prefix as a fallback.
    # 'prefix' (str) is the prefix of the printed line with the message.
    # Usually (but not always), it is a nick with an optional mode (e.g. on
    # IRC, @ denotes an operator and + denotes a user with voice). We have to
    # remove the mode (if any) before returning the nick.
    # Strip also a space as some protocols (e.g. Matrix) may start prefixes
    # with a space. It probably means that the nick has no mode set.
    if prefix.startswith(('~', '&', '@', '%', '+', '-', ' ')):
        return prefix[1:]

    return prefix


def parse_tags(tags):
    """Parses the given "list" of tags (str) from WeeChat into a list.
    """
    return tags.split(',')


def message_printed_callback(data, buffer, date, tags, is_displayed,
                             is_highlight, prefix, message):
    """A callback when a message is printed."""
    is_displayed = int(is_displayed)
    is_highlight = int(is_highlight)
    tags = parse_tags(tags)
    nick = nick_that_sent_message(tags, prefix)

    if message_should_be_voiced(buffer, tags, nick, is_displayed, is_highlight):
        text = prepare_tts(buffer, nick, message)
        tts(text)

    return weechat.WEECHAT_RC_OK


def message_should_be_voiced(buffer, tags, nick, is_displayed, is_highlight):
    """Should a notification be sent?"""
    if message_should_be_voiced_disregarding_time(buffer, tags, nick,
                                                     is_displayed, is_highlight):
        # The following function should be called only when the notification
        # should be sent (it updates the last notification time).
        if not is_below_min_notification_delay(buffer):
            return True
    return False


def message_should_be_voiced_disregarding_time(buffer, tags, nick,
                                                  is_displayed, is_highlight):
    """Should a notification be sent when not considering time?"""
    if not nick:
        # A nick is required to form a correct notification source/message.
        return False

    if i_am_author_of_message(buffer, nick):
        return False

    if not is_displayed:
        if not tts_on_filtered_messages():
            return False

    if buffer == weechat.current_buffer():
        if not tts_for_current_buffer():
            return False

    if is_away(buffer):
        if not tts_when_away():
            return False

    if ignore_messages_tagged_with(tags):
        return False

    if ignore_messages_from_nick(nick):
        return False

    if ignore_messages_from_buffer(buffer):
        return False

    if is_private_message(buffer):
        return tts_on_private_messages()

    if is_highlight:
        return tts_on_highlights()

    if tts_on_all_messages_in_buffer(buffer):
        return True

    return False


def is_below_min_notification_delay(buffer):
    """Is a notification in the given buffer below the minimal delay between
    successive notifications from the same buffer?

    When called, this function updates the time of the last notification.
    """
    # We store the time of the last notification in a buffer-local variable to
    # make it persistent over the lifetime of this plugin.
    LAST_NOTIFICATION_TIME_VAR = 'last_tts_time'
    last_notification_time = buffer_get_float(
        buffer,
        'localvar_' + LAST_NOTIFICATION_TIME_VAR
    )

    min_notification_delay = weechat.config_get_plugin('min_notification_delay')
    # min_notification_delay is in milliseconds (str). To compare it with
    # last_notification_time (float in seconds), we have to convert it to
    # seconds (float).
    min_notification_delay = float(min_notification_delay) / 1000

    current_time = time.time()

    # We have to update the last notification time before returning the result.
    buffer_set_float(
        buffer,
        'localvar_set_' + LAST_NOTIFICATION_TIME_VAR,
        current_time
    )

    return (min_notification_delay > 0 and
            current_time - last_notification_time < min_notification_delay)


def buffer_get_float(buffer, property):
    """A variant of weechat.buffer_get_x() for floats.

    This variant is needed because WeeChat supports only buffer_get_string()
    and buffer_get_int().
    """
    value = weechat.buffer_get_string(buffer, property)
    return float(value) if value else 0.0


def buffer_set_float(buffer, property, value):
    """A variant of weechat.buffer_set() for floats.

    This variant is needed because WeeChat supports only integers and strings.
    """
    weechat.buffer_set(buffer, property, str(value))


def names_for_buffer(buffer):
    """Returns a list of all names for the given buffer."""
    # The 'buffer' parameter passed to our callback is actually the buffer's ID
    # (e.g. '0x2719cf0'). We have to check its name (e.g. 'freenode.#weechat')
    # and short name (e.g. '#weechat') because these are what users specify in
    # their configs.
    buffer_names = []

    full_name = weechat.buffer_get_string(buffer, 'name')
    if full_name:
        buffer_names.append(full_name)

    short_name = weechat.buffer_get_string(buffer, 'short_name')
    if short_name:
        buffer_names.append(short_name)
        # Consider >channel and #channel to be equal buffer names. The reason
        # is that the https://github.com/rawdigits/wee-slack plugin replaces
        # '#' with '>' to indicate that someone in the buffer is typing. This
        # fixes the behavior of several configuration options (e.g.
        # 'tts_on_all_messages_in_buffers') when weechat_notify_send is used
        # together with the wee_slack plugin.
        #
        # Note that this is only needed to be done for the short name. Indeed,
        # the full name always stays unchanged.
        if short_name.startswith('>'):
            buffer_names.append('#' + short_name[1:])

    return buffer_names


def tts_for_current_buffer():
    """Should we also send notifications for the current buffer?"""
    return weechat.config_get_plugin('tts_for_current_buffer') == 'on'


def tts_on_highlights():
    """Should we send notifications on highlights?"""
    return weechat.config_get_plugin('tts_on_highlights') == 'on'


def tts_on_private_messages():
    """Should we send notifications on private messages?"""
    return weechat.config_get_plugin('tts_on_privmsgs') == 'on'


def tts_on_filtered_messages():
    """Should we also send notifications for filtered (hidden) messages?"""
    return weechat.config_get_plugin('tts_on_filtered_messages') == 'on'


def tts_when_away():
    """Should we also send notifications when away?"""
    return weechat.config_get_plugin('tts_when_away') == 'on'


def is_away(buffer):
    """Is the user away?"""
    return weechat.buffer_get_string(buffer, 'localvar_away') != ''


def is_private_message(buffer):
    """Has a private message been sent?"""
    return weechat.buffer_get_string(buffer, 'localvar_type') == 'private'


def i_am_author_of_message(buffer, nick):
    """Am I (the current WeeChat user) the author of the message?"""
    return weechat.buffer_get_string(buffer, 'localvar_nick') == nick


def split_option_value(option, separator=','):
    """Splits the value of the given plugin option by the given separator and
    returns the result in a list.
    """
    values = weechat.config_get_plugin(option)
    return [value.strip() for value in values.split(separator)]

def get_format_chan_message():
    return weechat.config_get_plugin('format_chan_message')

def get_format_priv_message():
    return weechat.config_get_plugin('format_priv_message')

def ignore_messages_tagged_with(tags):
    """Should notifications be ignored for a message tagged with the given
    tags?
    """
    ignored_tags = split_option_value('ignore_messages_tagged_with')
    for ignored_tag in ignored_tags:
        for tag in tags:
            if tag == ignored_tag:
                return True
    return False


def ignore_messages_from_buffer(buffer):
    """Should notifications from the given buffer be ignored?"""
    buffer_names = names_for_buffer(buffer)

    for buffer_name in buffer_names:
        if buffer_name and buffer_name in ignored_buffers():
            return True

    for buffer_name in buffer_names:
        for prefix in ignored_buffer_prefixes():
            if prefix and buffer_name and buffer_name.startswith(prefix):
                return True

    return False


def ignored_buffers():
    """A generator of buffers from which notifications should be ignored."""
    for buffer in split_option_value('ignore_buffers'):
        yield buffer


def ignored_buffer_prefixes():
    """A generator of buffer prefixes from which notifications should be
    ignored.
    """
    for prefix in split_option_value('ignore_buffers_starting_with'):
        yield prefix


def ignore_messages_from_nick(nick):
    """Should notifications from the given nick be ignored?"""
    if nick in ignored_nicks():
        return True

    for prefix in ignored_nick_prefixes():
        if prefix and nick.startswith(prefix):
            return True

    return False


def ignored_nicks():
    """A generator of nicks from which notifications should be ignored."""
    for nick in split_option_value('ignore_nicks'):
        yield nick


def ignored_nick_prefixes():
    """A generator of nick prefixes from which notifications should be
    ignored.
    """
    for prefix in split_option_value('ignore_nicks_starting_with'):
        yield prefix


def buffers_to_tts_on_all_messages():
    """A generator of buffer names in which the user wants to be notified for
    all messages.
    """
    for buffer in split_option_value('tts_on_all_messages_in_buffers'):
        yield buffer


def tts_on_all_messages_in_buffer(buffer):
    """Does the user want to be notified for all messages in the given buffer?
    """
    buffer_names = names_for_buffer(buffer)
    for buf in buffers_to_tts_on_all_messages():
        if buf in buffer_names:
            return True
    return False

def remove_urls(body):
    import re
    return re.sub(r'https?:\/\/\S+[\ \t]', '', body)

def prepare_tts(buffer, nick, message):
    """Prepares the text to be spoken."""
    chan = ""
    if is_private_message(buffer):
        unformatted_message = get_format_priv_message()
    else:
        unformatted_message = get_format_chan_message()
        chan = weechat.buffer_get_string(buffer, 'short_name')
    if weechat.config_get_plugin('tts_url') == 'off':
        message = remove_urls(message)
    return unformatted_message % {'nick':nick, 'body': message, 'chan': chan}

def my_process_cb(data, command, return_code, out, err):
    if return_code == weechat.WEECHAT_HOOK_PROCESS_ERROR:
        weechat.prnt("", "Error with command '%s'" % command)
        return weechat.WEECHAT_RC_OK
    if return_code > 0:
        weechat.prnt("", "return_code = %d" % return_code)
    if err != "":
        weechat.prnt("", "stderr: %s" % err)
    return weechat.WEECHAT_RC_OK

def tts(text):
    """Pronounce the text"""
    engine = weechat.config_get_plugin('tts_engine')
    lang = weechat.config_get_plugin('language')
    if engine == 'espeak':
        args = {'arg1':text}
        if lang:
            args['arg2'] = '-v'
            args['arg3'] = lang
        hook = weechat.hook_process_hashtable('espeak',args,0,'my_process_cb','')
    elif engine == 'festival':
        args = {'stdin':'1', 'arg1':'festival', 'arg2':'--tts'}
        if lang:
            args['arg3'] = '--language'
            args['arg4'] = lang
        hook = weechat.hook_process_hashtable('festival',args,0,'my_process_cb','')
        weechat.hook_set(hook, "stdin", text)
        weechat.hook_set(hook, "stdin_close", "")
    elif engine == 'picospeaker':
        args = {'stdin':'1'}
        if lang:
            args['arg1'] = '-l'
            args['arg2'] = lang
        hook = weechat.hook_process_hashtable('picospeaker',args,0,'my_process_cb','')
        weechat.hook_set(hook, "stdin", text)
        weechat.hook_set(hook, "stdin_close", "")

if __name__ == '__main__':
    # Registration.
    weechat.register(
        SCRIPT_NAME,
        SCRIPT_AUTHOR,
        SCRIPT_VERSION,
        SCRIPT_LICENSE,
        SCRIPT_DESC,
        SCRIPT_SHUTDOWN_FUNC,
        SCRIPT_CHARSET
    )

    # Initialization.
    for option, (default_value, description) in OPTIONS.items():
        description = add_default_value_to(description, default_value)
        weechat.config_set_desc_plugin(option, description)
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

    # Catch all messages on all buffers and strip colors from them before
    # passing them into the callback.
    weechat.hook_print('', '', '', 1, 'message_printed_callback', '')
