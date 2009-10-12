''' Buffer searcher '''
# -*- coding: utf-8 -*-
#
# Copyright (c) 2009 by xt <xt@bash.no>
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

#
# Buffer searcher
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
# 2009-10-12, omero
#   version 0.5: made it python-2.4.x compliant
# 2009-06-23
#   version 0.4: added --exact
# 2009-06-22
#   version 0.4: added --all to help
# 2009-06-17, xt
#   version 0.3: use formatted buffer and prefix. Added --all
# 2009-06-16, sleo
#     version 0.2: find existing grep window, scroll to bottom 
# 2009-05-24, xt <xt@bash.no>
#     version 0.1: initial release

#from __future__ import with_statement # This isn't required in Python 2.6
import weechat as w
import re

SCRIPT_NAME    = "grep"
SCRIPT_AUTHOR  = "xt <xt@bash.no>"
SCRIPT_VERSION = "0.5"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Search in buffer"
SCRIPT_COMMAND = 'grep'

def buffer_input(*kwargs):
    return w.WEECHAT_RC_OK

def buffer_close(*kwargs):
    global search_buffer
    search_buffer =  None
    return w.WEECHAT_RC_OK

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    w.hook_command(SCRIPT_COMMAND,
                         "Buffer searcher",
                         "[--all] [--exact] expression",
                         "  --all: search all buffers with logs\n"
                         "  --exact: only return the exact match, not the matching line\n"
                         "  expression: regular search expression\n",
                         "",
                         "grep_cmd",
                         "")

def irc_nick_find_color(nick):

    color = 0
    for char in nick:
        color += ord(char)

    color %= w.config_integer(w.config_get("weechat.look.color_nicks_number"))
    color = w.config_get('weechat.color.chat_nick_color%02d' %(color+1))
    color = w.config_string(color)
    return '%s%s%s' %(w.color(color), nick, w.color('reset'))

def get_logfilename(buffer):
    ''' Given buffer pointer, finds log filename or returns False '''

    linfolist = w.infolist_get('logger_buffer', '', '')
    logfilename = ''
    log_enabled = False
    while w.infolist_next(linfolist):
        bpointer = w.infolist_pointer(linfolist, 'buffer')
        if bpointer == buffer:
            logfilename = w.infolist_string(linfolist, 'log_filename')
            log_enabled = w.infolist_integer(linfolist, 'log_enabled')
            break
    w.infolist_free(linfolist)

    if not log_enabled:
        return False

    return logfilename

def find_infolist_matching_lines(buffer, matcher, exact):
    ''' if exact is True only return the exact match '''

    matching_lines = []
    infolist = w.infolist_get('buffer_lines', buffer, '')
    while w.infolist_next(infolist):
        message = w.infolist_string(infolist, 'message')
        prefix = w.infolist_string(infolist, 'prefix')
        if exact:
            for match in matcher.findall(message):
                matching_lines.append((
                    w.infolist_time(infolist, 'date'),
                    w.infolist_string(infolist, 'prefix'),
                    match
                    ))
        else:
            if matcher.search(message) or matcher.search(prefix):
                matching_lines.append((
                    w.infolist_time(infolist, 'date'),
                    w.infolist_string(infolist, 'prefix'),
                    w.infolist_string(infolist, 'message'),
                    ))

    w.infolist_free(infolist)

    return matching_lines

def get_matching_lines(buffer, matcher, exact):
    ''' if exact is True only return the exact match '''

    matching_lines = []
    logfilename = get_logfilename(buffer)
    if logfilename:
        f = file(logfilename, 'r')
        for line in f:
            if exact:
                for match in matcher.findall(line):
                    time, prefix = line.split('\t')[0], line.split('\t')[1]
                    matching_lines.append((time, prefix, match))
            else:
                if matcher.findall(line):
                    matching_lines.append(line.split('\t'))
    else:
        matching_lines = find_infolist_matching_lines(buffer, matcher, exact)

    return matching_lines

def get_all_buffers():
    buffers = []
    infolist = w.infolist_get("buffer", "", "")
    while w.infolist_next(infolist):
        buffers.append(w.infolist_pointer(infolist, "pointer"))
    w.infolist_free(infolist)
    return buffers

def grep_cmd(data, buffer, args):
    global search_buffer
    

    if not args:
        w.command('', '/help %s' %SCRIPT_COMMAND)
        return w.WEECHAT_RC_OK

    if ' ' in args and args.startswith('--'):
        sargs = args.split(' ')
        opts = sargs[0:-1]
        pattern = sargs[-1]
    else:
        pattern = args
        opts = ''

    try:
        matcher = re.compile(pattern, re.IGNORECASE)
    except Exception, e:
        w.prnt('', '%s failed (Regex Error): %s' %(SCRIPT_COMMAND, str(e)))
        return w.WEECHAT_RC_OK

    matching_lines = []

    exact = False 
    if '--exact' in opts:
        exact = True

    if '--all' in opts:
        for buffer in get_all_buffers():
            matching_lines += get_matching_lines(buffer, matcher, exact)
    else:
        matching_lines += get_matching_lines(buffer, matcher, exact)


    update_buffer(matching_lines, pattern)

    return w.WEECHAT_RC_OK


def buffer_create():
    global search_buffer
    
    search_buffer = w.buffer_search('python', SCRIPT_COMMAND)
    if not search_buffer:
        search_buffer = w.buffer_new(SCRIPT_COMMAND, "buffer_input", "", "buffer_close", "")
    w.buffer_set(search_buffer, "time_for_each_line", "0")
    w.buffer_set(search_buffer, "nicklist", "0")
    w.buffer_set(search_buffer, "title", "Search output buffer")
    w.buffer_set(search_buffer, "localvar_set_no_log", "1")


def update_buffer(matching_lines, pattern):
    buffer_create()

    w.buffer_clear(search_buffer)

    w.buffer_set(search_buffer, "title", "Search '%s' matched %s lines" % (pattern, len(matching_lines) ))

    for line in matching_lines:
        w.prnt(search_buffer, '%s\t%s %s %s' % (\
            line[0],
            irc_nick_find_color(line[1]),
            w.color('reset'),
            line[2]))

    w.buffer_set(search_buffer, "display", "1")

