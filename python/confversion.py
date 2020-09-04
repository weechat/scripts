# -*- coding: utf-8 -*-
#
# Copyright (c) 2010-2010 by drubin <drubin at smartcube.co.za>
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


# Allows you to visually see if there are updates to your weechat system

#Versions
# 0.1 drubin     - First release.
#                - Basic functionality to save version history of your config files (only git, bzr)
# 0.2 ShockkPony - Fixed massive weechat startup time caused by initial config loading
# 0.3 noctux     - Adapt to python 3

SCRIPT_NAME    = "confversion"
SCRIPT_AUTHOR  = "drubin <drubin at smartcube.co.za>"
SCRIPT_VERSION = "0.3"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Stores version controlled history of your configuration files"

import_ok = True
import subprocess
try:
    import weechat
except ImportError:
    print("This script must be run under WeeChat.")
    print("Get WeeChat now at: http://www.weechat.org/")
    import_ok = False


# script options
settings = {
    #Currently supports git and bzr and possibly other that support simple "init" "add *.conf" "commit -m "message" "
    "versioning_method"   : "git",
    "commit_each_change"  : "true",
    "commit_message"      : "Commiting changes",
    #Allows you to not auto commit stuff that relates to these configs
    #, (comma) seperated list of config options
    #The toggle_nicklist script can make this property annoying.
    "auto_commit_ignore"  : "weechat.bar.nicklist.hidden",
}

def shell_in_home(cmd):
    try:
        output = open("/dev/null","w")
        subprocess.Popen(ver_method()+" "+cmd, cwd = weechat_home(),
            stdout= output, stderr=output, shell=True)
    except Exception as e:
        print(e)

def weechat_home():
    return weechat.info_get ("weechat_dir", "")

def ver_method():
    return weechat.config_get_plugin("versioning_method")

def init_repo():
    #Set up version control (doesn't matter if previously setup for bzr, git)
    shell_in_home("init")
    #Save first import OR on start up if needed.
    commit_cb()

confversion_commit_finish_hook = 0

def commit_cb(data=None, remaning=None):
    global confversion_commit_finish_hook

    # only hook timer if not already hooked
    if confversion_commit_finish_hook == 0:
        confversion_commit_finish_hook = weechat.hook_timer(500, 0, 1, "commit_cb_finish", "")

    return weechat.WEECHAT_RC_OK

def commit_cb_finish(data=None, remaining=None):
    global confversion_commit_finish_hook

    # save before doing commit
    weechat.command("","/save")

    # add all config changes to git
    shell_in_home("add ./*.conf")

    # do the commit
    shell_in_home("commit -m \"%s\"" % weechat.config_get_plugin("commit_message"))

    # set hook back to 0
    confversion_commit_finish_hook = 0

    return weechat.WEECHAT_RC_OK

def conf_update_cb(data, option, value):
    #Commit data if not part of ignore list.
    if weechat.config_get_plugin("commit_each_change") == "true"  and not option in weechat.config_get_plugin("auto_commit_ignore").split(","):
        #Call use pause else /save will be called before the config is actually saved to disc
        #This is kinda hack but better input would be appricated.
        weechat.hook_timer(500, 0, 1, "commit_cb", "")
    return weechat.WEECHAT_RC_OK

def confversion_cmd(data, buffer, args):
    commit_cb()
    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.items():
        if weechat.config_get_plugin(option) == "":
            weechat.config_set_plugin(option, default_value)

    weechat.hook_command("confversion", "Saves configurations to version control", "",
                         "",
                         "", "confversion_cmd", "")
    init_repo()
    hook = weechat.hook_config("*", "conf_update_cb", "")
