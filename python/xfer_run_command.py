# -*- coding: utf-8 -*-

"""
xfer_run_command.py - a weechat script to run a command on xfer_ended signal

Settings:
    * plugins.var.python.xfer_run_command.command <string: the command to run>
      e.g. '/exec mailscript.sh someone@foo.bar -s "XFER {status_string}" -b "File: {filename}"'

Author: Michael Kebe <michael.kebe@gmail.com>
License: GPL3
Date: 25 Oct 2016
"""

import_ok = True

try:
  import weechat
except:
  print("You must run this script within Weechat!")
  print("http://www.weechat.org")
  import_ok = False

SCRIPT_NAME = "xfer_run_command"
SCRIPT_AUTHOR = "Michael Kebe <michael.kebe@gmail.com>"
SCRIPT_VERSION = "0.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC = "Runs a command on xfer_ended signal with acces to data (with trigger not possible)"


OPTIONS = {
  "command" : ("", "This command will be run on xfer_ended signal. You can use the following placeholders: {status_string}, {filename}, {local_filename}, {size}, {remote_nick}."),
}


def xfer_ended_signal_cb(data, signal, signal_data):
  weechat.infolist_next(signal_data)

  command_template = weechat.config_get_plugin("command")
  command_string = command_template.format(
    status_string = weechat.infolist_string(signal_data, 'status_string'),
    filename = weechat.infolist_string(signal_data, 'filename'),
    local_filename = weechat.infolist_string(signal_data, 'local_filename'),
    size = weechat.infolist_string(signal_data, 'size'),
    remote_nick = weechat.infolist_string(signal_data, 'remote_nick'),
  )
  
  rc = weechat.command('', command_string)
  if rc != weechat.WEECHAT_RC_OK:
    weechat.prnt('', "xfer_run_command: there was a problem running command: " + command_string)

  return weechat.WEECHAT_RC_OK


def init_config():
  global OPTIONS
  for option, value in OPTIONS.items():
    weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))
    if not weechat.config_is_set_plugin(option):
      weechat.config_set_plugin(option, value[0])


if __name__ == "__main__" and import_ok:
  if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    init_config()
    weechat.hook_signal('xfer_ended', 'xfer_ended_signal_cb', '')

