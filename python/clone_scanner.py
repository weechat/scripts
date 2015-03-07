# -*- coding: utf-8 -*-
#
# Clone Scanner, version 1.3 for WeeChat version 0.3
# Latest development version: https://github.com/FiXato/weechat_scripts
#
#   A Clone Scanner that can manually scan channels and
#   automatically scans joins for users on the channel
#   with multiple nicknames from the same host.
#
#   Upon join by a user, the user's host is compared to the infolist of
#   already connected users to see if they are already online from
#   another nickname. If the user is a clone, it will report it.
#   With the '/clone_scanner scan' command you can manually scan a chan.
#
#   See /set plugins.var.python.clone_scanner.* for all possible options
#   Use the brilliant iset.pl plugin (/weeget install iset) to see what they do
#   Or check the sourcecode below.
#
# Example output for an on-join scan result:
#   21:32:46  ▬▬▶ FiXato_Odie (FiXato@FiXato.net) has joined #lounge
#   21:32:46      FiXato_Odie is already on the channel as FiXato!FiXato@FiXato.Net and FiX!FiXaphone@FiXato.net
#
# Example output for a manual scan:
#   21:34:44 fixato.net is online from 3 nicks:
#   21:34:44  - FiXato!FiXato@FiXato.Net
#   21:34:44  - FiX!FiXaphone@FiXato.net
#   21:34:44  - FiXato_Odie!FiXato@FiXato.net
#
## History:
### 2011-09-11: FiXato:
#
# * version 0.1: initial release.
#     * Added an on-join clone scan. Any user that joins a channel will be
#       matched against users already on the channel.
#
# * version 0.2: manual clone scan
#     * Added a manual clone scan via /clone_scanner scan
#        you can specify a target channel with:
#         /clone_scanner scan #myChannelOnCurrentServer
#        or:
#         /clone_scanner scan Freenode.#myChanOnSpecifiedNetwork
#     * Added completion
#
### 2011-09-12: FiXato:
#
# * version 0.3: Refactor galore
#     * Refactored some code. Codebase should be DRYer and clearer now.
#     * Manual scan report lists by host instead of nick now.
#     * Case-insensitive host-matching
#     * Bugfixed the infolist memleak.
#     * on-join scanner works again
#     * Output examples added to the comments
#
### 2011-09-19
# * version 0.4: Option galore
#     * Case-insensitive buffer lookup fix.
#     * Made most messages optional through settings.
#     * Made on-join alert and clone report key a bit more configurable.
#     * Added formatting options for on-join alerts.
#     * Added format_message helper method that accepts multiple whitespace-separated weechat.color() options.
#     * Added formatting options for join messages
#     * Added formatting options for clone reports
#     * Added format_from_config helper method that reads the given formatting key from the config
#
# * version 0.5: cs_buffer refactoring
#     * dropping the manual cs_create_buffer call in favor for a cs_get_buffer() method
#
### 2012-02-10: FiXato:
#
# * version 0.6: Stop shoving that buffer in my face!
#     * The clone_scanner buffer should no longer pop up by itself when you load the script.
#       It should only pop up now when you actually a line needs to show up in the buffer.
#
# * version 0.7: .. but please pop it up in my current window when I ask for it
#     * Added setting plugins.var.python.clone_scanner.autofocus
#       This will autofocus the clone_scanner buffer in the current window if another window isn't
#       already showing it, and of course only when the clone_scanner buffer is triggered
#
### 2012-02-10: FiXato:
#
# * version 0.8: .. and only when it is first created..
#     * Prevents the buffer from being focused every time there is activity in it and not being shown in a window.
#
### 2012-04-01: FiXato:
#
# * version 0.9: Hurrah for bouncers...
#     * Added the option plugins.var.python.clone_scanner.compare_idents
#       Set it to 'on' if you don't want people with different idents to be marked as clones.
#       Useful on channels with bouncers.
#
### 2012-04-02: FiXato:
#
# * version 1.0: Bugfix
#     * Fixed the on-join scanner bug introduced by the 0.9 release.
#       I was not properly comparing the new ident@host.name key in all places yet.
#       Should really have tested this better ><
#
### 2012-04-03: FiXato:
#
# * version 1.1: Stop being so sensitive!
#     * Continuing to fix the on-join scanner bugs introduced by the 0.9 release.
#       The ident@host.name dict key wasn't being lowercased for comparison in the on-join scan.
#
# * version 1.2: So shameless!
#     * Added shameless advertising for my script through /clone_scanner advertise
#
### 2013-04-09: FiXato:
# * version 1.3: Such a killer rabbit
#     * Thanks to Curtis Sorensen aka killerrabbit clone_scanner.py now supports:
#       * local channels (&-prefixed)
#       * nameless channels (just # or &)
#
### 2014-12-07: FiXato:
# * version 1.4: Inefficiency Warning Patch
# WARNING! I recently noticed the  clone_scanner script is currently rather inefficient, and requires a rewrite.
#   It may cause nasty lag when there are a lot of concurrent joins on the channel, as it evaluates the nicklist on every join.
#   For servers like twitch.tv and bitlbee, you might want to exclude the server with the new setting:
#    /set plugins.var.python.clone_scanner.hooks.excluded_servers twitchtv,bitlbee
#   This script update is an emergency update to add the above option, and warn the users of this script.
#   You can disable this warning with: /set plugins.var.python.clone_scanner.lag_warning off
#
# * Other patches in this version include:
#     * Re-did how settings are handled, using nils_2's skeleton code
#     * Settings are now automatically memoized when changed
#     * Added options hooks.excluded_servers, hooks.explicit_servers and lag_warning
#     * Updated advertise option to include /script install clone_scanner.py
#     * Updated min version to 0.3.6, though this will prob change in the next version
#
## Acknowledgements:
# * Sebastien "Flashcode" Helleu, for developing the kick-ass chat/IRC
#    client WeeChat
# * ArZa, whose kickban.pl script helped me get started with using the
#   infolist results.
# * LayBot, for requesting the ident comparison
# * Curtis "killerrabbit" Sorensen, for sending in two pull-requests,
#   adding support for local and nameless channels.
# * nils_2 aka weechatter, for providing the excellent skeleton.py script
#
## TODO:
#   - REWRITE TO IMPROVE EFFICIENCY:
#     - Probably only do the infolist loop on self-join,
#       and from then on manually keep track of join/parts/quit/nick-changes
#   - Add option to enable/disable public clone reporting aka msg channels
#   - Add option to enable/disable scanning on certain channels
#   - Add cross-channel clone scan
#   - Add cross-server clone scan
#
## Copyright (c) 2011-2014 Filip H.F. "FiXato" Slagter,
#   <FiXato [at] Gmail [dot] com>
#   http://profile.fixato.org
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
SCRIPT_NAME     = "clone_scanner"
SCRIPT_AUTHOR   = "Filip H.F. 'FiXato' Slagter <fixato [at] gmail [dot] com>"
SCRIPT_VERSION  = "1.4"
SCRIPT_LICENSE  = "MIT"
SCRIPT_DESC     = "A Clone Scanner that can manually scan channels and automatically scans joins for users on the channel with multiple nicknames from the same host."
SCRIPT_COMMAND  = "clone_scanner"
SCRIPT_CLOSE_CB = "cs_close_cb"

