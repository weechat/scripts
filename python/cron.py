# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2012 Sebastien Helleu <flashcode@flashtux.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Time-based scheduler, like cron and at.
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.4: make script compatible with Python 3.x
# 2011-02-13, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.3: use new help format for command arguments
# 2010-07-31, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.2: add keyword "commands" to run many commands
# 2010-07-26, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release
# 2010-07-20, Sebastien Helleu <flashcode@flashtux.org>:
#     script creation
#

SCRIPT_NAME    = "cron"
SCRIPT_AUTHOR  = "Sebastien Helleu <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.4"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Time-based scheduler, like cron and at"

import_ok = True

try:
    import weechat
except:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False

try:
    import os, stat, time
    from datetime import datetime, timedelta
except ImportError as message:
    print("Missing package(s) for %s: %s" % (SCRIPT_NAME, message))
    import_ok = False

# script options
cron_settings = {
    "auto_reload" : "on",          # auto reload cron file each minute if file has changed
                                   # if set to off, then command "/cron reload" must be executed manually
    "auto_save"   : "on",          # auto save jobs to file (when adding/removing job, and when unloading script)
    "filename"    : "%h/cron.txt", # cron filename
    "quiet_load"  : "off",         # silently load crontab file (no message displayed, except errors)
    "quiet_save"  : "on" ,         # silently save crontab file (no message displayed, except errors)
    "quiet_exec"  : "off",         # silently exec commands (no error displayed)
}

crontab = []
cron_last_read_time = 0
cron_commands = {
    "print"     : "print a message on buffer",
    "print_hl"  : "print a message on buffer with \"highlight\" notify on line",
    "print_msg" : "print a message on buffer with \"message\" notify on line",
    "command"   : "execute a command (starting with \"/\") or send text to buffer (like input)",
    "commands"  : "execute many commands separated by \";\"",
    "python"    : "evaluate python code",
}

# ================================[ cron jobs ]===============================

class AlwaysMatch(set):
    def __contains__(self, item):
        return True
    def __str__(self):
        return "*"

alwaysMatch = AlwaysMatch()

def cron_str2int(str):
    """ Convert day name to digit. """
    days = [ "sun", "mon", "tue", "wed", "thu", "fri", "sat" ]
    try:
        pos = days.index(str)
        if pos != ValueError:
            return pos
    except:
        try:
            value = int(str)
            return value
        except:
            return 0

def cron_str2set(str, min_value, max_value):
    """ Convert string with range to a set. """
    if str == "*":
        return alwaysMatch
    ret = set([])
    try:
        items = str.split(",")
        for item in items:
            values = item
            skip = 1
            pos = values.find("/")
            if pos > 0:
                try:
                    skip = int(values[pos+1:])
                except:
                    skip = 1
                values = values[0:pos]
            pos = values.find("-")
            if pos > 0:
                value1 = cron_str2int(values[0:pos])
                value2 = cron_str2int(values[pos+1:])
            else:
                if values == "*":
                    value1 = min_value
                    value2 = max_value
                else:
                    value1 = cron_str2int(values)
                    value2 = cron_str2int(values)
            ret = set.union(ret, set(range(value1, value2 + 1, skip)))
    except:
        weechat.prnt("", "%scron: error with time string \"%s\""
                     % (weechat.prefix("error"), str))
        return alwaysMatch
    return ret

def cron_set2str(obj):
    """ Convert a set to a string, for display (sort set). """
    if isinstance(obj, AlwaysMatch):
        return "*"
    l = list(obj)
    l.sort()
    return "%s" % l

