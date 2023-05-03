# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 by drubin <drubin at smartcube.co.za>
# Copyright (c) 2017 Sébastien Helleu <flashcode at flashtux.org>
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


# Allows you to visually see if there are updates to your weechat system.

# Versions:
#
# 0.6 flashcode - add compatibility with WeeChat >= 3.2 (XDG directories)
# 0.5 flashcode - fix URL with infos, fix download of infos, fix PEP8 errors
#                 and refactor code
# 0.4 drubin    - changed default weechat hostname
# 0.3 nils_2    - third release.
#               - *fixed bug* every time the item_bar was updated, script did a
#                 read access to homepage
#               - get python 2.x binary for hook_process (fix problem when
#                 python 3.x is default python
#                 version, requires WeeChat >= 0.3.4)
#               - new option "git pull". executes "git pull" if "true" and a
#                 new git version is available
# 0.2 nils_2    - second release.
#               - countdown to next stable release added.
#               - now using hook_signal(day_changed) instead of hook_timer()
#               └-> option "update_interval" is obsolet now.
#               - hook_config() added.
#               - type missmatched removed if git_compile_location wasn't set
# 0.1 drubin   - First release.
#              - Basic functionality with url getting and compairing version.

SCRIPT_NAME = "update_notifier"
SCRIPT_AUTHOR = "drubin <drubin at smartcube.co.za>"
SCRIPT_VERSION = "0.6"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Notifiers users of updates to weechat."

import_ok = True
import os
from time import *
try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: https://weechat.org/")
    import_ok = False


# script options
settings = {
    "uses_git": "false",
    "uses_devel": "false",
    "git_pull": "false",
    "git_compile_location": "",
    "update_text": "New devel version available",
    "update_text_stable": "New stable version %s available",
    "start_counting": "30",
    "start_countdown": "10",
    "next_stable_text": "%d day(s) left to version %s",
    "color_default": "default",
    "color_countdown": "red",
}

# Not a config because it should not change ever
URL_INFOS = "https://weechat.org/dev/info/all/"
INFOS_FILENAME = "infos.txt"
BAR_ITEM_NAME = "updnotf"

# How long to wait for download
TIMEOUT_DOWNLOAD = 60 * 1000


def un_cache_dir():
    options = {
        'directory': 'cache',
    }
    filename = weechat.string_eval_path_home('%%h/%s' % SCRIPT_NAME,
                                             {}, {}, options)
    if not os.path.isdir(filename):
        os.makedirs(filename, mode=0o700)
    return filename


def get_version(as_number=False):
    """Gets the version number of weechat, both number and string."""
    if as_number:
        return weechat.info_get("version_number", "")
    else:
        return weechat.info_get("version", "")


def get_filename_infos():
    """Return the path to the file with infos."""
    return os.path.join(un_cache_dir(), INFOS_FILENAME)


def get_cur_git_version():
    path = weechat.config_get_plugin("git_compile_location")
    if path == "":
        return None

    f = os.popen("cd %s && git rev-parse HEAD" % path)
    stuff = f.readline()
    f.close()
    return stuff.strip()


def do_git_pull():
    if (weechat.config_get_plugin("git_pull") == "false"):
        return
    path = weechat.config_get_plugin("git_compile_location")
    if path != "":
        f = os.popen("cd %s && git pull 2>&1" % path)
        stuff = f.readline()
        weechat.prnt("", weechat.prefix("action") +
                     weechat.color(weechat.config_color(
                         weechat.config_get("weechat.color.chat_nick_self"))) +
                     SCRIPT_NAME + ":")
        weechat.prnt("", stuff)
        f.close()


def get_info_ver(info):
    with open(get_filename_infos(), "r") as f:
        for line in f.readlines():
            items = line.strip().split(":", 1)
            if len(items) == 2 and items[0] == info:
                return items[1]
    return None


