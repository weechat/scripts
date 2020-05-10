"""
Copyright (c) 2014-2018 by Vlad Stoica <stoica.vl@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

History
-------
01-05-2014 - Vlad Stoica
Uses a sqlite3 database to store triggers with the replies, has the
ability to ignore channels.
16-08-2015 - Vlad Stoica
Fixed a bug where replies couldn't have `:' in them.
15-02-2018 - Vlad Stoica
Added regex support in triggers, and edited syntax of adding triggers.
The command is now 'add "trigger" "reply"'. Quote marks can be escaped
in triggers or replies by prefixing them with a backslash ('\'). For
example, 'add "\"picture\"" "say \"cheese\"!"' is a valid command and
will reply with 'say "cheese"!' whenever it finds '"picture"' sent.
29-04-2020 - Fisher
Some new functions:
      - multiple matches ("match1|match2|match3" etc)
      - random selected multiple replites ("reply1|reply2|reply3" etc)
      - can ignore nicks (and ignore itself) for example bots
      - matches now case insensitive
      - utf-8 added
      - cooldown (max. n replies in t time)
      - random delay, so more human-like
      - even more randomness: can specify randomness of the reply/replies group.
05-09-20 - new function - actions

Bugs: not that i'm aware of.
"""

try:
    import weechat
    import sqlite3
    import re
    import random
    import sys
except ImportError:
    raise ImportError("Failed importing weechat, sqlite3, re or random")
import os

SCRIPT_NAME = "triggerreply"
SCRIPT_AUTHOR = "Vlad Stoica <stoica.vl@gmail.com>"
SCRIPT_VERSION = "0.4.2"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Auto replies when someone sends a specified trigger. Now with 100% more regex!"
pcooldown  = 1
""" This is all I need so far :) """
colorcodes = { "^Cb":"\x02","^CR":"\x0F","^Ci":"\x1D" }

def cooldown_timer_cb(data, remaining_calls):
    global pcooldown
    if ( pcooldown > 0 ):
         pcooldown -= 1
    return weechat.WEECHAT_RC_OK


def print_help():
    """ print the help message """
    weechat.prnt("", """
Triggerreply (trigge.rs) plugin. Automatically replies over specified triggers.
------------
Usage: /triggerreply [list | add | remove | ignore | parse] ARGUMENTS

Commands:
    list   - lists the triggers with replies, and ignored channels
    add    - three arguments: "trigger", "reply" and probability
           - adds a trigger with the specified reply and probability
           - probability 1 = 1/1 (100%), 5 = 1/5 (20 %) - optional, default is 1 (100%)
           - negative probability means action, see examples
           - %n in the reply will be replaced by the nick of the matching line
           - %N replaced by "my" nick
           - %m replaced by host and mask *!*@
           - %c replaced by channel name

    remove - one argument: "trigger"
           - remove a trigger
    ignore - one argument: "server.#channel"
           - ignores a particular channel from a server
    parse  - one argument: "server.#channel"
           - removes a channel from ignored list
ignorenick - one argument: "server.#channel.Nick"
           - ignores a particular nick from a server.#channel
watchnick  - one argument: "server.#channel.Nick"
           - removes a nick from ignored list

Examples:
    /triggerreply add "^H(i|ello|ey)[ .!]*" "Hey there!|Hi matey|Aloha!" "1"
    /triggerreply add "lol" "not funny tho" "5"
    /triggerreply remove 2
    /triggerreply ignore rizon.#help
    /triggerreply parse rizon.#help
    /triggerreply ignore rizon.#help.
    /triggerreply ignorenick rizon.#help.Bot
    /triggerreply watchnick rizon.#help.Bot

Auto greetings:
/triggerreply add "(hi|hello|hey|howdy)[,: ]+%N" "Hi, %n.|Hello, %n." "1"
/triggerreply add "%N[,: ]+(hi|hello|hey|howdy)" "Hi, %n.|Helllo, %n." "1"


Kick on adult content. Probability -1 means the strings between | are command executed in order:
/triggerreply add "https?://(www\.)?pornhub\.com|https?://(www\.)?xhamster\.com" "/msg chanserv op %c %N|/kick %n No adult content here, bye|/ban *!*@%m|/msg chanserv deop %c %N" "-1"

""")

def debug(mlevel, message):
    if int(weechat.config_get_plugin('debug')) >= int(mlevel):
       weechat.prnt("", "DEBUG: %s" % message)