class CronJob(object):
    """ Class for a job in crontab. """
    def __init__(self, minute=alwaysMatch, hour=alwaysMatch,
                 monthday=alwaysMatch, month=alwaysMatch, weekday=alwaysMatch,
                 repeat="*", buffer="core.weechat", command=""):
        self.minute = minute
        self.minutes = cron_str2set(minute, 0, 59)
        self.hour = hour
        self.hours = cron_str2set(hour, 0, 23)
        self.monthday = monthday
        self.monthdays = cron_str2set(monthday, 1, 31)
        self.month = month
        self.months = cron_str2set(month, 1, 12)
        self.weekday = weekday
        self.weekdays = cron_str2set(weekday, 0, 6)
        if repeat == "*":
            self.repeat = -1
        else:
            try:
                self.repeat = int(repeat)
                if self.repeat < 1:
                    self.repeat = 1
            except:
                self.remaining_exec = 1
        self.buffer = buffer
        self.command = command

    def str_repeat(self):
        if self.repeat < 0:
            return "*"
        return "%d" % self.repeat

    def __str__(self):
        """ Job to string. """
        return "%s %s %s %s %s %s %s %s" % (self.minute, self.hour, self.monthday,
                                            self.month, self.weekday,
                                            self.str_repeat(), self.buffer, self.command)

    def str_debug(self):
        """ Job to string with detail (to view sets). """
        return "%s %s %s %s %s %d %s %s" % (cron_set2str(self.minutes),
                                            cron_set2str(self.hours),
                                            cron_set2str(self.monthdays),
                                            cron_set2str(self.months),
                                            cron_set2str(self.weekdays),
                                            self.repeat, self.buffer, self.command)

    def matchtime(self, t):
        """ Check if this job matches given time (ie command must be executed). """
        return ((t.minute in self.minutes) and
                (t.hour in self.hours) and
                (t.day in self.monthdays) and
                (t.month in self.months) and
                ((t.isoweekday() % 7) in self.weekdays))

    def exec_command(self, userExec=False):
        """ Execute job command. """
        global cron_commands
        display_error = weechat.config_get_plugin("quiet_exec") == "off"
        buf = ""
        if self.buffer == "current":
            buf = weechat.current_buffer()
        else:
            items = self.buffer.split(".", 1)
            if len(items) >= 2:
                buf = weechat.buffer_search(items[0], items[1])
        if buf:
            argv = self.command.split(None, 1)
            if len(argv) > 0 and argv[0] in cron_commands:
                if argv[0] == "print":
                    weechat.prnt(buf, "%s" % argv[1])
                elif argv[0] == "print_hl":
                    weechat.prnt_date_tags(buf, 0, "notify_highlight", "%s" % argv[1])
                elif argv[0] == "print_msg":
                    weechat.prnt_date_tags(buf, 0, "notify_message", "%s" % argv[1])
                elif argv[0] == "command":
                    weechat.command(buf, "%s" % argv[1])
                elif argv[0] == "commands":
                    cmds = argv[1].split(";")
                    for cmd in cmds:
                        weechat.command(buf, "%s" % cmd)
                elif argv[0] == "python":
                    eval(argv[1])
            elif display_error:
                weechat.prnt("", "%scron: unknown command (\"%s\")"
                             % (weechat.prefix("error"), self.command))
        else:
            if display_error:
                weechat.prnt("", "%scron: buffer \"%s\" not found"
                             % (weechat.prefix("error"), self.buffer))
        if not userExec and self.repeat > 0:
            self.repeat -= 1

# ============================[ load/save crontab ]===========================

def cron_filename():
    """ Get crontab filename. """
    return weechat.config_get_plugin("filename").replace("%h", weechat.info_get("weechat_dir", ""))

def cron_str_job_count(number):
    """ Get string with "%d jobs". """
    if number <= 1:
        return "%d job" % number
    return "%d jobs" % number

def cron_load(force_message=False):
    """ Load crontab from file. """
    global crontab, cron_last_read_time
    display_message = weechat.config_get_plugin("quiet_load") == "off" or force_message
    crontab = []
    filename = cron_filename()
    if os.path.isfile(filename):
        f = open(filename)
        for line in f:
            line = line.lstrip().rstrip("\r\n")
            if not line.startswith("#"):
                argv = line.split(None, 7)
                if len(argv) >= 8:
                    crontab.append(CronJob(argv[0], argv[1], argv[2], argv[3],
                                           argv[4], argv[5], argv[6], argv[7]))
        f.close()
        cron_last_read_time = time.time()
        if display_message:
            weechat.prnt("", "cron: %s loaded from \"%s\""
                         % (cron_str_job_count(len(crontab)), filename))
    else:
        if cron_last_read_time != 0:
            cron_last_read_time = 0
            if display_message:
                weechat.prnt("", "cron: reset (file not found: \"%s\")" % filename)
        elif display_message:
            weechat.prnt("", "cron: file not found: \"%s\"" % filename)

