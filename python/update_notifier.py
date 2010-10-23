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
# 0.1 drubin - First release.
#            - Basic functionality with url getting and compairing version.

SCRIPT_NAME    = "update_notifier"
SCRIPT_AUTHOR  = "drubin <drubin at smartcube.co.za>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Notifiers users of updates to weechat."

import_ok = True
import os
try:
    import weechat
except ImportError:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False
    
    
# script options
settings = {
    "uses_git"                  : "false",
    "uses_devel"                : "false",
    "git_compile_location"      : "",
    #In seconds
    "update_interval"           : "%s"  % (60*60*24) , #Default is to check every day
    "update_text"               : "New Version Available",
}

infos = ["stable","stable_number","git","next_stable","next_stable_number"]

#Not a config because it should not change ever
BASE_URL = "http://www.weechat.net/info/"
BAR_NAME = "updnotf"


#List of proccesses
un_hook_process = {}

#How long to wait for download
TIMEOUT_DOWNLOAD = 60 * 1000

def un_cache_dir():
    filename =  weechat.info_get("weechat_dir", "") + os.sep+ SCRIPT_NAME
    if not os.path.isdir(filename):
        os.makedirs(filename, mode=0700)
    return filename
    
def get_version(isnumber = False):
    """Gets the version number of weechat, both number and string"""
    if isnumber:
        return weechat.info_get("version_number", "")
    else:
        return weechat.info_get("version", "")
        
def full_file_name(filename):
     path = un_cache_dir() + os.sep + filename
     return path

def un_timer_cache(date,remaning):
    un_update_cache()
    return weechat.WEECHAT_RC_OK 


def un_update_cache():
    for info in infos:
        un_download_url(BASE_URL+info,info)

        
def get_cur_git_version():
    path = weechat.config_get_plugin("git_compile_location")
    f = os.popen("cd %s && git rev-parse HEAD" % path)
    stuff = f.readline()
    f.close()
    return stuff.strip()
    

def get_info_ver(info):
    filecontents = file(full_file_name(info)).read().strip()
    return filecontents      

def un_download_url(url, filename):
    pathfile = full_file_name(filename)
    un_hook_process[filename] = weechat.hook_process(
        "python -c \"import urllib, urllib2\n"
        "req = urllib2.Request('" + url + "')\n"
        "try:\n"
        "    response = urllib2.urlopen(req)\n"
        "    file = open('" + pathfile + "', 'w')\n"
        "    file.write(response.read())\n"
        "    response.close()\n"
        "    file.close()\n"
        "except urllib2.URLError, e:\n"
        "    print 'error:%s' % e.code\n"
        "\"",
        TIMEOUT_DOWNLOAD, "un_download_cb", filename)

def un_download_cb(filename, command, rc, stdout, stderr):
    un_hook_process[filename] = ""
    #Update configs..
    weechat.bar_item_update(BAR_NAME)
    return weechat.WEECHAT_RC_OK
    
    
    
def up_item_cb(data, buffer, args):
    """ Callback for building update item. """
    version = get_version()
    version_num = get_version(True)
    
    compare_version = ""
    compare_version_num = ""
    
    update_avaliable = False
    
    if weechat.config_get_plugin("uses_devel") == "true":
        compare_version_num = get_info_ver("next_stable_number")
        compare_version = get_info_ver("next_stable")
        update_avaliable = int(compare_version_num) > int(version_num)
    elif weechat.config_get_plugin("uses_git") == "true":
        git_cur = get_cur_git_version()
        git_ver = get_info_ver("git")
        compare_version = git_cur
        update_avaliable = get_cur_git_version() != git_ver
    else:
        compare_version_num = get_info_ver("stable_number")
        compare_version = get_info_ver("stable")
        update_avaliable = int(compare_version_num) > int(version_num)
    
    if update_avaliable:
        return weechat.config_get_plugin("update_text")
    else: 
        return ""
    

def un_cmd(data, buffer, args):
    un_update_cache()

    return weechat.WEECHAT_RC_OK

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE,
                    SCRIPT_DESC, "", ""):
    for option, default_value in settings.iteritems():
        if weechat.config_get_plugin(option) == "":
            weechat.config_set_plugin(option, default_value)
            
    weechat.hook_command("upgrade_check", "Checks for upgrades", "",
                         "",
                         "", "un_cmd", "")        
            
            
    weechat.bar_item_new(BAR_NAME, 'up_item_cb', '')
    weechat.hook_timer(int(weechat.config_get_plugin("update_interval")) * 1000, 0, 0, "un_timer_cache", "")
    #Update the cache when it starts up.
    un_update_cache()