import_ok = True

try:
  import weechat
except ImportError:
  print "This script must be run under WeeChat."
  import_ok = False

import re
cs_buffer = None
OPTIONS = {
  "autofocus":                           ("on", "Focus the clone_scanner buffer in the current window if it isn't already displayed by a window."),
  "compare_idents":                      ("off", "Match against ident@host.name instead of just the hostname. Useful if you don't want different people from bouncers marked as clones"),
  "display_join_messages":               ("off", "Display all joins in the clone_scanner buffer"),
  "display_onjoin_alert_clone_buffer":   ("on", "Display an on-join clone alert in the clone_scanner buffer"),
  "display_onjoin_alert_target_buffer":  ("on", "Display an on-join clone alert in the buffer where the clone was detected"),
  "display_onjoin_alert_current_buffer": ("off", "Display an on-join clone alert in the current buffer"),
  "display_scan_report_clone_buffer":    ("on", "Display manual scan reports in the clone buffer"),
  "display_scan_report_target_buffer":   ("off", "Display manual scan reports in the buffer of the scanned channel"),
  "display_scan_report_current_buffer":  ("on", "Display manual scan reports in the current buffer"),

  "clone_report_key":                    ("mask", "Which 'key' to display in the clone report: 'mask' for full hostmasks, or 'nick' for nicks"),
  "clone_onjoin_alert_key":              ("mask", "Which 'key' to display in the on-join alerts: 'mask' for full hostmasks, or 'nick' for nicks"),

  "colors.onjoin_alert.message":   ("red", "The on-join clone alert's message colour. Formats are space separated."),
  "colors.onjoin_alert.nick":      ("bold red", "The on-join clone alert's nick colour. Formats are space separated. Note: if you have colorize_nicks, this option might not work as expected."),
  "colors.onjoin_alert.channel":   ("red", "The on-join clone alert's channel colour. Formats are space separated."),
  "colors.onjoin_alert.matches":   ("bold red", "The on-join clone alert's matches (masks or nicks) colour. Formats are space separated. Note: if you have colorize_nicks, this option might not work as expected."),

  "colors.join_messages.message":    ("chat", "The base colour for the join messages."),
  "colors.join_messages.nick":       ("bold", "The colour for the 'nick'-part of the join messages. Note: if you have colorize_nicks, this option might not always work as expected."),
  "colors.join_messages.identhost":  ("chat", "The colour for the 'ident@host'-part of the join messages."),
  "colors.join_messages.channel":    ("bold", "The colour for the 'channel'-part of the join messages."),

  "colors.clone_report.header.message":          ("chat", "The colour of the clone report header."),
  "colors.clone_report.header.number_of_hosts":  ("bold", "The colour of the number of hosts in the clone report header."),
  "colors.clone_report.header.channel":          ("bold", "The colour of the channel name in the clone report header."),

  "colors.clone_report.subheader.message":        ("chat", "The colour of the clone report subheader."),
  "colors.clone_report.subheader.host":              ("bold", "The colour of the host in the clone report subheader."),
  "colors.clone_report.subheader.number_of_clones":  ("bold", "The colour of the number of clones in the clone report subheader."),

  "colors.clone_report.clone.message": ("chat", "The colour of the clone hit in the clone report message."),
  "colors.clone_report.clone.match":   ("chat", "The colour of the match details (masks or nicks) in the clone report."),

  "colors.mask.nick":      ("bold", "The formatting of the nick in the match mask."),
  "colors.mask.identhost": ("", "The formatting of the identhost in the match mask."),
  "hooks.explicit_servers": ("*", "Comma-separated, wildcard-supporting list of servers for which we should add hook to for monitoring clones. E.g. 'freenode,chat4all,esper*' or '*' (default)"),
  "hooks.excluded_servers": ("bitlbee,twitchtv", "Which servers should the hook *not* be valid for? There's no support for wildcards unfortunately. E.g.: 'bitlbee,twitchtv' to exclude servers named bitlbee and twitchtv (default)."),
  "lag_warning": ('on', 'Show temporary warning upon script load regarding the inefficiency of the script. Set to "off" to disable.')
}
hooks = set([])