def cron_save(force_message=False):
    """ Save crontab in file. """
    global crontab, cron_last_read_time
    display_message = weechat.config_get_plugin("quiet_save") == "off" or force_message
    filename = cron_filename()
    f = open(filename, "w")
    f.write("#\n")
    f.write("# WeeChat crontab for script cron.py\n")
    f.write("# format: min hour monthday month weekday repeat buffer command args\n")
    f.write("#\n")
    for job in crontab:
        f.write("%s\n" % job)
    f.close()
    cron_last_read_time = time.time()
    if display_message:
        weechat.prnt("", "cron: %s saved to \"%s\""
                     % (cron_str_job_count(len(crontab)), filename))

def cron_reload_needed():
    """ Return True if crontab must be reloaded, False if it is not needed. """
    global cron_last_read_time
    filename = cron_filename()
    if os.path.isfile(filename):
        return cron_last_read_time == 0 or os.stat(filename)[stat.ST_MTIME] > cron_last_read_time
    else:
        return cron_last_read_time != 0

# ============================[ crontab functions ]===========================

def cron_list(debug=False):
    """ Display list of jobs in crontab. """
    global crontab
    if len(crontab) == 0:
        weechat.prnt("", "cron: empty crontab")
    else:
        weechat.prnt("", "crontab:")
        for i, job in enumerate(crontab):
            if debug:
                str_job = "%s" % job.str_debug()
            else:
                str_job = "%s" % job
            weechat.prnt("", "  %s[%s%03d%s]%s %s"
                         % (weechat.color("chat_delimiters"), weechat.color("chat"),
                            i + 1,
                            weechat.color("chat_delimiters"), weechat.color("chat"),
                            str_job))

def cron_add(minute, hour, monthday, month, weekday, repeat, buffer, command):
    """ Add a job to crontab. """
    global crontab
    job = CronJob(minute, hour, monthday, month, weekday, repeat, buffer, command)
    crontab.append(job)
    weechat.prnt("", "cron: job added:  %s" % job)
    if weechat.config_get_plugin("auto_save") == "on":
        cron_save()

def cron_current_time():
    """ Get current time. """
    return datetime(*datetime.now().timetuple()[:5])

# ==============================[ at functions ]==============================

def cron_at_time(strtime):
    reftime = datetime.now()
    if strtime.startswith("+"):
        try:
            strtime = strtime[1:]
            delta = timedelta(minutes=1)
            unit = strtime[-1]
            if unit in ["m", "h", "d"]:
                value = int(strtime[:-1])
            else:
                value = int(strtime)
                unit = "m"
            if unit == "m":
                delta = timedelta(minutes=value)
            elif unit == "h":
                delta = timedelta(hours=value)
            elif unit == "d":
                delta = timedelta(days=value)
            reftime += delta
        except:
            return None
        return [reftime.hour, reftime.minute]
    else:
        items = strtime.split(":", 1)
        if len(items) >= 2:
            try:
                hour = int(items[0])
                minute = int(items[1])
            except:
                return None
            return [hour, minute]

# ================================[ commands ]================================

def cron_completion_time_cb(data, completion_item, buffer, completion):
    """ Complete with time, for command '/cron'. """
    weechat.hook_completion_list_add(completion, "*",
                                     0, weechat.WEECHAT_LIST_POS_BEGINNING)
    return weechat.WEECHAT_RC_OK

def cron_completion_repeat_cb(data, completion_item, buffer, completion):
    """ Complete with repeat, for command '/cron'. """
    weechat.hook_completion_list_add(completion, "*",
                                     0, weechat.WEECHAT_LIST_POS_BEGINNING)
    return weechat.WEECHAT_RC_OK

