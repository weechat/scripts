# This script sends "uname -a" output to current channel.
# 	Just type /uname while chatting on some channel ;)
#
# 		by Stalwart <stlwrt doggy gmail.com>
#
# port to WeeChat 0.3.0 by Benjamin Neff (SuperTux88) <info@benjaminneff.ch>
#
# Released under GPL licence.


SCRIPT_NAME    = "uname"
SCRIPT_AUTHOR  = "Stalwart <stlwrt doggy gmail.com>"
SCRIPT_VERSION = "1.1"
SCRIPT_LICENSE = "GPL2"
SCRIPT_DESC    = "Sends \"uname -a\" output to current channel"

import_ok = True

try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

try:
    from os import popen
except ImportError, message:
    print "Missing package(s) for %s: %s" % (SCRIPT_NAME, message)
    import_ok = False

def senduname(data, buffer, args):
	unameout = popen ('uname -a')
	uname = unameout.readline()
	weechat.command(buffer, "uname -a: " + uname[:-1])
	return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
	if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
		weechat.hook_command (SCRIPT_NAME, SCRIPT_DESC, '','Just type /uname while chatting on some channel ;)','', 'senduname', '')
