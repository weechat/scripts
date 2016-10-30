# -*- coding: utf-8 -*-
# zncnotice: weechat script to convert ZNC status PRIVMSGs to NOTICEs
# © 2016 Hugo Landau <hlandau@devever.net>  MIT License
# Tested with Weechat 1.5. Older versions may or may not work.
#
# Settings:
#   plugins.var.python.zncnotice.prefix=*
#     The nickname prefix used by ZNC for its psuedo-users. Usually * but can be
#     changed to something else. Must match the ZNC configuration. (default: "*")
#
# Instructions for use:
#   1. Load script.
#   2. If using a prefix other than *, set plugins.var.python.zncnotice.prefix.
#   3. PRIVMSGs from nicknames with that prefix will now be converted to NOTICEs.

SCRIPT_NAME = 'zncnotice'
SCRIPT_AUTHOR = 'hlandau'
SCRIPT_VERSION = '1.0.0'
SCRIPT_LICENSE = 'MIT'
SCRIPT_DESC = 'Convert privmsg to notice from nicks with a certain prefix (useful for ZNC)'

import weechat
import re

re_match = None

def set_re(prefix):
  global re_match
  if prefix == '':
    prefix = '*'
  re_match = re.compile(r'''^(:'''+re.escape(prefix)+r'''[^!]+![^ ]+) PRIVMSG ''')

def irc_in_privmsg(data, signal, server, args):
  return re_match.sub('\\1 NOTICE ', args)

def config_change(data, opt, value):
  set_re(value)
  return weechat.WEECHAT_RC_OK

if __name__ == '__main__':
  weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', '')

  settings = dict(prefix=['*','The nickname prefix used by ZNC for its psuedo-users. Usually * but can be changed to something else. Must match the ZNC configuration.'])
  for k, v in settings.items():
    if not weechat.config_is_set_plugin(k):
      weechat.config_set_plugin(k, v[0])

    weechat.config_set_desc_plugin(k, '%s (default: "%s")' % (v[1], v[0]))

  set_re(weechat.config_get_plugin('prefix'))
  weechat.hook_modifier('irc_in_privmsg', 'irc_in_privmsg', '')
  weechat.hook_config('plugins.var.python.zncnotice.prefix', 'config_change', '')