def get_validated_key_from_config(setting):
  key = OPTIONS[setting]
  if key != 'mask' and key != 'nick':
    weechat.prnt("", "Key %s not found. Valid settings are 'nick' and 'mask'. Reverted the setting to 'mask'" % key)
    weechat.config_set_plugin("clone_report_key", "mask")
    key = "mask"
  return key

def format_message(msg, formats, reset_color='chat'):
  if type(formats) == str:
    formats = formats.split()
  formatted_message = msg
  needs_color_reset = False
  for format in formats:
    if format in ['bold', 'reverse', 'italic', 'underline']:
      end_format = '-%s' % format
    else:
      needs_color_reset = True
      end_format = ""
    formatted_message = "%s%s%s" % (weechat.color(format), formatted_message, weechat.color(end_format))
  if needs_color_reset:
    formatted_message += weechat.color(reset_color)
  return formatted_message

def format_from_config(msg, config_option):
  return format_message(msg, OPTIONS[config_option])

def on_join_scan_cb(data, signal, signal_data):
  network = signal.split(',')[0]
  if network in OPTIONS['hooks.excluded_servers'].split(','):
    return weechat.WEECHAT_RC_OK

  joined_nick = weechat.info_get("irc_nick_from_host", signal_data)
  join_match_data = re.match(':[^!]+!([^@]+@(\S+)) JOIN :?([#&]\S*)', signal_data)
  parsed_ident_host = join_match_data.group(1).lower()
  parsed_host = join_match_data.group(2).lower()
  if OPTIONS["compare_idents"] == "on":
    hostkey = parsed_ident_host
  else:
    hostkey = parsed_host

  chan_name = join_match_data.group(3)
  network_chan_name = "%s.%s" % (network, chan_name)
  chan_buffer = weechat.info_get("irc_buffer", "%s,%s" % (network, chan_name))
  if not chan_buffer:
    print "No IRC channel buffer found for %s" % network_chan_name
    return weechat.WEECHAT_RC_OK

  if OPTIONS["display_join_messages"] == "on":
    message = "%s%s%s%s%s" % (
      format_from_config(joined_nick, "colors.join_messages.nick"),
      format_from_config("!", "colors.join_messages.message"),
      format_from_config(parsed_ident_host, "colors.join_messages.identhost"),
      format_from_config(" JOINed ", "colors.join_messages.message"),
      format_from_config(network_chan_name, "colors.join_messages.channel"),
    )
    #Make sure message format is also applied if no formatting is given for nick
    message = format_from_config(message, "colors.join_messages.message")
    weechat.prnt(cs_get_buffer(), message)

  clones = get_clones_for_buffer("%s,%s" % (network, chan_name), hostkey)
  if clones:
    key = get_validated_key_from_config("clone_onjoin_alert_key")

    filtered_clones = filter(lambda clone: clone['nick'] != joined_nick, clones[hostkey])
    match_strings = map(lambda m: format_from_config(m[key], "colors.onjoin_alert.matches"), filtered_clones)

    join_string = format_from_config(' and ',"colors.onjoin_alert.message")
    masks = join_string.join(match_strings)
    message = "%s %s %s %s %s" % (
      format_from_config(joined_nick, "colors.onjoin_alert.nick"),
      format_from_config("is already on", "colors.onjoin_alert.message"),
      format_from_config(network_chan_name, "colors.onjoin_alert.channel"),
      format_from_config("as", "colors.onjoin_alert.message"),
      masks
    )
    message = format_from_config(message, 'colors.onjoin_alert.message')

    if OPTIONS["display_onjoin_alert_clone_buffer"] == "on":
      weechat.prnt(cs_get_buffer(),message)
    if OPTIONS["display_onjoin_alert_target_buffer"] == "on":
      weechat.prnt(chan_buffer, message)
    if OPTIONS["display_onjoin_alert_current_buffer"] == "on":
      weechat.prnt(weechat.current_buffer(),message)
  return weechat.WEECHAT_RC_OK

