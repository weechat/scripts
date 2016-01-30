# coding: utf-8

"""
    lastfm.py

    author: Adam Saponara <saponara TA gmail TOD com>
      desc: Sends your latest Last.fm track to the current buffer
     usage:
       /set plugins.var.python.lastfm.lastfm_username yourusername
       /lastfm
   license: GPLv3

   history:
       0.7 - 2016-01-29, timss <timsateroy@gmail.com>
             Fix UnicodeEncodeError

       0.6 - 2016-01-14, Lukas Martini <lutoma@ohai.su>
             Use Last.fm API as RSS feeds are broken

       0.5 - 2014-05-07, Kromonos <weechat@kromonos.net>
             fixed some simple bugs

       0.4 - 2011-11-21, Jimmy Zelinskie <jimmyzelinskie@gmail.com>:
             changed default encoding to utf-8

       0.3 - 2011-03-11, Sebastien Helleu <flashcode@flashtux.org>:
             get python 2.x binary for hook_process (fix problem when
             python 3.x is default python version)

       0.2 - using hook_process for last.fm call (prevents hang)
           - using ?limit=1 in last.fm call (faster, more efficient)

       0.1 - initial script

"""

import weechat
import requests

weechat.register("lastfm", "Adam Saponara", "0.7", "GPL3", "Sends your latest Last.fm track to the current buffer", "", "")

defaults = {
        "lastfm_username" : "yourusername",
        "command" : "/me is listening to %s"
}

cmd_hook_process = ""
cmd_buffer       = ""
cmd_stdout       = ""
cmd_stderr       = ""

for k, v in defaults.iteritems():
        if not weechat.config_is_set_plugin(k):
                weechat.config_set_plugin(k, v)

def lastfm_cmd(data, buffer, args):
        global cmd_hook_process, cmd_buffer, cmd_stdout, cmd_stderr
        if cmd_hook_process != "":
                weechat.prnt(buffer, "Lastfm is already running!")
                return weechat.WEECHAT_RC_OK
        cmd_buffer = buffer
        cmd_stdout = ""
        cmd_stderr = ""
        python2_bin = weechat.info_get("python2_bin", "") or "python"
        cmd_hook_process = weechat.hook_process(
                python2_bin + " -c \"\n"
                "import sys, requests\n"
                "r = requests.get('https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%(username)s&api_key=618f9ef38b3d0fed172a88c45ae67f33&format=json&limit=1&extended=0')\n"
                "if not r.status_code == requests.codes.ok:\n"
                "	print >>sys.stderr, 'Could not fetch Last.fm RSS feed.',\n"
                "	exit()\n"
                "json = r.json()['recenttracks']['track'][0]\n"
                "print('{} – {}'.format(json['artist']['#text'].encode('utf-8'), json['name'].encode('utf-8'))),\n"
                "\"" % {"username" : weechat.config_get_plugin('lastfm_username')},
                10000, "lastfm_cb", "")
        return weechat.WEECHAT_RC_OK

def lastfm_cb(data, command, rc, stdout, stderr):
        global cmd_hook_process, cmd_buffer, cmd_stdout, cmd_stderr
        cmd_stdout += stdout
        cmd_stderr += stderr
        if int(rc) >= 0:
                if cmd_stderr != "":
                        weechat.prnt(cmd_buffer, "%s" % cmd_stderr)
                if cmd_stdout != "":
                        weechat.command(cmd_buffer, weechat.config_get_plugin("command") % cmd_stdout.replace('\n',''))
                cmd_hook_process = ""
        return weechat.WEECHAT_RC_OK

hook = weechat.hook_command(
        "lastfm",
        "Sends your latest Last.fm track to the current buffer. Before using /lastfm, set your Last.fm username like this:\n\n"
        "    /set plugins.var.python.lastfm.lastfm_username yourusername\n\n"
        "You can also customize the command that will be sent to the buffer like this:\n\n"
        "    /set plugins.var.python.lastfm.command Right now I'm listening to %s\n",
        "", "", "", "lastfm_cmd", "")