def cron_completion_buffer_cb(data, completion_item, buffer, completion):
    """ Complete with buffer, for command '/cron'. """
    infolist = weechat.infolist_get("buffer", "", "")
    while weechat.infolist_next(infolist):
        plugin_name = weechat.infolist_string(infolist, "plugin_name")
        name = weechat.infolist_string(infolist, "name")
        weechat.hook_completion_list_add(completion,
                                         "%s.%s" % (plugin_name, name),
                                         0, weechat.WEECHAT_LIST_POS_SORT)
    weechat.infolist_free(infolist)
    weechat.hook_completion_list_add(completion, "current",
                                     0, weechat.WEECHAT_LIST_POS_BEGINNING)
    weechat.hook_completion_list_add(completion, "core.weechat",
                                     0, weechat.WEECHAT_LIST_POS_BEGINNING)
    return weechat.WEECHAT_RC_OK

def cron_completion_keyword_cb(data, completion_item, buffer, completion):
    """ Complete with cron keyword, for command '/cron'. """
    global cron_commands
    for command in sorted(cron_commands.keys()):
        weechat.hook_completion_list_add(completion, command,
                                         0, weechat.WEECHAT_LIST_POS_END)
    return weechat.WEECHAT_RC_OK

def cron_completion_commands_cb(data, completion_item, buffer, completion):
    """ Complete with commands, for command '/cron'. """
    infolist = weechat.infolist_get("hook", "command", "")
    while weechat.infolist_next(infolist):
        command = weechat.infolist_string(infolist, "command")
        if command.startswith("/"):
            command = command[1:]
        if command:
            weechat.hook_completion_list_add(completion, "/%s" % command,
                                             0, weechat.WEECHAT_LIST_POS_SORT)
    weechat.infolist_free(infolist)
    return weechat.WEECHAT_RC_OK

def cron_completion_number_cb(data, completion_item, buffer, completion):
    """ Complete with jobs numbers, for command '/cron'. """
    global crontab
    if len(crontab) > 0:
        for i in reversed(range(0, len(crontab))):
            weechat.hook_completion_list_add(completion, "%d" % (i + 1),
                                             0, weechat.WEECHAT_LIST_POS_BEGINNING)
    return weechat.WEECHAT_RC_OK

def cron_completion_at_time_cb(data, completion_item, buffer, completion):
    """ Complete with time, for command '/at'. """
    weechat.hook_completion_list_add(completion, "+5m",
                                     0, weechat.WEECHAT_LIST_POS_END)
    weechat.hook_completion_list_add(completion, "20:00",
                                     0, weechat.WEECHAT_LIST_POS_END)
    return weechat.WEECHAT_RC_OK

def cron_cmd_cb(data, buffer, args):
    """ Command /cron. """
    global crontab, cron_commands
    if args in ["", "list"]:
        cron_list()
        return weechat.WEECHAT_RC_OK
    if args == "debug":
        cron_list(debug=True)
        return weechat.WEECHAT_RC_OK
    argv = args.split(None, 9)
    if len(argv) > 0:
        if argv[0] == "add":
            if len(argv) >= 10:
                if argv[8] not in cron_commands:
                    weechat.prnt("", "%scron: unknown keyword \"%s\""
                                 % (weechat.prefix("error"), argv[8]))
                    return weechat.WEECHAT_RC_ERROR
                cron_add(argv[1], argv[2], argv[3], argv[4], argv[5],
                         argv[6], argv[7], argv[8] + " " + argv[9])
                return weechat.WEECHAT_RC_OK
        elif argv[0] in ["del", "exec"]:
            if argv[0] == "del" and argv[1] == "-all":
                crontab = []
                weechat.prnt("", "cron: all jobs deleted")
                if weechat.config_get_plugin("auto_save") == "on":
                    cron_save()
                return weechat.WEECHAT_RC_OK
            try:
                number = int(argv[1])
                if number < 1 or number > len(crontab):
                    weechat.prnt("", "%scron: job number not found" % weechat.prefix("error"))
                    return weechat.WEECHAT_RC_OK
                if argv[0] == "del":
                    job = crontab.pop(number - 1)
                    weechat.prnt("", "cron: job #%d deleted (%s)" % (number, job))
                    if weechat.config_get_plugin("auto_save") == "on":
                        cron_save()
                elif argv[0] == "exec":
                    job = crontab[number - 1]
                    job.exec_command(userExec=True)
            except:
                weechat.prnt("", "%scron: job number not found" % weechat.prefix("error"))
            return weechat.WEECHAT_RC_OK
        elif argv[0] == "reload":
            cron_load(force_message=True)
            return weechat.WEECHAT_RC_OK
        elif argv[0] == "save":
            cron_save(force_message=True)
            return weechat.WEECHAT_RC_OK
    weechat.prnt("", "%scron: invalid arguments" % weechat.prefix("error"))
    return weechat.WEECHAT_RC_OK