def cs_get_buffer():
  global cs_buffer

  if not cs_buffer:
    # Sets notify to 0 as this buffer does not need to be in hotlist.
    cs_buffer = weechat.buffer_new("clone_scanner", "", \
                "", SCRIPT_CLOSE_CB, "")
    weechat.buffer_set(cs_buffer, "title", "Clone Scanner")
    weechat.buffer_set(cs_buffer, "notify", "0")
    weechat.buffer_set(cs_buffer, "nicklist", "0")
    if OPTIONS["autofocus"] == "on":
      if not weechat.window_search_with_buffer(cs_buffer):
        weechat.command("", "/buffer " + weechat.buffer_get_string(cs_buffer,"name"))

  return cs_buffer

def cs_close_cb(*kwargs):
  """ A callback for buffer closing. """
  global cs_buffer

  #TODO: Ensure the clone_scanner buffer gets closed if its option is set and the script unloads

  cs_buffer = None
  return weechat.WEECHAT_RC_OK


def get_channel_from_buffer_args(buffer, args):
  server_name = weechat.buffer_get_string(buffer, "localvar_server")
  channel_name = args
  if not channel_name:
    channel_name = weechat.buffer_get_string(buffer, "localvar_channel")

  match_data = re.match('\A(irc.)?([^.]+)\.([#&]\S*)\Z', channel_name)
  if match_data:
    channel_name = match_data.group(3)
    server_name = match_data.group(2)

  return server_name, channel_name

