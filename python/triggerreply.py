# Copyright (c) 2014 by Vlad Stoica <stoica.vl@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# History
# 01-05-2014 - Vlad Stoica
# Uses a sqlite3 database to store triggers with the replies, has the
# ability to ignore channels.
#
# Bugs : not that i'm aware of.

try:
    import weechat
    import sqlite3
    import_error = 0
except ImportError:
    import_error = 1
import os

SCRIPT_NAME = "triggerreply"
SCRIPT_AUTHOR = "Vlad Stoica <stoica.vl@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Auto replies when someone sends a specified trigger."

def phelp():
    weechat.prnt("", "Triggerreply (trigge.rs) plugin. Automatically replies over specified triggers")
    weechat.prnt("", "------------")
    weechat.prnt("", "Usage: /triggerreply [list | add trigger:reply | remove trigger | ignore server.#channel | parse server.#channel]")

def create_db():
    tmpcon = sqlite3.connect(dbfile)
    cur = tmpcon.cursor()
    cur.execute("CREATE TABLE triggers(id INTEGER PRIMARY KEY, trig VARCHAR, reply VARCHAR);")
    cur.execute("INSERT INTO triggers(trig, reply) VALUES ('trigge.rs', 'Automatic reply');")
    cur.execute("CREATE TABLE banchans(id INTEGER PRIMARY KEY, ignored VARCHAR);")
    cur.execute("INSERT INTO banchans(ignored) VALUES ('rizon.#help');")
    tmpcon.commit()
    cur.close()

def search_trig_cb(data, buffer, date, tags, displayed, highlight, prefix, message):
    """
    Function for parsing sent messages.
    """
    database = sqlite3.connect(dbfile)
    database.text_factory = str
    cursor = database.cursor()
    ignored_chan = False
    for row in cursor.execute("SELECT ignored from banchans;"):
        if weechat.buffer_get_string(buffer, "name") == row[0]:
            ignored_chan = True
    if not ignored_chan:
        for row in cursor.execute("SELECT reply FROM triggers WHERE trig = ?", (str(message),)):
            weechat.command(buffer, "/say %s" % row)
    return weechat.WEECHAT_RC_OK

def command_input_callback(data, buffer, argv):
    """
    Function called when `/triggerreply args' is run
    """
    database = sqlite3.connect(dbfile)
    cursor = database.cursor()
    command = argv.split()
    if len(command) == 0:
        phelp()
    elif command[0] == "list":
        weechat.prnt("", "List of triggers with replies:")
        for row in cursor.execute("SELECT * FROM triggers;"):
            weechat.prnt("", str(row[0]) + ". " + row[1] + " -> " + row[2])
        weechat.prnt("", "\nList of ignored channels:")
        for row in cursor.execute("SELECT ignored FROM banchans;"):
            weechat.prnt("", row[0])
    elif command[0] == "add":
        try:
            trigger = argv[4:].split(":")[0]
            reply = argv[4:].split(":")[1]
            cursor.execute("INSERT INTO triggers(trig, reply) VALUES (?,?)", (trigger, reply,))
        except:
            weechat.prnt("", "Could not add trigger.\n")
            weechat.prnt("", "Usage:   /triggerreply add trigger:reply")
            weechat.prnt("", "Example: /triggerreply add lol:hue hue")
        else:
            database.commit()
            weechat.prnt("", "Trigger added successfully!")
    elif command[0] == "remove":
        try:
            cursor.execute("DELETE FROM triggers WHERE trig = ?", (argv[7:],))
        except:
            weechat.prnt("", "Could not remove trigger.")
            weechat.prnt("", "Usage:   /triggerreply remove trigger")
            weechat.prnt("", "Example: /triggerreply remove hue")
        else:
            database.commit()
            weechat.prnt("", "Trigger successfully removed.")
    elif command[0] == "ignore":
        try:
            cursor.execute("INSERT INTO banchans(ignored) VALUES (?)", (command[1],))
        except:
            weechat.prnt("", "Could not add channel to ignored list.")
            weechat.prnt("", "Usage:   /triggerreply ignore server.#channel")
            weechat.prnt("", "Example: /triggerreply ignore freenode.#mychan")
        else:
            database.commit()
            weechat.prnt("", "Channel successfully added to ignore list!")
    elif command[0] == "parse":
        try:
            cursor.execute("DELETE FROM banchans WHERE ignored = ?", (command[1],))
        except:
            weechat.prnt("", "Could not remove channel from ignored.")
            weechat.prnt("", "Usage:   /triggerreply parse server.#channel")
            weechat.prnt("", "Example: /triggerreply parse freenode.#mychan")
        else:
            database.commit()
            weechat.prnt("", "Channel successfully removed from ignored.")
    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    if import_error:
        weechat.prnt("", "You need sqlite3 to run this plugin.")
    dbfile = "%s/trigge.rs" % weechat.info_get("weechat_dir", "")
    if not os.path.isfile(dbfile):
        create_db()


    weechat.hook_print("", "", "", 1, "search_trig_cb", "")
    weechat.hook_command(SCRIPT_NAME, SCRIPT_DESC, "See `/triggerreply' for more information.", "", "", "command_input_callback", "")