def create_db(delete=False):
    debug(3, "Creating basic database.")
    """ create the sqlite database """
    if delete:
        os.remove(db_file)
    temp_con = sqlite3.connect(db_file)
    cur = temp_con.cursor()
    cur.execute("CREATE TABLE triggers(id INTEGER PRIMARY KEY, trig VARCHAR, reply VARCHAR, prob INTEGER);")
    cur.execute("INSERT INTO triggers(trig, reply, prob) VALUES ('trigge.rs', 'Automatic reply', '1');")
    cur.execute("CREATE TABLE banchans(id INTEGER PRIMARY KEY, ignored VARCHAR);")
    cur.execute("INSERT INTO banchans(ignored) VALUES ('rizon.#help');")
    cur.execute("CREATE TABLE ignorenicks(id INTEGER PRIMARY KEY, ignored VARCHAR);")
    cur.execute("INSERT INTO ignorenicks(ignored) VALUES ('dumanet.#DumaNet.Neo');")
    temp_con.commit()
    cur.close()



def check_db():
    temp_con = sqlite3.connect(db_file)
    cur = temp_con.cursor()

    try:
        """ Try to add record enchated with probability """
        cur.execute("INSERT INTO triggers(trig, reply, prob) VALUES (?,?,?)", ('JJORAIGPADMLOLYUGSBZ',"",1))
    except:
        """ If it fails, hope the best and assume it is just an older schema """
        cur.execute("ALTER TABLE triggers ADD COLUMN prob INTEGER")

    """ Clean up the mess """
    cur.execute("DELETE FROM triggers WHERE trig='JJORAIGPADMLOLYUGSBZ'")
    temp_con.commit()
    cur.close()



def search_trig_cb(data, buf, date, tags, displayed, highlight, prefix, message):
    """ function for parsing sent messages """
    global pcooldown

    """ Prevent infinite loop/flood, no more messages than n (approx 3) in 300 secs """
    if ( pcooldown > 300 ): return weechat.WEECHAT_RC_OK

    """ Save some CPU cycles """
    if (prefix == '-->' or prefix == '<--' or prefix == '--' or prefix == ' *' or prefix == ""): return weechat.WEECHAT_RC_OK

    bufname = weechat.buffer_get_string(buf, "name")

    if bufname == 'weechat': return weechat.WEECHAT_RC_OK

    """ Ignore myself """
    mynick =  weechat.buffer_get_string(buf, "localvar_nick")
    if re.search('[@+~]?' + mynick, prefix):
        """ weechat.prnt("", "Ignored myself.") """
        return weechat.WEECHAT_RC_OK


    database = sqlite3.connect(db_file)
    cursor = database.cursor()
    pure = weechat.string_remove_color(message,"")

    debug(1, "Nick in question:'%s" % bufname + '.' + prefix.translate(None,'@+~') + "'")

    for row in cursor.execute("SELECT ignored from ignorenicks;"):
        if re.search(row[0], bufname + '.' + prefix.translate(None,'@+~')):
            """ weechat.prnt("", "Nick ignored: %s" % row[0]) """
            return weechat.WEECHAT_RC_OK

    for row in cursor.execute("SELECT ignored from banchans;"):
        if  bufname == row[0]:
            return weechat.WEECHAT_RC_OK

    for row in cursor.execute("SELECT * FROM triggers"):
        delay = random.randint(4,9)

        pattern = row[1].encode('utf8')
        pattern = pattern.replace("%N", mynick)
        replydata = row[2].encode('utf8')
        prob = int(row[3])

        for ccode, chex in colorcodes.items():
            replydata = replydata.replace(ccode,chex)

        try:
            nick = re.sub('^[+%@]','', prefix)
            debug(2, "prefix: %s, mynick: %s, nick: %s, pattern: %s, prob: %s, pure: %s" % (prefix, mynick, nick, pattern, str(prob), pure))

            r = re.compile(pattern,re.I | re.U)

            if r.search(pure) is not None:
                weechat.prnt("", "Matched")

                """ Meh, not really sure how random it is, but probably good enough """
                if ( prob > 1 and random.randint(1,prob) == 1):
                    debug(1, "Randomly ignored.")
                    return weechat.WEECHAT_RC_OK

                weechat.prnt("", "Match: %s" % r.search(pure).group(0))
                myreply = "n/a"
                if prob < 0:
                    """ -1 means this is action, not saying """
                    delay = 0
                    debug(1,"Command mode triggered.")
                    infolist = weechat.infolist_get("irc_nick", "", bufname.replace(".",","))
                    while weechat.infolist_next(infolist):
                       _nick = weechat.infolist_string(infolist, 'name')
                       if _nick == nick:
                          hostinfo = weechat.infolist_string(infolist,'host')
                          break
                    mask = hostinfo.split('@')[1]
                    weechat.prnt("", "mask: %s" % mask)
                    weechat.infolist_free(infolist)

                    for myreply in replydata.split('|'):
                        myreply = myreply.replace("%n", nick)
                        myreply = myreply.replace("%N", mynick)
                        myreply = myreply.replace("%m", mask)
                        myreply = myreply.replace("%c", bufname.split(".")[1])
                        weechat.prnt("", "Command: %s" % myreply)
                        if delay > 0:
                            weechat.command(buf, "/wait %s %s" % (delay, myreply))
                        else:
                            weechat.command(buf, "%s" % myreply)
                        delay++2

                    return weechat.WEECHAT_RC_OK

                myreply = random.choice(replydata.split('|'))
                myreply = myreply.replace("%n", nick)
                weechat.prnt("", "reply: %s" % myreply)
                weechat.prnt("", "%s triggered." % pattern)
                weechat.command(buf, "/wait %s /say %s" % (delay, myreply))
                pcooldown += 100
        except:
            weechat.prnt("", "NOMatch")
            if pattern == pure:
                weechat.command(buf, "/wait %s /say %s" % (delay, myreply))
                pcooldown += 120

    return weechat.WEECHAT_RC_OK