def cron_at_cmd_cb(data, buffer, args):
    """ Command /at. """
    global crontab, cron_commands
    if args in ["", "list"]:
        cron_list()
        return weechat.WEECHAT_RC_OK
    if args == "debug":
        cron_list(debug=True)
        return weechat.WEECHAT_RC_OK
    argv = args.split(None, 3)
    if len(argv) >= 4:
        if argv[2] not in cron_commands:
            weechat.prnt("", "%scron: unknown keyword \"%s\""
                         % (weechat.prefix("error"), argv[2]))
            return weechat.WEECHAT_RC_ERROR
        hour_min = cron_at_time(argv[0])
        if hour_min == None:
            weechat.prnt("", "%scron: invalid time \"%s\""
                         % (weechat.prefix("error"), argv[0]))
            return weechat.WEECHAT_RC_OK
        cron_add(str(hour_min[1]), str(hour_min[0]), "*", "*", "*",
                 "1", argv[1], argv[2] + " " + argv[3])
        return weechat.WEECHAT_RC_OK
    weechat.prnt("", "%scron: invalid arguments" % weechat.prefix("error"))
    return weechat.WEECHAT_RC_OK

# ==================================[ timer ]=================================

def cron_timer_cb(data, remaining_calls):
    """ Timer called each minute. """
    global crontab
    t1 = cron_current_time()
    if weechat.config_get_plugin("auto_reload") == "on":
        if cron_reload_needed():
            cron_load()
    crontab2 = []
    for job in crontab:
        if job.matchtime(t1):
            job.exec_command()
        if job.repeat != 0:
            crontab2.append(job)
    crontab = crontab2
    return weechat.WEECHAT_RC_OK

# ==================================[ main ]==================================