#TODO: track the hosts + nicks ourselves instead of looking up the entire list every join...
def get_clones_for_buffer(infolist_buffer_name, hostname_to_match=None):
  matches = {}
  infolist = weechat.infolist_get("irc_nick", "", infolist_buffer_name)
  while(weechat.infolist_next(infolist)):
    ident_hostname = weechat.infolist_string(infolist, "host")
    host_matchdata = re.match('([^@]+)@(\S+)', ident_hostname)
    if not host_matchdata:
      continue

    hostname = host_matchdata.group(2).lower()
    ident = host_matchdata.group(1).lower()
    if OPTIONS["compare_idents"] == "on":
      hostkey = ident_hostname.lower()
    else:
      hostkey = hostname

    if hostname_to_match and hostname_to_match.lower() != hostkey:
      continue

    nick = weechat.infolist_string(infolist, "name")

    matches.setdefault(hostkey,[]).append({
      'nick': nick,
      'mask': "%s!%s" % (
        format_from_config(nick, "colors.mask.nick"),
        format_from_config(ident_hostname, "colors.mask.identhost")),
      'ident': ident,
      'ident_hostname': ident_hostname,
      'hostname': hostname,
    })
  weechat.infolist_free(infolist)

  #Select only the results that have more than 1 match for a host
  return dict((k, v) for (k, v) in matches.iteritems() if len(v) > 1)

def report_clones(clones, scanned_buffer_name, target_buffer=None):
  # Default to clone_scanner buffer
  if not target_buffer:
    target_buffer = cs_get_buffer()

  if clones:
    clone_report_header = "%s %s %s%s" % (
      format_from_config(len(clones), "colors.clone_report.header.number_of_hosts"),
      format_from_config("hosts with clones were found on", "colors.clone_report.header.message"),
      format_from_config(scanned_buffer_name, "colors.clone_report.header.channel"),
      format_from_config(":", "colors.clone_report.header.message"),
    )
    clone_report_header = format_from_config(clone_report_header, "colors.clone_report.header.message")
    weechat.prnt(target_buffer, clone_report_header)

    for (host, clones) in clones.iteritems():
      host_message = "%s %s %s %s" % (
        format_from_config(host, "colors.clone_report.subheader.host"),
        format_from_config("is online from", "colors.clone_report.subheader.message"),
        format_from_config(len(clones), "colors.clone_report.subheader.number_of_clones"),
        format_from_config("nicks:", "colors.clone_report.subheader.message"),
      )
      host_message = format_from_config(host_message, "colors.clone_report.subheader.message")
      weechat.prnt(target_buffer, host_message)

      for user in clones:
        key = get_validated_key_from_config("clone_report_key")
        clone_message = "%s%s" % (" - ", format_from_config(user[key], "colors.clone_report.clone.match"))
        clone_message = format_from_config(clone_message,"colors.clone_report.clone.message")
        weechat.prnt(target_buffer, clone_message)
  else:
    weechat.prnt(target_buffer, "No clones found on %s" % scanned_buffer_name)

def cs_command_main(data, buffer, args):
  if args[0:4] == 'scan':
    server_name, channel_name = get_channel_from_buffer_args(buffer, args[5:])
    clones = get_clones_for_buffer('%s,%s' % (server_name, channel_name))
    if OPTIONS["display_scan_report_target_buffer"] == "on":
      target_buffer = weechat.info_get("irc_buffer", "%s,%s" % (server_name, channel_name))
      report_clones(clones, '%s.%s' % (server_name, channel_name), target_buffer)
    if OPTIONS["display_scan_report_clone_buffer"] == "on":
      report_clones(clones, '%s.%s' % (server_name, channel_name))
    if OPTIONS["display_scan_report_current_buffer"] == "on":
      report_clones(clones, '%s.%s' % (server_name, channel_name), weechat.current_buffer())
  elif args[0:9] == 'advertise':
    weechat.command("", "/input insert /me is using FiXato's CloneScanner v%s for WeeChat. Get the latest version from: https://github.com/FiXato/weechat_scripts/blob/master/clone_scanner.py or /script install clone_scanner.py" % SCRIPT_VERSION)
  return weechat.WEECHAT_RC_OK

