#Author: Pawel Pogorzelski <pawelpogorzelski AT gmail DOT com>
#What it does: This script shows the currently played song in sonata 
#Usage: /weesonata - Displays the songname
#Released under GNU GPL v2 or newer

#/usr/bin/python
#coding: utf-8

import weechat
import re
import codecs
from os import popen

weechat.register ('weesonata', '0.01', '', """sonata-weechat current song script (usage: /weesonata)""")
weechat.add_command_handler ('weesonata', 'show_it_to_them')

default = {
  "msg_head": "is playing",
  "msg_tail": "with sonata",
  "spacer": "*",
}

for k, v in default.items():
  if not weechat.get_plugin_config(k):
    weechat.set_plugin_config(k, v)

def show_it_to_them(server, args):
	spacer = weechat.get_plugin_config("spacer")
	msg_tail = weechat.get_plugin_config("msg_tail")
	msg_head = weechat.get_plugin_config("msg_head")
	sonata_info = popen ('sonata info')
	if sonata_info.readline().rstrip().find('MPD')==-1:
		sonata_info = popen ('sonata info')
		song_name_text = sonata_info.readline().rstrip().split(': ')
		song_artist_text = sonata_info.readline().rstrip().split(': ')
		album_text = sonata_info.readline().rstrip().split(': ')
		date_text = sonata_info.readline().rstrip().split(': ')
		track_text = sonata_info.readline().rstrip().split(': ')
		type_text = sonata_info.readline().rstrip().split(': ')
		file_text = sonata_info.readline().rstrip().split(': ')
		time_text = sonata_info.readline().rstrip().split(': ')
		bitrate_text = sonata_info.readline().rstrip().split(': ')
		all = '/me ' + " " + msg_head + " " +  song_name_text[1] + " " + spacer + " " + song_artist_text[1] + " " + spacer + " " + time_text[1] + " " + spacer + " " + bitrate_text[1] + "kbit/s " + spacer + " "+ msg_tail 
	else :
		all = '/me listens to silence :)'
	weechat.command(all)
	return 0

