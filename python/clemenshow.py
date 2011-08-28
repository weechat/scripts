"""
Simple weechat script for showing currently playing song from clementine.

Basic install / usage:
place into ~/.weechat/python/autoload
/python load python/autoload/clemenshow.py
/np
"""
SCRIPT_NAME    = "clemenshow"
SCRIPT_AUTHOR  = "Leigh MacDonald <leigh.macdonald@gmail.com>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Clementine now playing script"
SCRIPT_COMMAND = "np"

import sys
from os.path import exists

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat 3.4 or better."
    print "Get WeeChat now at: http://www.weechat.org/"
    sys.exit()
try:
    from dbus import Bus, DBusException
except ImportError:
    print "Please install python-dbus"
    sys.exit()

bus = Bus(Bus.TYPE_SESSION)

def get_type(path):
    p = path.split(".")
    return p[len(p)-1].upper()

#@DebugArgs
def np_command(data, buffer, args):
    try:
        c = bus.get_object('org.mpris.clementine', '/Player')
        f = c.GetMetadata()
        weechat.command(buffer, "/me %s | %s [%s@%dkbps/%dHz]" % (f['artist'].encode('UTF-8'),
                                                                  f['title'].encode('UTF-8'),
                                                                  get_type(f['location'].encode('UTF-8')),
                                                                  int(f['audio-bitrate']),
                                                                  int(f['audio-samplerate'])))
    except DBusException:
        weechat.prnt(buffer, "Doesnt look like clementine is running, if it is make sure dbus is running")
    except Exception, err:
        weechat.prnt(buffer, err)
    finally:
        return weechat.WEECHAT_RC_OK

weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "on_shutdown", "")
weechat.hook_command(SCRIPT_COMMAND, SCRIPT_DESC, "", "", "", "np_command", "")
weechat.prnt("", "%s | %s" % (SCRIPT_NAME, SCRIPT_AUTHOR))
