"""
    wtwitter.py

    author: Jimmy Zelinskie <jimmyzelinskie@gmail.com>
      desc: Sends your latest tweet to the current buffer
     usage:
       /set plugins.var.python.wtwitter.twitter_handle yourusername
       /wtwitter
   license: GPL3

   history:

       0.2 - rename script to wtwitter.py (twitter is a python module)
       Sebastien Helleu <flashcode@flashtux.org>

       0.1 - initial script
       Jimmy Zelinskie <jimmyzelinskie@gmail.com>

       0.0 - forked from lastfm.py by
       Adam Saponara <saponara TA gmail TOD com>

"""

import weechat
import feedparser

weechat.register("wtwitter", "Jimmy Zelinskie", "0.2", "GPL3", "Sends your latest tweet to the current buffer", "", "")

defaults = {
        "twitter_handle" : "nobody",
        "command" : "/me last tweeted: %s"
}

cmd_hook_process = ""
cmd_buffer       = ""
cmd_stdout       = ""
cmd_stderr       = ""

for k, v in defaults.iteritems():
        if not weechat.config_is_set_plugin(k):
                weechat.config_set_plugin(k, v)

def twitter_cmd(data, buffer, args):
        global cmd_hook_process, cmd_buffer, cmd_stdout, cmd_stderr
        if cmd_hook_process != "":
                weechat.prnt(buffer, "Twitter is already running!")
                return weechat.WEECHAT_RC_OK
        cmd_buffer = buffer
        cmd_stdout = ""
        cmd_stderr = ""
        python2_bin = weechat.info_get("python2_bin", "") or "python"
        cmd_hook_process = weechat.hook_process(
                python2_bin + " -c \"\n"
                "import sys, feedparser\n"
                "feed = None\n"
                "feed = feedparser.parse('http://api.twitter.com/1/statuses/user_timeline.rss?screen_name=%(username)s')\n"
                "if not feed or feed.bozo:\n"
                "	print >>sys.stderr, 'Could not fetch Twitter RSS feed.',\n"
                "elif not 'items' in feed or len(feed['items']) < 1:\n"
                "	print >>sys.stderr, 'No tweets found in Twitter RSS feed.',\n"
                "else:\n"
                "	print '@'+feed['items'][0]['title'].replace(u'\u2013', '-').encode('utf-8', 'replace'),\n"
                "\"" % {"username" : weechat.config_get_plugin('twitter_handle')},
                10000, "twitter_cb", "")
        return weechat.WEECHAT_RC_OK

def twitter_cb(data, command, rc, stdout, stderr):
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
        "wtwitter",
        "Sends your latest tweet to the current buffer. Before using /wtwitter, set your twitter handle like this:\n\n"
        "    /set plugins.var.python.wtwitter.twitter_handle yourhandle\n\n"
        "You can also customize the command that will be sent to the buffer like this:\n\n"
        "    /set plugins.var.python.wtwitter.command I last tweeted %s\n",
        "", "", "", "twitter_cmd", "")
