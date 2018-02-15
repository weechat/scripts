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

Bugs: not that i'm aware of.
"""

try:
    import weechat
    import sqlite3
    import re
except ImportError:
    raise ImportError("Failed importing weechat, sqlite3, re")
import os

SCRIPT_NAME = "triggerreply"
SCRIPT_AUTHOR = "Vlad Stoica <stoica.vl@gmail.com>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Auto replies when someone sends a specified trigger. Now with 100% more regex!"


def print_help():
    """ print the help message """
    weechat.prnt("", """
Triggerreply (trigge.rs) plugin. Automatically replies over specified triggers.
------------
Usage: /triggerreply [list | add | remove | ignore | parse] ARGUMENTS

Commands:
    list   - lists the triggers with replies, and ignored channels
    add    - two arguments: "trigger" and "reply"
           - adds a trigger with the specified reply
           - if '-r' is specified, then the trigger will be parsed as regular expression
    remove - one argument: "trigger"
           - remove a trigger
    ignore - one argument: "server.#channel"
           - ignores a particular channel from a server
    parse  - one argument: "server.#channel"
           - removes a channel from ignored list

Examples:
    /triggerreply add "^[Hh](i|ello|ey)[ .!]*" "Hey there!"
    /triggerreply add "lol" "not funny tho"
    /triggerreply remove lol
    /triggerreply ignore rizon.#help
    /triggerreply parse rizon.#help
""")


def create_db(delete=False):
    """ create the sqlite database """
    if delete:
        os.remove(db_file)
    temp_con = sqlite3.connect(db_file)
    cur = temp_con.cursor()
    cur.execute("CREATE TABLE triggers(id INTEGER PRIMARY KEY, trig VARCHAR, reply VARCHAR);")
    cur.execute("INSERT INTO triggers(trig, reply) VALUES ('trigge.rs', 'Automatic reply');")
    cur.execute("CREATE TABLE banchans(id INTEGER PRIMARY KEY, ignored VARCHAR);")
    cur.execute("INSERT INTO banchans(ignored) VALUES ('rizon.#help');")
    temp_con.commit()
    cur.close()


def search_trig_cb(data, buf, date, tags, displayed, highlight, prefix, message):
    """ function for parsing sent messages """
    if weechat.buffer_get_string(buf, "name") == 'weechat':
        return weechat.WEECHAT_RC_OK

    database = sqlite3.connect(db_file)
    database.text_factory = str
    cursor = database.cursor()

    for row in cursor.execute("SELECT ignored from banchans;"):
        if weechat.buffer_get_string(buf, "name") == row[0]:
            return weechat.WEECHAT_RC_OK

    for row in cursor.execute("SELECT * FROM triggers"):
        try:
            r = re.compile(row[1])
            if r.search(message) is not None:
                weechat.command(buf, "/say %s" % row[2])
        except:
            if row[1] == message:
                weechat.command(buf, "/say %s" % row[2])

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
            weechat.prnt("", str(row[0]) + ". " + row[1] + " -> " + row[2])

        weechat.prnt("", "\nList of ignored channels:")
        for row in cursor.execute("SELECT ignored FROM banchans;"):
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

        if len(pos) != 4:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        trigger = argv[pos[0] + 1:pos[1]].replace('\\"', '"')
        reply = argv[pos[2] + 1:pos[3]].replace('\\"', '"')

        try:
            cursor.execute("INSERT INTO triggers(trig, reply) VALUES (?,?)", (trigger, reply,))
        except:
            print_help()
            return weechat.WEECHAT_RC_ERROR

        database.commit()
        weechat.prnt("", "Trigger added successfully!")
    elif command[0] == "remove":
        if len(argv) == len(command[0]):
            print_help()
            return weechat.WEECHAT_RC_ERROR

        try:
            cursor.execute("DELETE FROM triggers WHERE trig = ?", (argv[7:],))
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
        weechat.prnt("", "Channel successfully removed from ignored.")

    return weechat.WEECHAT_RC_OK


if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    db_file = "%s/trigge.rs" % weechat.info_get("weechat_dir", "")

    if not os.path.isfile(db_file):
        create_db()

    weechat.hook_print("", "", "", 1, "search_trig_cb", "")
    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, "See `/triggerreply' for more information.", "", "",
                         "command_input_callback", "")
