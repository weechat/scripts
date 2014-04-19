# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 by Filip H.F. "FiXato" Slagter <fixato+weechat@gmail.com>
#
# Shutup: a quick WeeChat script to replace text from specified users with
#         random or preset text as a way to hide their actual text.
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
# 2014-01-31: FiXato, (freenode.#weechat)
#       0.1 : initial release
#
# requires: WeeChat version 0.3.6 or higher
#
# Thanks go out to nils_2 for providing his skeleton.py template, available at https://github.com/weechatter/weechat-scripts/blob/master/python/skeleton.py
#
# Development is currently hosted at
# https://github.com/FiXato/weechat_scripts

try:
  import weechat,re
  from random import choice

except Exception:
  print "This script must be run under WeeChat."
  print "Get WeeChat now at: http://www.weechat.org/"
  quit()

SCRIPT_NAME     = "shutup"
SCRIPT_AUTHOR   = 'Filip H.F. "FiXato" Slagter <FiXato+weechat@gmail.com>'
SCRIPT_VERSION  = "0.2"
SCRIPT_LICENSE  = "GPL"
SCRIPT_DESC     = "Replace text from specified IRC users with random or preset text as a way to hide their actual text. Unlike /filter it won't hide the line (and thus can't be toggled either), and has access to the entire hostmask for comparison. Can be useful to mute users while still seeing that they are active."

OPTIONS         = {
                    'replacement_text'        : ('','Replacement text for everything the muted user says. Leave empty to use random lines from the Jabberwocky poem.'),
                    'muted_masks'             : ('','Space-separated regular expressions that will be matched against the nick!ident@host.mask. Any user matching will get their message muted. Can also include a comma-separated list of channels for every regular expression separated from the regexp by a colon. Prefix regexp with (?i) if you want it to be case insensitive. Example: "@\S+\.aol\.com$:#comcast,#AT&T (?i)!root@\S+" would mute messages in channels #comcast and #AT&T from users whose hosts end in *.aol.com, as well as all users who have any case variation of root as ident regardless of channel.'),
                  }
DEBUG = False
jabberwocky = """
'Twas brillig, and the slithy toves
Did gyre and gimble in the wabe;
All mimsy were the borogoves,
And the mome raths outgrabe.

"Beware the Jabberwock, my son!
The jaws that bite, the claws that catch!
Beware the Jubjub bird, and shun
The frumious Bandersnatch!"

He took his vorpal sword in hand:
Long time the manxome foe he sought—
So rested he by the Tumtum tree,
And stood awhile in thought.

And as in uffish thought he stood,
The Jabberwock, with eyes of flame,
Came whiffling through the tulgey wood,
And burbled as it came!

One, two! One, two! and through and through
The vorpal blade went snicker-snack!
He left it dead, and with its head
He went galumphing back.

"And hast thou slain the Jabberwock?
Come to my arms, my beamish boy!
O frabjous day! Callooh! Callay!"
He chortled in his joy.

'Twas brillig, and the slithy toves
Did gyre and gimble in the wabe;
All mimsy were the borogoves,
And the mome raths outgrabe.
"""
replacement_lines = filter(None, jabberwocky.splitlines())

def random_replacement_line(lines = replacement_lines):
  return choice(lines)

def replacement_line():
  global OPTIONS
  if OPTIONS['replacement_text'] == '':
    return random_replacement_line()
  return OPTIONS['replacement_text']

# Easily use weechat colors in the script
#   text = substitute_colors('my text ${color:yellow}yellow${color:default} colored.')
# eval_expression():  to match ${color:nn} tags
regex_color=re.compile('\$\{color:([^\{\}]+)\}')
def substitute_colors(text):
  if int(version) >= 0x00040200:
    return weechat.string_eval_expression(text,{},{},{})
  # substitute colors in output
  return re.sub(regex_color, lambda match: weechat.color(match.group(1)), text)

# ===================[ weechat options & description ]===================
def init_options():
  for option,value in OPTIONS.items():
    if not weechat.config_is_set_plugin(option):
      weechat.config_set_plugin(option, value[0])
      toggle_refresh(None, 'plugins.var.python.' + SCRIPT_NAME + '.' + option, value[0])
    else:
      toggle_refresh(None, 'plugins.var.python.' + SCRIPT_NAME + '.' + option, weechat.config_get_plugin(option))
    weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def debug(str):
  if DEBUG:
    weechat.prnt("", str)

def update_muted_masks(masks):
  global muted_masks
  muted_masks = {}
  for mask in masks.split():
    if '#' in mask:
      mask, chan = mask.split(':',1)
      channels = [channel.lower() for channel in chan.split(',')]
    else:
      channels = []
    muted_masks[mask] = [re.compile(mask), channels]
  debug('muted masks: %s' % muted_masks)

def toggle_refresh(pointer, name, value):
  global OPTIONS
  option = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]        # get optionname
  OPTIONS[option] = value                                               # save new value
  if option == 'muted_masks':
    update_muted_masks(value)
  return weechat.WEECHAT_RC_OK

def shutup_cb(data, modifier, modifier_data, string):
  dict_in = { "message": string }
  message_ht = weechat.info_get_hashtable("irc_message_parse", dict_in)

  hostmask = message_ht['host']
  arguments = message_ht['arguments']
  channel = message_ht['channel']

  new_arguments = re.sub(r'^%s :.+' % channel, lambda x: '%s :%s' % (channel, replacement_line()), arguments)
  new_string = re.sub(r'%s$' % re.escape(arguments), lambda x: new_arguments, string)

  for key, [mask_regexp, channels] in muted_masks.iteritems():
    # If there is one or more channels listed for this mask regexp, and none of them match the current channel, continue to the next mute mask
    if len(channels) > 0 and channel.lower() not in channels:
      debug("%s doesn't match any of the listed channels: %s" % (channel, channels))
      continue

    # If the hostmask matches the mask regular expression, return the new, manipulated, string.
    debug("comparing %s to %s" % (mask_regexp.pattern, hostmask))
    if mask_regexp.search(hostmask):
      debug("  %s matches %s" % (mask_regexp.pattern, hostmask))
      return new_string
  # Nothing matches, so return the original, unmodified, string
  return string

# ================================[ main ]===============================
if __name__ == "__main__":
  if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''):
    version = weechat.info_get("version_number", "") or 0

    if int(version) >= 0x00030600:
      # init options from your script
      init_options()
      # create a hook for your options
      weechat.hook_config( 'plugins.var.python.' + SCRIPT_NAME + '.*', 'toggle_refresh', '' )
    else:
      weechat.prnt("","%s%s %s" % (weechat.prefix("error"),SCRIPT_NAME,": needs version 0.3.6 or higher"))
      weechat.command("","/wait 1ms /python unload %s" % SCRIPT_NAME)

    hook = weechat.hook_modifier("irc_in_privmsg", "shutup_cb", "")