def cron_unload():
    """ Called when script is unloaded. """
    if weechat.config_get_plugin("auto_save") == "on":
        cron_save()
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "cron_unload", ""):
        # set default settings
        for option, default_value in cron_settings.items():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        # completions for commands
        weechat.hook_completion("cron_time", "cron time", "cron_completion_time_cb", "")
        weechat.hook_completion("cron_repeat", "cron repeat", "cron_completion_repeat_cb", "")
        weechat.hook_completion("cron_buffer", "cron buffer", "cron_completion_buffer_cb", "")
        weechat.hook_completion("cron_keyword", "cron keyword", "cron_completion_keyword_cb", "")
        weechat.hook_completion("cron_commands", "cron commands", "cron_completion_commands_cb", "")
        weechat.hook_completion("cron_number", "cron number", "cron_completion_number_cb", "")
        weechat.hook_completion("at_time", "at time", "cron_completion_at_time_cb", "")
        # commands /cron and /at
        str_buffer = "  buffer: buffer where command is executed\n" \
            "          (\"current\" for current buffer, \"core.weechat\" for WeeChat core buffer)\n"
        str_commands = " command: a keyword, followed by arguments:\n"
        for cmd in sorted(cron_commands.keys()):
            str_commands += "          - " + cmd + ": " + cron_commands[cmd] + "\n";
        weechat.hook_command("cron",
                             "Manage jobs in crontab",
                             "list || add <minute> <hour> <monthday> <month> <weekday> <repeat> <buffer> <command> || "
                             "del <number>|-all || exec <number> || reload|save",
                             "    list: display jobs in crontab\n"
                             "     add: add a job in crontab\n"
                             "  minute: minute (0-59)\n"
                             "    hour: hour (0-23)\n"
                             "monthday: day of month (1-31)\n"
                             "   month: month (1-12)\n"
                             " weekday: day of week (0-6, or name: "
                             "sun (0), mon (1), tue (2), wed (3), thu (4), fri (5), sat (6))\n"
                             "  repeat: number of times job will be executed, must be >= 1 or special value * (repeat forever)\n"
                             + str_buffer + str_commands +
                             "     del: remove job(s) from crontab\n"
                             "  number: job number\n"
                             "    -all: remove all jobs\n"
                             "    exec: execute a command for a job (useful for testing command)\n"
                             "  reload: reload crontab file (automatic by default)\n"
                             "    save: save current crontab to file (automatic by default)\n\n"
                             "Format for time and date is similar to crontab, see man 5 crontab.\n\n"
                             "Examples:\n"
                             "  Display \"short drink!\" at 12:00 each day:\n"
                             "    /cron add 0 12 * * * * core.weechat print short drink!\n"
                             "  Same example with python code:\n"
                             "    /cron add 0 12 * * * * core.weechat python weechat.prnt(\"\", \"short drink!\")\n"
                             "  Set away status on all servers at 23:30:\n"
                             "    /cron add 30 23 * * * * core.weechat command /away -all I am sleeping\n"
                             "  Remove away status on all servers at 07:00:\n"
                             "    /cron add 0 7 * * * * core.weechat command /away -all I am sleeping\n"
                             "  Set away status on all servers at 10:00 every sunday:\n"
                             "    /cron add 0 10 * * sun * core.weechat command /away -all I am playing tennis\n"
                             "  Say \"hello\" on IRC channel #private at 08:00 from monday to friday:\n"
                             "    /cron add 0 8 * * mon-fri * irc.freenode.#private command hello\n"
                             "  Display \"wake up!\" at 06:00 next monday, only one time, with highlight:\n"
                             "    /cron add 0 6 * * mon 1 core.weechat print_hl wake up!\n"
                             "  Delete first entry in crontab:\n"
                             "    /cron del 1",
                             "list"
                             " || add %(cron_time) %(cron_time) %(cron_time) "
                             "%(cron_time) %(cron_time) %(cron_repeat) %(cron_buffer) "
                             "%(cron_keyword) %(cron_commands)"
                             " || del %(cron_number)|-all"
                             " || exec %(cron_number)"
                             " || reload"
                             " || save",
                             "cron_cmd_cb", "")
        weechat.hook_command("at",
                             "Queue job for later execution",
                             "list || <time> <buffer> <command>",
                             "    list: display jobs in crontab\n"
                             "    time: time for job, can be absolute (HH:MM) or relative "
                             "with \"+\" followed by value and optional unit\n"
                             "          (units: m=minutes (default), h=hours, d=days)\n"
                             + str_buffer + str_commands + "\n"
                             "To manage scheduled jobs, or use date and time to schedule a job, "
                             "use /cron command.\n\n"
                             "Examples:\n"
                             "  Display \"water the garden\" at 20:00:\n"
                             "    /at 20:00 core.weechat print water the garden\n"
                             "  Display \"phone to mom\" in 15 minutes:\n"
                             "    /at +15 core.weechat print phone to mom\n"
                             "  Display \"phone to dad\" in 2 hours:\n"
                             "    /at +2h core.weechat print phone to dad",
                             "list|%(at_time) %(cron_buffer) %(cron_keyword) %(cron_commands)",
                             "cron_at_cmd_cb", "")
        # load crontab
        cron_load()
        # timer
        weechat.hook_timer(60 * 1000, 60, 0, "cron_timer_cb", "")
