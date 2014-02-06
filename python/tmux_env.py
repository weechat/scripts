"""
tmux_env.py -- update weechat environment from tmux

Copyright 2013 Aron Griffis <agriffis@n01se.net>
Released under the terms of the GNU General Public License v3

Description:

    This script propagates environment updates from tmux into the weechat
    process, including the script interpreters.  This allows the process
    environment to follow the tmux client, such as the X DISPLAY variable,
    and the DBUS_SESSION_BUS_ADDRESS used for desktop notifications.

    See https://github.com/agriffis/weechat-tmux-env for full usage
    instructions.

History:

    2013-09-30 Aron Griffis <agriffis@n01se.net>
      version 1: initial release

    2014-02-03 Aron Griffis <agriffis@n01se.net>
      version 2: python 2.6 compatible subprocess.check_output()
"""

from __future__ import absolute_import, unicode_literals

import fnmatch
import os
import subprocess

if not hasattr(subprocess, 'check_output'):
    def check_output(*popenargs, **kwargs):
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd)
        return output
    subprocess.check_output = check_output
    del check_output

import weechat as w

SCRIPT_NAME    = "tmux_env"
SCRIPT_AUTHOR  = "Aron Griffis <agriffis@n01se.net>"
SCRIPT_VERSION = "2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Update weechat environment from tmux"

settings = {
    'interval': '30',  # How often in seconds to check for updates

    # For include/exclude, the bare variable name only refers to
    # environment updates, not removals. For removals, include the variable
    # name prefixed by a minus sign. For example, to add/remove exclusively
    # the DISPLAY variable, include="DISPLAY,-DISPLAY"
    # 
    # Globs are also accepted, so you can ignore all variable removals with
    # exclude="-*"

    'include': '*,-*',  # Env vars to include, default all
    'exclude': '',      # Env vars to exclude, default all
    }

TIMER = None

def set_timer():
    """Update timer hook with new interval"""

    global TIMER
    if TIMER:
        w.unhook(TIMER)
    TIMER = w.hook_timer(int(w.config_get_plugin('interval')) * 1000,
            0, 0, 'timer_cb', '')

def config_cb(data, option, value):
    """Reset timer when interval option is updated"""

    if option.endswith('.interval'):
        set_timer()
    return w.WEECHAT_RC_OK

def timer_cb(buffer, args):
    """Check if tmux is attached, update environment"""

    attached = os.access(SOCK, os.X_OK) # X bit indicates attached
    if attached:
        update_environment()
    return w.WEECHAT_RC_OK

def update_environment():
    """Updates environment from tmux showenv"""

    env = subprocess.check_output(['tmux', 'showenv'])
    for line in env.splitlines():
        name = line.split('=', 1)[0]
        if check_include(name) and not check_exclude(name):
            if name.startswith('-'):
                remove_env(name[1:])
            else:
                add_env(name, line.split('=', 1)[1])

def check_include(name):
    globs = comma_split_config('include')
    return check_match(name, globs)

def check_exclude(name):
    globs = comma_split_config('exclude')
    return check_match(name, globs)

def check_match(name, globs):
    for g in globs:
        if fnmatch.fnmatch(name, g):
            return True

def comma_split_config(name):
    config = w.config_get_plugin(name)
    return filter(None, (s.strip() for s in config.split(',')))

def add_env(name, value):
    old = os.environ.get(name)
    if old != value:
        w.prnt("", "%s: add %s=%r (was %r)" % (SCRIPT_NAME, name, value, old))
        os.environ[name] = value

def remove_env(name):
    old = os.environ.get(name)
    if old is not None:
        w.prnt("", "%s: remove %s (was %r)" % (SCRIPT_NAME, name, old))
        del os.environ[name]

if w.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
        SCRIPT_DESC, '', ''):
    for option, default_value in settings.iteritems():
        if not w.config_is_set_plugin(option):
            w.config_set_plugin(option, default_value)

    global SOCK
    SOCK = None

    if 'TMUX' in os.environ.keys():
        # We are running under tmux
        socket_data = os.environ['TMUX']
        SOCK = socket_data.rsplit(',',2)[0]

    if SOCK:
        w.hook_config("plugins.var.python." + SCRIPT_NAME + ".*",
            "config_cb", "")
        set_timer()