def cs_set_default_settings():
  global OPTIONS

  # Set default settings
  for option,value in OPTIONS.items():
    if not weechat.config_is_set_plugin(option):
        weechat.config_set_plugin(option, value[0])
        OPTIONS[option] = value[0]
    else:
        OPTIONS[option] = weechat.config_get_plugin(option)
    weechat.config_set_desc_plugin(option, '%s (default: "%s")' % (value[1], value[0]))

def toggle_refresh(pointer, name, value):
  global OPTIONS

  config_option          = name[len('plugins.var.python.' + SCRIPT_NAME + '.'):]  # get optionname
  OPTIONS[config_option] = value                                                  # save new value
  if config_option in ('hooks.excluded_servers', 'hooks.explicit_servers'):
    remove_hooks()
    add_hooks()
  weechat.config_set_plugin(config_option, value)
  return weechat.WEECHAT_RC_OK

def add_hooks():
  global hooks
  hooked_servers = OPTIONS['hooks.explicit_servers'].split(',')
  for server_name in hooked_servers:
    signal = "%s,irc_in2_join" % server_name
    # weechat.prnt('', "Adding hook on %s" % signal)
    hook = weechat.hook_signal(signal, "on_join_scan_cb", "")
    hooks.add(hook)

def remove_hooks():
  global hooks
  for hook in hooks:
    weechat.unhook(hook)
  hooks = set([])

if __name__ == "__main__" and import_ok:
  if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, SCRIPT_CLOSE_CB, ""):
    version = weechat.info_get("version_number", "") or 0
    if int(version) >= 0x00030600:
      if (not weechat.config_is_set_plugin('lag_warning') or weechat.config_get_plugin('lag_warning') == 'on'):
        weechat.prnt('', '%s%sWARNING! This %s script is currently rather inefficient, and requires a rewrite.' % (weechat.prefix('error'), weechat.color('red'), SCRIPT_NAME))
        weechat.prnt('', '%s  It may cause nasty lag when there are a lot of concurrent joins on the channel, as it evaluates the nicklist on every join.' % weechat.prefix('notice'))
        weechat.prnt('', '%s  For servers like twitch.tv and bitlbee, you might want to exclude the server with the new setting:' % weechat.prefix('notice'))
        weechat.prnt('', '%s  %s  /set plugins.var.python.clone_scanner.hooks.excluded_servers twitchtv,bitlbee' % (weechat.prefix("notice"), weechat.color('*white')))
        weechat.prnt('', '%s  This script update is an emergency update to add the above option, and warn the users of this script.' % weechat.prefix("notice"))
        weechat.prnt('', '%s  You can disable this warning with:%s /set plugins.var.python.clone_scanner.lag_warning off' % (weechat.prefix("notice"), weechat.color('*white')))

      cs_set_default_settings()
      cs_buffer = weechat.buffer_search("python", "clone_scanner")

      weechat.hook_config( 'plugins.var.python.%s.*' % SCRIPT_NAME, 'toggle_refresh', '' )
      add_hooks()

      weechat.hook_command(SCRIPT_COMMAND,
                            SCRIPT_DESC,
                            "[scan] [[plugin.][network.]channel] | [advertise] | [help]",
                            "the target_buffer can be: \n"
                            "- left out, so the current channel buffer will be scanned.\n"
                            "- a plain channel name, such as #weechat, in which case it will prefixed with the current network name\n"
                            "- a channel name prefixed with network name, such as Freenode.#weechat\n"
                            "- a channel name prefixed with plugin and network name, such as irc.freenode.#weechat\n"
                            "See /set plugins.var.python.clone_scanner.* for all possible configuration options",

                            " || scan %(buffers_names)"
                            " || advertise"
                            " || help",

                            "cs_command_main", "")
  else:
    weechat.prnt("","%s%s %s" % (weechat.prefix("error"),SCRIPT_NAME,": needs version 0.3.6 or higher"))
    weechat.command("","/wait 1ms /python unload %s" % SCRIPT_NAME)
