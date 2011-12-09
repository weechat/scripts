"""
    lastfm.py

    author: Adam Saponara <saponara TA gmail TOD com>
      desc: Sends your latest Last.fm track to the current buffer
     usage:
       /set plugins.var.python.lastfm.lastfm_username yourusername
       /lastfm
   license: GPLv3

   history:

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
import feedparser

weechat.register("lastfm", "Adam Saponara", "0.4", "GPL3", "Sends your latest Last.fm track to the current buffer", "", "")

defaults = {
        "lastfm_username" : "nobody",
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
                "import sys, feedparser\n"
                "feed = None\n"
                "feed = feedparser.parse('http://ws.audioscrobbler.com/1.0/user/%(username)s/recenttracks.rss?limit=1')\n"
                "if not feed or feed.bozo:\n"
                "	print >>sys.stderr, 'Could not fetch Last.fm RSS feed.',\n"
                "elif not 'items' in feed or len(feed['items']) < 1:\n"
                "	print >>sys.stderr, 'No tracks found in Last.fm RSS feed.',\n"
                "else:\n" 
                "	print feed['items'][0]['title'].replace(u'\u2013', '-').encode('utf-8', 'replace'),\n"
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
                        weechat.command(cmd_buffer, weechat.config_get_plugin("command") % cmd_stdout)
                cmd_hook_process = ""
        return weechat.WEECHAT_RC_OK

hook = weechat.hook_command(
        "lastfm",
        "Sends your latest Last.fm track to the current buffer. Before using /lastfm, set your Last.fm username like this:\n\n"
        "    /set plugins.var.python.lastfm.lastfm_username yourusername\n\n"
        "You can also customize the command that will be sent to the buffer like this:\n\n"
        "    /set plugins.var.python.lastfm.command Right now I'm listening to %s\n",
        "", "", "", "lastfm_cmd", "")
