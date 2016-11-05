# Show differences between old and new topics
# Author: Dafydd Harries <daf@rhydd.org>
# License: GPL3

import re

from itertools import izip_longest

import weechat

SCRIPT_NAME    = "topicdiff"
SCRIPT_AUTHOR  = "Dafydd Harries <daf@rhydd.org>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Show differences between old and new topics."

pending_change_buffer = None
topics = {}

def topic_chunks(s):
    return re.split(r'\s+[-~|]+\s+', s)

def topic_changed(buffer, new_topic):
    if buffer in topics:
        old_chunks = topic_chunks(topics[buffer])
        new_chunks = topic_chunks(new_topic)

        for old_chunk, new_chunk in izip_longest(old_chunks, new_chunks):
            if old_chunk and old_chunk not in new_chunks:
                weechat.prnt(buffer, '%s-\t%s' % (
                    weechat.color('red'),
                    old_chunk
                ))

            if new_chunk and new_chunk not in old_chunks:
                weechat.prnt(buffer, '%s+\t%s' % (
                    weechat.color('green'),
                    new_chunk
                ))

    topics[buffer] = new_topic

def print_332(data, buffer, time, tags, displayed, highlight, prefix, message):
    #weechat.prnt('', 'print: %r' % (a,))
    global pending_change_buffer
    pending_change_buffer = buffer
    return weechat.WEECHAT_RC_OK

def print_topic(
        data, buffer, time, tags, displayed, highlight, prefix, message):
    global pending_change_buffer
    pending_change_buffer = buffer
    return weechat.WEECHAT_RC_OK

def irc_in2_332(data, tags, msg):
    global pending_change_buffer

    if pending_change_buffer is None:
        # Hmm, that's weird.
        #weechat.prnt('', 'no pending buffer :(')
        return weechat.WEECHAT_RC_OK

    match = re.match(r':\S+ 332 \S+ \S+ :(.*)', msg)

    if not match:
        #weechat.prnt('', 'no match :(')
        return weechat.WEECHAT_RC_OK

    new_topic = match.group(1)
    topic_changed(pending_change_buffer, new_topic)
    pending_change_buffer = None
    return weechat.WEECHAT_RC_OK

def irc_in2_topic(data, tags, msg):
    global pending_change_buffer

    #weechat.prnt('', '%r' % ((tags, msg),))

    if pending_change_buffer is None:
        # Hmm, that's weird.
        #weechat.prnt('', 'no pending buffer :(')
        return weechat.WEECHAT_RC_OK

    match = re.match(r':\S+ TOPIC \S+ :(.*)', msg)

    if not match:
        #weechat.prnt('', 'no match :(')
        return weechat.WEECHAT_RC_OK

    new_topic = match.group(1)
    topic_changed(pending_change_buffer, new_topic)
    pending_change_buffer = None
    return weechat.WEECHAT_RC_OK

def register():
    weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
        SCRIPT_LICENSE, SCRIPT_DESC, '', '')

    weechat.hook_print('', 'irc_332', '', 1, 'print_332', '')
    weechat.hook_print('', 'irc_topic', '', 1, 'print_topic', '')
    weechat.hook_signal('*,irc_in2_332', 'irc_in2_332', '')
    weechat.hook_signal('*,irc_in2_topic', 'irc_in2_topic', '')

if __name__ == '__main__':
    register()