def un_download_cb(filename, command, rc, stdout, stderr):
    """Callback on download of URL."""

    if rc != 0:
        return weechat.WEECHAT_RC_OK

    weechat.bar_item_update(BAR_ITEM_NAME)

    version = get_version()
    version_num = get_version(as_number=True)
    compare_version = ""
    compare_version_num = ""
    update_avaliable = False
    global next_stable_text
    next_stable_text = ""

    # check for stable version first
    start_counting = weechat.config_get_plugin("start_counting")
    if start_counting != "":
        next_stable_date = get_info_ver("next_stable_date")
        lt = localtime()
        year, month, day = lt[0:3]  # today
        next_stable_date = next_stable_date.split("-")  # next_stable_date
        next_stable_date = (int(next_stable_date[0]), int(next_stable_date[1]),
                            int(next_stable_date[2]), 0, 0, 0, 0, 0, 0)
        next_stable_date = mktime(next_stable_date)
        today = year, month, day, 0, 0, 0, 0, 0, 0
        today = mktime(today)
        # calculate days till next_stable_date
        diff_day = (next_stable_date - today) // 60 // 60 // 24
        diff_day = "%1i" % (diff_day)

        # diff_day = 0  # test to pop up new stable text
        if (int(diff_day) > 0) and (int(diff_day) <= int(start_counting)):
            used_color = weechat.config_get_plugin("color_default")
            # TEN and counting....
            if (int(diff_day) <=
                    int(weechat.config_get_plugin("start_countdown"))):
                used_color = weechat.config_get_plugin("color_countdown")

            next_stable_text = weechat.config_get_plugin("next_stable_text")
            next_stable = get_info_ver("next_stable")
            if next_stable_text == "":
                next_stable_text = ("days left:" + weechat.color(used_color) +
                                    "%d" + weechat.color("reset") +
                                    " to stable: %s") % (
                                        int(diff_day), next_stable)
            else:
                next_stable_text = next_stable_text.replace(
                    "%d", weechat.color(used_color) + "%d" +
                    weechat.color("reset"))
                if next_stable_text.find("%s") >= 1:  # check for %s
                    next_stable_text = next_stable_text % (
                        int(diff_day), next_stable)
                else:
                    next_stable_text = next_stable_text % int(diff_day)
                update_avaliable = False
        elif (int(diff_day) <= 0):  # today a new stable version is available
            stable_number = get_info_ver("stable")
            next_stable_text = weechat.config_get_plugin("update_text_stable")
            if "%s" in next_stable_text >= 1:  # %s in string?
                next_stable_text = (next_stable_text % stable_number)
            return weechat.WEECHAT_RC_OK

    if weechat.config_get_plugin("uses_devel") == "true":
        compare_version_num = get_info_ver("next_stable_number")
        compare_version = get_info_ver("next_stable")
        update_avaliable = int(compare_version_num) > int(version_num)
    elif weechat.config_get_plugin("uses_git") == "true":
        git_cur = get_cur_git_version()
        if git_cur is not None:  # path to git dir exists?
            git_ver = get_info_ver("git")  # yes
            compare_version = git_cur
            update_avaliable = get_cur != git_ver
            if update_avaliable:
                do_git_pull()  # call git pull
        else:
            update_avaliable = False
    else:
        compare_version_num = get_info_ver("stable_number")
        compare_version = get_info_ver("stable")
        update_avaliable = int(compare_version_num) > int(version_num)

    if update_avaliable:
        next_stable_text = weechat.config_get_plugin("update_text")

    return weechat.WEECHAT_RC_OK


def un_update_cache():
    """Callback for building update item."""
    weechat.hook_process_hashtable("url:%s" % URL_INFOS,
                                   {"file_out": get_filename_infos()},
                                   TIMEOUT_DOWNLOAD,
                                   "un_download_cb", "")


def un_day_changed(data, signal, signal_data):
    un_update_cache()
    return weechat.WEECHAT_RC_OK


def un_config_changed(data, option, value):
    un_update_cache()
    return weechat.WEECHAT_RC_OK


def up_item_cb(data, buffer, args):
    return next_stable_text


def un_cmd(data, buffer, args):
    un_update_cache()
    return weechat.WEECHAT_RC_OK


if __name__ == '__main__' and import_ok and \
       weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)

    weechat.hook_command("upgrade_check", "Checks for upgrades", "",
                         "The bar item is called \"%s\"." % BAR_ITEM_NAME,
                         "", "un_cmd", "")

    weechat.bar_item_new(BAR_ITEM_NAME, 'up_item_cb', '')
    weechat.hook_signal("day_changed", "un_day_changed", "")
    weechat.hook_config("plugins.var.python." + SCRIPT_NAME + ".*",
                        "un_config_changed", "")

    # Update the cache when it starts up.
    un_update_cache()