def command_input_callback(data, buffer, argv):
    """ function called when `/triggerreply args' is run """
    database = sqlite3.connect(db_file)
    cursor = database.cursor()
    command = argv.split()

    if len(command) == 0:
        print_help()
        return weechat.WEECHAT_RC_ERROR

    if command[0] == "list":
        weechat.prnt("", "List of triggers with replies:")
        for row in cursor.execute("SELECT * FROM triggers;"):
            weechat.prnt("", str(row[0]) + ". " + row[1].encode('utf8') + " -> " + row[2].encode('utf8') + "  [Prob: " + str(row[3]) + "]")

        weechat.prnt("", "\nList of ignored channels:")
        for row in cursor.execute("SELECT ignored FROM banchans;"):
            weechat.prnt("", row[0])

        weechat.prnt("", "\nList of ignored nicks:")
        for row in cursor.execute("SELECT ignored FROM ignorenicks;"):
            weechat.prnt("", row[0])

    elif command[0] == "add":
        if len(argv) == len(command[0]):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        if argv.count('"') < 4:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        pos = []
        for k, v in enumerate(argv):
            if v == '"' and argv[k - 1] != '\\':
                pos.append(k)

        if (len(pos) != 6 and len(pos) != 4):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        trigger = argv[pos[0] + 1:pos[1]].replace('\\"', '"')
        reply = argv[pos[2] + 1:pos[3]].replace('\\"', '"')

        prob = 1
        if (len(pos) == 6):
            prob = int(argv[pos[4] + 1:pos[5]])

        try:
            cursor.execute("INSERT INTO triggers(trig, reply, prob) VALUES (?,?,?)", (trigger.decode('utf8'), reply.decode('utf8'), prob))
        except:
            print_help()
            weechat.prnt("", "DB Insert error.")
            return weechat.WEECHAT_RC_ERROR

        database.commit()
        weechat.prnt("", "Trigger added successfully!")
    elif command[0] == "remove":
        if len(argv) == len(command[0]):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        try:
            cursor.execute("DELETE FROM triggers WHERE id = ?", (argv[7:],))
        except:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        database.commit()
        weechat.prnt("", "Trigger successfully removed.")
    elif command[0] == "ignore":
        if len(argv) == len(command[0]):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        try:
            cursor.execute("INSERT INTO banchans(ignored) VALUES (?)", (command[1],))
        except:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        database.commit()
        weechat.prnt("", "Channel successfully added to ignore list!")
    elif command[0] == "parse":
        if len(argv) == len(command[0]):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        try:
            cursor.execute("DELETE FROM banchans WHERE ignored = ?", (command[1],))
        except:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        database.commit()
        weechat.prnt("", "Channnel being watched again.")

    elif command[0] == "ignorenick":
        if len(argv) == len(command[0]):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        try:
            cursor.execute("INSERT INTO ignorenicks(ignored) VALUES (?)", (command[1],))
        except:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        database.commit()
        weechat.prnt("", "Nick successfully added to ignore list!")
    elif command[0] == "watchnick":
        if len(argv) == len(command[0]):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        try:
            cursor.execute("DELETE FROM ignorenicks WHERE ignored = ?", (command[1],))
        except:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        database.commit()
        weechat.prnt("", "Nick successfully removed from ignored.")

    return weechat.WEECHAT_RC_OK


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    db_file = "%s/trigge.rs" % weechat.info_get("weechat_dir", "")
    if weechat.config_get_plugin('debug') == "":
        weechat.config_set_plugin('debug', "0")

    random.seed()

    if not os.path.isfile(db_file):
        create_db()

    check_db()

    weechat.hook_print("", "", "", 1, "search_trig_cb", "")
    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, "See `/triggerreply' for more information.", "", "",
                         "command_input_callback", "")

    """ fire every sec """
    hook = weechat.hook_timer(1000, 0, 0, "cooldown_timer_cb", "")
