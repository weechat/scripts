# gribble - automatically authenticate to gribble for bitcoin otc exchange
# by Alex Fluter <afluter@gmail.com>
# irc nick @fluter
#
# before load this script, set your gpg passphrase by
#     /secure set gpg_passphrase xxxxxx

import re
import subprocess
import urllib2
import weechat

NAME = "gribble"
AUTHOR = "fluter <afluter@gmail.com>"
VERSION = "0.1"
LICENSE = "Apache"
DESCRIPTION = "Script to talk to gribble"

gribble_channel = "#bitcoin-fr"
gribble_nick = "gribble"
ident_nick = "fluter"
options = {
        # the channel name to watch to trigger this script
        "channel": "#bitcoin-otc",
        # the key of the secure data storing gpg passphrase
        "pass_key": "gpg_passphrase"
}
gribble_buffer = None


hook_msg = None

def init():
    global gribble_buffer
    gribble_buffer = weechat.buffer_new(NAME, "", "", "", "")
    weechat.prnt(gribble_buffer, "Options:")
    for opt, val in options.iteritems():
        if not weechat.config_is_set_plugin(opt):
            weechat.config_set_plugin(opt, val)
        else:
            options[opt] = weechat.config_get_plugin(opt)
        weechat.prnt(gribble_buffer, "    %s: %s" % (opt, options[opt]))

def privmsg(server, to, msg):
    buffer = weechat.info_get("irc_buffer", server)
    weechat.command(buffer, "/msg %s %s" % (to, msg))

def join_cb(data, signal, signal_data):
    dict_in = {"message": signal_data}
    dict_out = weechat.info_get_hashtable("irc_message_parse", dict_in)
    channel = dict_out["channel"]
    if channel != options["channel"]:
        return weechat.WEECHAT_RC_OK

    server = signal.split(",")[0]
    nick = dict_out["nick"]
    me = weechat.info_get("irc_nick", server)
    if nick != me:
        return weechat.WEECHAT_RC_OK

    weechat.prnt(gribble_buffer, "Channel %s joined" % channel)
    hook_msg = weechat.hook_signal("*,irc_in2_PRIVMSG", "privmsg_cb", "")
    weechat.prnt(gribble_buffer, "Sent eauth to %s" % gribble_nick)
    privmsg(server, gribble_nick, "eauth %s" % ident_nick)

    return weechat.WEECHAT_RC_OK

def privmsg_cb(data, signal, signal_data):
    dict_in = {"message": signal_data}
    dict_out = weechat.info_get_hashtable("irc_message_parse", dict_in)
    if not weechat.info_get("irc_is_nick", dict_out["channel"]):
        return weechat.WEECHAT_RC_OK

    server = signal.split(",")[0]
    nick = dict_out["channel"]
    me = weechat.info_get("irc_nick", server)
    if nick != me:
        return weechat.WEECHAT_RC_OK

    if dict_out["nick"] != gribble_nick:
        return weechat.WEECHAT_RC_OK

    msg = dict_out["text"]
    m = re.match("^.*Get your encrypted OTP from (.*)$", msg)
    if m is None:
        return weechat.WEECHAT_RC_OK
    weechat.prnt(gribble_buffer, "Got OTP")
    otp_url = m.group(1)
    otp = urllib2.urlopen(otp_url).read()
    # the passphrase is stored encrypted in secure data
    expr = "${sec.data.%s}" % options["pass_key"]
    gpg_pass = weechat.string_eval_expression(expr, "", "", "")
    if gpg_pass == "":
        weechat.prnt(gribble_buffer, "no gpg pass found in secure data")
        return weechat.WEECHAT_RC_OK

    p = subprocess.Popen(["gpg", "--batch", "--decrypt", "--passphrase", gpg_pass],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
    out, err = p.communicate(otp)
    if err != "":
        weechat.prnt(gribble_buffer, "gpg output: " + err)
    if out != "":
        privmsg(server, gribble_nick, "everify %s" % out)

    return weechat.WEECHAT_RC_OK

def main():
    init()
    hook_join = weechat.hook_signal("*,irc_in2_JOIN", "join_cb", "foo")

weechat.register(NAME, AUTHOR, VERSION, LICENSE, DESCRIPTION, "", "")
weechat.prnt("", "%s %s loaded" % (NAME, VERSION))
main()
