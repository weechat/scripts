# -*- coding: utf-8 -*-
###
# Copyright (c) 2009 by Elián Hanisch <lambdae2@gmail.com>
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
###

###
# Search in Weechat buffers and logs (for Weechat 0.3.*)
#
#   Inspired by xt's grep.py
#   Originally I just wanted to add some fixes in grep.py, but then
#   I got carried away and rewrote everything, so new script.
#
#   Commands:
#   * /egrep
#     Search in logs or buffers, see /help egrep
#   * /logs:
#     Lists logs in ~/.weechat/logs, see /help logs
#
#   Settings:
#   * plugins.var.python.egrep.clear_buffer:
#     Clear the results buffer before each search. Valid values: on, off
#
#   * plugins.var.python.egrep.go_to_buffer:
#     Automatically go to egrep buffer when search is over. Valid values: on, off
#
#   * plugins.var.python.egrep.log_filter:
#     Coma separated list of patterns that egrep will use for exclude logs, e.g.
#     if you use '*server/*' any log in the 'server' folder will be excluded
#     when using the command '/egrep log'
#
#   * plugins.var.python.egrep.show_summary:
#     Shows summary for each log. Valid values: on, off
#
#   * plugins.var.python.egrep.max_lines:
#     egrep will only print the last matched lines that don't surpass the value defined here.
#
#
#   TODO:
#   * grepping should run in background for big logs
#   * possibly add option for defining time intervals
#
#
#   History:
#   2010-01-04
#   version 0.5.4.1: fix index error when using --after/before-context options.
#
#   2010-01-03
#   version 0.5.4: new features
#   * added --after-context and --before-context options.
#   * added --context as a shortcut for using both -A -B options.
#
#   2009-11-06
#   version 0.5.3: improvements for long grep output
#   * egrep buffer input accepts the same flags as /egrep for repeat a search with different
#     options.
#   * tweaks in egrep's output.
#   * max_lines option added for limit egrep's output.
#   * code in update_buffer() optimized.
#   * time stats in buffer title.
#   * added go_to_buffer config option.
#   * added --buffer for search only in buffers.
#   * refactoring.
#
#   2009-10-12, omero
#   version 0.5.2: made it python-2.4.x compliant
#
#   2009-08-17
#   version 0.5.1: some refactoring, show_summary option added.
#
#   2009-08-13
#   version 0.5: rewritten from xt's grep.py
#   * fixed searching in non weechat logs, for cases like, if you're
#     switching from irssi and rename and copy your irssi logs to %h/logs
#   * fixed "timestamp rainbow" when you /grep in grep's buffer
#   * allow to search in other buffers other than current or in logs
#     of currently closed buffers with cmd 'buffer'
#   * allow to search in any log file in %h/logs with cmd 'log'
#   * added --count for return the number of matched lines
#   * added --matchcase for case sensible search
#   * added --hilight for color matches
#   * added --head and --tail options, and --number
#   * added command /logs for list files in %h/logs
#   * added config option for clear the buffer before a search
#   * added config option for filter logs we don't want to grep
#   * added the posibility to repeat last search with another regexp by writing
#     it in egrep's buffer
#   * changed spaces for tabs in the code, which is my preference
#
###

import os.path as path
import getopt, time

now = time.time

try:
    import weechat
    WEECHAT_RC_OK = weechat.WEECHAT_RC_OK
    import_ok = True
except ImportError:
    import_ok = False

SCRIPT_NAME    = "egrep"
SCRIPT_AUTHOR  = "Elián Hanisch <lambdae2@gmail.com>"
SCRIPT_VERSION = "0.5.4.1"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Search in buffers and logs"
SCRIPT_COMMAND = "egrep"

script_nick    = '***'

### class definitions
class linesDict(dict):
	"""
	Class for handling matched lines in more than one buffer.
	linesDict[buffer_name] = matched_lines_list
	"""
	def __setitem__(self, key, value):
		assert isinstance(value, list)
		if key not in self:
			dict.__setitem__(self, key, value)
		else:
			dict.__getitem__(self, key).extend(value)

	def get_matches_count(self):
		"""Return the sum of total matches stored."""
		if dict.__len__(self):
			return sum(map(lambda L: L.matches_count, self.itervalues()))
		else:
			return 0

	def __len__(self):
		"""Return the sum of total lines stored."""
		if dict.__len__(self):
			return sum(map(len, self.itervalues()))
		else:
			return 0

	def __str__(self):
		"""Returns buffer count or buffer name if there's just one stored."""
		n = len(self.keys())
		if n == 1:
			return self.keys()[0]
		elif n > 1:
			return '%s logs' %n
		else:
			return ''

	def strip_separator(self):
		for L in self.itervalues():
			L.strip_separator()

class linesList(list):
	"""Class for list of matches, since sometimes I need to add lines that aren't matches, I need an
	independent counter."""
	_sep = '...'
	def __init__(self):
		self.matches_count = 0

	def append_separator(self):
		"""adds a separator into the list, makes sure it doen't add two together."""
		s = self._sep
		if (self and self[-1] != s) or not self:
			self.append(s)

	def count_match(self):
		self.matches_count += 1

	def strip_separator(self):
		"""removes separators if there are first or/and last in the list."""
		if self:
			s = self._sep
			if self[0] == s:
				del self[0]
			if self[-1] == s:
				del self[-1]


### config
settings = {
		'clear_buffer' :'off', # Should clear the buffer before every search
		'log_filter'   :'',    # filter for exclude log files
		'go_to_buffer' :'on',
		'max_lines'    :'4000',
		'show_summary' :'on'}  # Show summary line after the search

### value validation
boolDict = {'on':True, 'off':False}
def get_config_boolean(config):
    value = weechat.config_get_plugin(config)
    try:
        return boolDict[value]
    except KeyError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is invalid, allowed: 'on', 'off'" %value)
        return boolDict[default]

def get_config_int(config):
    value = weechat.config_get_plugin(config)
    try:
        return int(value)
    except ValueError:
        default = settings[config]
        error("Error while fetching config '%s'. Using default value '%s'." %(config, default))
        error("'%s' is not a number." %value)
        return int(default)

def get_config_log_filter():
	filter = weechat.config_get_plugin('log_filter')
	if filter:
		return filter.split(',')
	else:
		return []

def get_home():
	home = weechat.config_string(weechat.config_get('logger.file.path'))
	return home.replace('%h', weechat.info_get('weechat_dir', ''))

### messages
def debug(s, prefix='debug'):
	"""Debug msg"""
	weechat.prnt('', '%s: %s'  %(prefix,s))

def error(s, prefix=SCRIPT_NAME, buffer=''):
	"""Error msg"""
	weechat.prnt(buffer, '%s%s: %s' %(weechat.prefix('error'), prefix, s))

def say(s, prefix=SCRIPT_NAME, buffer=''):
	"""normal msg"""
	weechat.prnt(buffer, '%s: %s' %(prefix, s))

### log files and buffers
cache_dir = {} # for avoid walking the dir tree more than once per command
def dir_list(dir, filter_list=(), filter_excludes=True):
	"""Returns a list of files in 'dir' and its subdirs."""
	global cache_dir
	import fnmatch
	#debug('dir_list: listing in %s' %dir)
	if dir in cache_dir:
		#debug('dir_list: using dir cache.')
		return cache_dir[dir]

	def append_files(arg, dir, fnames):
		arg.extend(map(lambda s:path.join(dir, s), fnames))

	def filter(file):
		if path.isdir(file):
			return True
		elif filter_list:
			file = file[len(dir):] # pattern shouldn't match home dir
			for pattern in filter_list:
				if fnmatch.fnmatch(file, pattern):
					return filter_excludes
		return not filter_excludes

	file_list = []
	filter_list = filter_list or get_config_log_filter()
	#debug('filter: %s' %filter_list)
	path.walk(dir, append_files, file_list) # get a list of log files, including in subdirs
	file_list = [ file for file in file_list if not filter(file) ]
	cache_dir[dir] = file_list
	return file_list

def get_file_by_pattern(pattern, all=False):
	"""Returns the first log whose path matches 'pattern',
	if all is True returns all logs that matches."""
	global home_dir
	if not pattern: return []
	#debug('get_file_by_filename: searching for %s.' %pattern)
	file = path.join(home_dir, pattern)
	if not path.isfile(file):
		# lets see if there's a log matching pattern
		import fnmatch
		file = []
		file_list = dir_list(home_dir)
		n = len(home_dir)
		for log in file_list:
			basename = log[n:]
			if fnmatch.fnmatch(basename, pattern):
				file.append(log)
				if not all: break
	else:
		file = [file]
	#debug('get_file_by_filename: got %s.' %file)
	return file

def get_file_by_buffer(buffer):
	"""Given buffer pointer, finds log's path or returns None."""
	#debug('get_file_by_buffer: searching for %s' %buffer)
	file = None
	log_enabled = False
	infolist = weechat.infolist_get('logger_buffer', '', '')
	while weechat.infolist_next(infolist):
		pointer = weechat.infolist_pointer(infolist, 'buffer')
		if pointer == buffer:
			file = weechat.infolist_string(infolist, 'log_filename')
			log_enabled = weechat.infolist_integer(infolist, 'log_enabled')
			break
	weechat.infolist_free(infolist)
	#debug('get_file_by_buffer: log_enabled: %s got: %s' %(log_enabled, file))
	if not log_enabled:
		return None
	return file

def get_file_by_name(buffer_name):
	"""Given a buffer name, returns its log path or None. buffer_name should be in 'server.#channel'
	or '#channel' format."""
	#debug('get_file_by_name: searching for %s' %buffer_name)
	# get common mask options
	masks = [weechat.config_string(weechat.config_get('logger.mask.irc'))]
	masks.append(weechat.config_string(weechat.config_get('logger.file.mask')))
	# I can't see how to replace all the local vars in mask nicely, so I just replace $channel,
	# $server and other local vars, replace the unreplaced vars left with '*', and use it as
	# a mask for get the path with get_file_by_pattern
	for mask in masks:
		#debug('get_file_by_name: mask: %s' %mask)
		if '$name' in mask:
			mask = mask.replace('$name', buffer_name)
		elif '$channel' in mask or '$server' in mask or '$short_name' in mask:
			if '.' in buffer_name and \
					'#' not in buffer_name[:buffer_name.find('.')]: # the dot isn't part of the channel name
				#	 ^ I'm asuming channel starts with #, i'm lazy.
				server, channel = buffer_name.split('.', 1)
			else:
				server, channel = '', buffer_name
			mask = mask.replace('$short_name', channel)
			mask = mask.replace('$channel', channel)
			if server:
				mask = mask.replace('$server', server)
		# change the unreplaced vars by '*'
		if '$' in mask:
			chars = 'abcdefghijklmnopqrstuvwxyz_'
			masks = mask.split('$')
			masks = map(lambda s: s.lstrip(chars), masks)
			mask = '*'.join(masks)
			if mask[0] != '*':
				mask = '*' + mask
		#debug('get_file_by_name: using mask %s' %mask)
		file = get_file_by_pattern(mask)
		if file:
			return file
	return None

def get_buffer_by_name(buffer_name):
	"""Given a buffer name returns its buffer pointer or None."""
	#debug('get_buffer_by_name: searching for %s' %buffer_name)
	pointer = weechat.buffer_search('', buffer_name)
	if not pointer:
		infolist = weechat.infolist_get('buffer', '', '')
		while weechat.infolist_next(infolist) and not pointer:
			name = weechat.infolist_string(infolist, 'name')
			if buffer_name in name:
				#debug('get_buffer_by_name: found %s' %name)
				pointer = weechat.buffer_search('', name)
		weechat.infolist_free(infolist)
	#debug('get_buffer_by_name: got %s' %pointer)
	if pointer:
		return pointer
	return None

def get_all_buffers():
	"""Returns list with pointers of all open buffers."""
	buffers = []
	infolist = weechat.infolist_get('buffer', '', '')
	while weechat.infolist_next(infolist):
		buffers.append(weechat.infolist_pointer(infolist, 'pointer'))
	weechat.infolist_free(infolist)
	return buffers

### grep
def make_regexp(pattern, matchcase=False):
	"""Returns a compiled regexp."""
	if pattern in ('.', '.*', '.?', '.+'):
		# because I don't need to use a regexp if we're going to match all lines
		return None
	try:
		import re
		if not matchcase:
			regexp = re.compile(pattern, re.IGNORECASE)
		else:
			regexp = re.compile(pattern)
	except Exception, e:
		raise Exception, 'Bad pattern, %s' %e
	return regexp

def check_string(s, regexp, hilight='', exact=False):
	"""Checks 's' with a regexp and returns it if is a match."""
	if not regexp:
		return s
	elif exact:
		matchlist = regexp.findall(s)
		if matchlist:
			return ' '.join(matchlist)
	elif hilight:
		matchlist = regexp.findall(s)
		if matchlist:
			matchlist = list(set(matchlist)) # remove duplicates if any
			# apply hilight
			color_hilight, color_reset = hilight.split(',', 1)
			for m in matchlist:
				s = s.replace(m, '%s%s%s' %(color_hilight, m, color_reset))
			return s
	# no need for findall() here
	elif regexp.search(s):
		return s

def grep_file(file, head, tail, after_context, before_context, *args):
	"""Return a list of lines that match 'regexp' in 'file', if no regexp returns all lines."""
	#debug(' '.join(map(str, (file, head, tail, after_context, before_context))))
	lines = linesList()
	file_object = open(file, 'r')
	if tail or after_context or before_context:
		# I need a full list of file's lines for these options, and only for these options, since
		# it makes the search take a bit more of time
		file_lines = file_object.readlines()
	else:
		file_lines = file_object
	if tail:
		# instead of searching in the whole file and later pick the last few lines, we
		# reverse the log, search until count reached and reverse it again, that way is a lot
		# faster
		file_lines.reverse()
	limit = head or tail

	# define these locally as it makes the loop run slightly faster
	append = lines.append
	count = lines.count_match
	separator = lines.append_separator
	check = check_string
	
	if before_context:
		before_context_range = range(1, before_context + 1)
		before_context_range.reverse()
	if after_context:
		after_context_range = range(1, after_context + 1)

	line_idx = 0
	for line in file_lines:
		line = check(line, *args)
		if line:
			if before_context:
				separator()
				for id in before_context_range:
					try:
						append(file_lines[line_idx - id])
					except IndexError:
						pass
			append(line)
			count()
			if after_context:
				for id in after_context_range:
					try:
						append(file_lines[line_idx + id])
					except IndexError:
						pass
				separator()
			if limit and lines.matches_count >= limit: break
		line_idx += 1

	if tail:
		lines.reverse()
	return lines

def grep_buffer(buffer, head, tail, after_context, before_context, *args):
	"""Return a list of lines that match 'regexp' in 'buffer', if no regexp returns all lines."""
	lines = linesList()
	# Using /grep in grep's buffer can lead to some funny effects
	# We should take measures if that's the case
	def make_get_line_funcion():
		"""Returns a function for get lines from the infolist, depending if the buffer is egrep's or
		not."""
		string_remove_color = weechat.string_remove_color
		infolist_string = weechat.infolist_string
		get_prefix = lambda infolist : string_remove_color(infolist_string(infolist, 'prefix'), '')
		get_message = lambda infolist : string_remove_color(infolist_string(infolist, 'message'), '')
		grep_buffer = weechat.buffer_search('python', SCRIPT_NAME)
		if buffer == grep_buffer:
			def function(infolist):
				prefix = get_prefix(infolist)
				message = get_message(infolist)
				if script_nick == prefix: # ignore our lines
					return None
				return '%s\t%s' %(prefix, message.replace(' ', '\t', 1))
		else:
			infolist_time = weechat.infolist_time
			def function(infolist):
				prefix = get_prefix(infolist)
				message = get_message(infolist)
				date = infolist_time(infolist, 'date')
				return '%s\t%s\t%s' %(date, prefix, message)
		return function
	get_line = make_get_line_funcion()

	infolist = weechat.infolist_get('buffer_lines', buffer, '')
	if tail:
		# like with grep_file() if we need the last few matching lines, we move the cursor to
		# the end and search backwards
		infolist_next = weechat.infolist_prev
		infolist_prev = weechat.infolist_next
	else:
		infolist_next = weechat.infolist_next
		infolist_prev = weechat.infolist_prev
	limit = head or tail

	# define these locally as it makes the loop run slightly faster
	append = lines.append
	count = lines.count_match
	separator = lines.append_separator
	check = check_string

	if before_context:
		before_context_range = range(before_context)
	if after_context:
		after_context_range = range(after_context)

	while infolist_next(infolist):
		line = get_line(infolist)
		if line is None: continue
		line = check(line, *args)
		if line:
			if before_context:
				separator()
				for id in before_context_range:
					infolist_prev(infolist)
				for id in before_context_range:
					append(get_line(infolist))
					infolist_next(infolist)
			append(line)
			count()
			if after_context:
				for id in after_context_range:
					infolist_next(infolist)
					append(get_line(infolist))
				for id in after_context_range:
					infolist_prev(infolist)
				separator()
			if limit and lines.matches_count >= limit:
				break
	weechat.infolist_free(infolist)

	if tail:
		lines.reverse()
	return lines

### this is our main grep function
hook_file_grep = None
def show_matching_lines():
	"""
	Greps buffers in search_in_buffers or files in search_in_files and updates egrep buffer with the
	result.
	"""
	global pattern, matchcase, number, count, exact, hilight
	global tail, head, after_context, before_context
	global search_in_files, search_in_buffers, matched_lines, home_dir
	global time_start
	matched_lines = linesDict()
	#debug('buffers:%s \nlogs:%s' %(search_in_buffers, search_in_files))
	time_start = now()
	regexp = make_regexp(pattern, matchcase)
	if search_in_buffers:
		for buffer in search_in_buffers:
			buffer_name = weechat.buffer_get_string(buffer, 'name')
			matched_lines[buffer_name] = grep_buffer(buffer, head, tail, after_context,
					before_context, regexp, hilight, exact)
	if search_in_files:
		len_home = len(home_dir)
		for log in search_in_files:
			log_name = log[len_home:]
			matched_lines[log_name] = grep_file(log, head, tail, after_context, before_context, regexp, hilight, exact)
	buffer_update()

grep_stdout = grep_stderr = ''
def grep_file_callback(data, command, rc, stdout, stderr):
	global hook_file_grep, grep_stderr,  grep_stdout
	global matched_lines
	#debug("%s @ stderr: '%s', stdout: '%s'" %(rc, stderr.strip('\n'), stdout.strip('\n')))
	if stdout:
		grep_stdout += stdout
	if stderr:
		grep_stderr += stderr
	if int(rc) >= 0:
		if grep_stderr:
			error(grep_stderr)
		elif grep_stdout:
			logs = grep_stdout.split('\n\n') # split between log files
			for log in logs:
				if not log: continue
				log = log.splitlines()
				log_name = log.pop(0)
				matched_lines[log_name] = log
			buffer_update()
		grep_stdout = grep_stderr = ''
		hook_file_grep = None
	return WEECHAT_RC_OK

def get_grep_file_status():
	global search_in_files, matched_lines, time_start
	elapsed = now() - time_start
	return 'There\'s a search in progress (running for %.4f seconds) interrupt it with /egrep stop'\
			%elapsed

### output buffer
def buffer_update():
	"""Updates our buffer with new lines."""
	global matched_lines, pattern, count, hilight
	time_grep = now()

	buffer = buffer_create()
	matched_lines.strip_separator() # remove first and last separators of each list
	len_total_lines = len(matched_lines)
	len_matched_lines = matched_lines.get_matches_count()
	max_lines = get_config_int('max_lines')
	if not count and len_total_lines > max_lines:
		weechat.buffer_clear(buffer)

	# color variables defined locally
	c_title = color_title
	c_reset = color_reset
	c_summary = color_summary
	c_date = color_date
	c_info = color_info
	c_hilight = color_hilight

	# formatting functions declared locally.
	def make_title(name, number):
		note = ''
		if len_total_lines > max_lines and not count:
			note = ' (last %s lines shown)' %max_lines
		return "Search in %s%s%s | %s matches%s | pattern \"%s%s%s\" | %.4f seconds (%.2f%%)" \
				%(c_title, name, c_reset, number, note, c_title, pattern, c_reset, time_total, time_grep_pct)

	def make_summary(name, lines, printed=0):
		note = ''
		if printed != len(lines):
			if printed:
				note = ' (last %s lines shown)' %printed
			else:
				note = ' (not shown)'
		return "%s matches \"%s%s%s\" in %s%s%s%s" \
				%(lines.matches_count, c_summary, pattern, c_info, c_summary, name, c_reset, note)

	global weechat_format
	weechat_format = True
	nick_dict = {} # nick caching
	def format_line(s):
		"""Returns the log line 's' ready for printing in buffer."""
		global weechat_format
		if s == linesList._sep:
			# ignore lines separator
			return s
		if weechat_format and s.count('\t') >= 2:
			date, nick, msg = s.split('\t', 2) # date, nick, message
		else:
			# looks like log isn't in weechat's format
			weechat_format = False # incoming lines won't be formatted if they have 2 tabs
			date, nick, msg = '', '', s.replace('\t', ' ')
		# we don't want colors if there's match highlighting
		if hilight:
			# fix color reset when there's highlighting from date to prefix
			if c_hilight in date and not c_reset in date:
				nick = c_hilight + nick
			return '%s\t%s %s' %(date, nick, msg)
		else:
			if nick in nick_dict:
				nick = nick_dict[nick]
			else:
				# cache nick
				s = color_nick(nick)
				nick_dict[nick] = s
				nick = s
			return '%s%s\t%s%s %s' %(c_date, date, nick, c_reset, msg)

	def color_nick(nick):
		"""Returns coloured nick, with coloured mode if any."""
		# XXX should check if nick has a prefix and subfix string?
		modes = '@!+%' # nick modes
		if not nick: return ''
		# nick mode
		if nick[0] in modes:
			mode, nick = nick[0], nick[1:]
			mode_color = weechat.config_string(weechat.config_get('weechat.color.nicklist_prefix%d' \
				%(modes.find(mode) + 1)))
			mode_color = weechat.color(mode_color)
		else:
			mode = ''
			mode_color = ''
		color_nicks_number = weechat.config_integer(weechat.config_get('weechat.look.color_nicks_number'))
		idx = (sum(map(ord, nick))%color_nicks_number) + 1
		color = weechat.config_string(weechat.config_get('weechat.color.chat_nick_color%02d' %idx))
		nick_color = weechat.color(color)
		return '%s%s%s%s' %(mode_color, mode, nick_color, nick)

	prnt = weechat.prnt
	prnt(buffer, '\n')
	print_info('Search for "%s" in %s.' %(pattern, matched_lines), buffer)
	# print last <max_lines> lines
	print_count = max_lines
	if matched_lines:
		print_lines = []
		for log, lines in matched_lines.iteritems():
			if lines:
				# matched lines
				if not count:
					len_lines = len(lines)
					if len_lines < print_count:
						print_lines = lines
						print_count -= len_lines
					elif print_count:
						print_lines = lines[-print_count:] # grab the last <print_count> lines
						print_count = 0
					else:
						print_lines = []
					# print lines
					for line in print_lines:
						prnt(buffer, format_line(line))

				# summary
				if count or get_config_boolean('show_summary'):
					summary = make_summary(log, lines, len(print_lines))
					print_info(summary, buffer)

				# separator
				if print_lines:
					prnt(buffer, '\n')
	else:
		print_info('No matches found.', buffer)

	# set title
	global time_start
	time_end = now()
	# total time
	time_total = time_end - time_start
	# percent of the total time used for grepping
	time_grep_pct = (time_grep - time_start)/time_total*100
	title = make_title(matched_lines, len_matched_lines)
	weechat.buffer_set(buffer, 'title', title)

	if get_config_boolean('go_to_buffer'):
		weechat.buffer_set(buffer, 'display', '1')

def print_info(s, buffer=None, display=False):
	"""Prints 's' in script's buffer as 'script_nick'. For displaying search summaries."""
	if buffer is None:
		buffer = buffer_create()
	weechat.prnt(buffer, '%s%s\t%s%s' \
			%(color_script_nick, script_nick, color_info, s))
	if display and get_config_boolean('go_to_buffer'):
		weechat.buffer_set(buffer, 'display', '1')

def buffer_create():
	"""Returns our buffer pointer, creates and cleans the buffer if needed."""
	buffer = weechat.buffer_search('python', SCRIPT_NAME)
	if not buffer:
		buffer = weechat.buffer_new(SCRIPT_NAME, 'buffer_input', '', 'buffer_close', '')
		weechat.buffer_set(buffer, 'time_for_each_line', '0')
		weechat.buffer_set(buffer, 'nicklist', '0')
		weechat.buffer_set(buffer, 'title', 'egrep output buffer')
		weechat.buffer_set(buffer, 'localvar_set_no_log', '1')
	else:
		if get_config_boolean('clear_buffer'):
			weechat.buffer_clear(buffer)
	return buffer

def buffer_input(data, buffer, input_data):
	"""Repeats last search with 'input_data' as regexp."""

	global search_in_buffers, search_in_files
	global pattern
	try:
		if pattern and (search_in_files or search_in_buffers):
			for pointer in search_in_buffers:
				if not weechat.infolist_get('buffer', pointer, ''):
					# I don't want any crashes
					del search_in_buffers[search_in_buffers.index(pointer)]
					error("Got invalid buffer pointer, did you close a buffer? Removing it.")
			try:
				cmd_grep_parsing(input_data)
			except Exception, e:
				error('Argument error, %s' %e, buffer=buffer)
				return WEECHAT_RC_OK
			try:
				show_matching_lines()
			except Exception, e:
				error(e)
	except NameError:
		error("There isn't any previous search to repeat.", buffer=buffer)
	return WEECHAT_RC_OK

def buffer_close(*args):
	return WEECHAT_RC_OK

### commands
def cmd_init():
	global home_dir, cache_dir
	global pattern, matchcase, number, count, exact, hilight
	global tail, head, after_context, before_context
	hilight = ''
	head = tail = after_context = before_context = False
	matchcase = count = exact = False
	number = None
	home_dir = get_home()
	cache_dir = {}

def cmd_grep_parsing(args):
	global pattern, matchcase, number, count, exact, hilight
	global tail, head, after_context, before_context
	global log_name, buffer_name, only_buffers, all
	opts, args = getopt.gnu_getopt(args.split(), 'cmHeahtin:bA:B:C:', ['count', 'matchcase', 'hilight',
		'exact', 'all', 'head', 'tail', 'number=', 'buffer', 'after-context=', 'before-context=',
		'context='])
	#debug(opts, 'opts: '); debug(args, 'args: ')
	if len(args) >= 2:
		if args[0] == 'log':
			del args[0]
			log_name = args.pop(0)
		elif args[0] == 'buffer':
			del args[0]
			buffer_name = args.pop(0)
	args = ' '.join(args) # join pattern for keep spaces
	if args:
		pattern = args
	elif not pattern:
		raise Exception, 'No pattern for grep the logs.'

	def positive_number(opt, val):
		try:
			number = int(val)
			if number < 0:
				raise ValueError
			return number
		except ValueError:
			if len(opt) == 1:
				opt = '-' + opt
			else:
				opt = '--' + opt
			raise Exception, "argument for %s must be a positive integer." %opt

	for opt, val in opts:
		opt = opt.strip('-')
		if opt in ('c', 'count'):
			count = not count
		elif opt in ('m', 'matchcase'):
			matchcase = not matchcase
		elif opt in ('H', 'hilight'):
			# hilight must be always a string!
			if hilight:
				hilight = ''
			else:
				hilight = '%s,%s' %(color_hilight, color_reset)
			# we pass the colors in the variable itself because check_string() must not use
			# weechat's module when applying the colors (this is for grep in a hooked process)
		elif opt in ('e', 'exact'):
			exact = not exact
		elif opt in ('a', 'all'):
			all = not all
		elif opt in ('h', 'head'):
			head = not head
			tail = False
		elif opt in ('t', 'tail'):
			tail = not tail
			head = False
		elif opt in ('b', 'buffer'):
			only_buffers = True
		elif opt in ('n', 'number'):
			number = positive_number(opt, val)
		elif opt in ('C', 'context'):
			n = positive_number(opt, val)
			after_context = n
			before_context = n
		elif opt in ('A', 'after-context'):
			after_context = positive_number(opt, val)
		elif opt in ('B', 'before-context'):
			before_context = positive_number(opt, val)
	# more checks
	if count:
		if hilight:
			hilight = '' # why hilight if we're just going to count?
		if exact:
			exact = False # see hilight
		if after_context:
			after_context = False
		if before_context:
			before_context = False
	elif exact:
		# pointless
		if after_context:
			after_context = False
		if before_context:
			before_context = False
	if head and tail: # it won't work
		raise Exception, "can't use --tail and --head simultaneously."
	if number is not None:
		if number == 0:
			# waste of cpu cycles
			raise Exception, "this humble script refuses to search and return zero lines."
		if head:
			head = number
		elif tail:
			tail = number
	else:
		if head:
			head = 10
		elif tail:
			tail = 10

def cmd_grep_stop(buffer, args):
	global hook_file_grep, pattern
	if hook_file_grep:
		if args == 'stop':
			weechat.unhook(hook_file_grep)
			hook_file_grep = None
			say('Search for \'%s\' stopped.' %pattern, buffer=buffer)
		else:
			error(get_grep_file_status(), buffer=buffer)
		raise Exception

def cmd_grep(data, buffer, args):
	"""Search in buffers and logs."""
	global pattern, matchcase, head, tail, number, count, exact, hilight

	if not args:
		weechat.command('', '/help %s' %SCRIPT_COMMAND)
		return WEECHAT_RC_OK

	cmd_init()
	global log_name, buffer_name, only_buffers, all
	log_name = buffer_name = ''
	only_buffers = all = False

	# parse
	try:
		cmd_grep_parsing(args)
	except Exception, e:
		error('Argument error, %s' %e)
		return WEECHAT_RC_OK

	# find logs
	log_file = search_buffer = None
	if log_name:
		log_file = get_file_by_pattern(log_name, all)
		if not log_file:
			error("Couldn't find any log for %s. Try /logs" %log_name)
			return WEECHAT_RC_OK
	elif all:
		search_buffer = get_all_buffers()
	elif buffer_name:
		search_buffer = get_buffer_by_name(buffer_name)
		if search_buffer is None:
			# there's no buffer, try in the logs
			log_file = get_file_by_name(buffer_name)
			if not log_file:
				error("Logs or buffer for '%s' not found." %buffer_name)
				return WEECHAT_RC_OK
		else:
			search_buffer = [search_buffer]
	else:
		search_buffer = [buffer]

	# make the log list
	global search_in_files, search_in_buffers
	search_in_files = []
	search_in_buffers = []
	if log_file:
		search_in_files = log_file
	elif not only_buffers:
		#debug(search_buffer)
		for pointer in search_buffer:
			log = get_file_by_buffer(pointer)
			#debug('buffer %s log %s' %(pointer, log))
			if log:
				search_in_files.append(log)
			else:
				search_in_buffers.append(pointer)
	else:
		search_in_buffers = search_buffer

	# grepping
	try:
		show_matching_lines()
	except Exception, e:
		error(e)
	return WEECHAT_RC_OK

def cmd_logs(data, buffer, args):
	"""List files in Weechat's log dir."""
	cmd_init()
	global home_dir
	from os import stat
	get_size = lambda x: stat(x).st_size
	sort_by_size = False
	filter = []

	try:
		opts, args = getopt.gnu_getopt(args.split(), 's', ['size'])
		if args:
			filter = args
		for opt, var in opts:
			opt = opt.strip('-')
			if opt in ('size', 's'):
				sort_by_size = True
	except Exception, e:
		error('Argument error, %s' %e)
		return WEECHAT_RC_OK

	# is there's a filter, filter_excludes should be False
	file_list = dir_list(home_dir, filter, filter_excludes=not filter)
	home_dir_len = len(home_dir)
	if sort_by_size:
		file_list.sort(key=get_size)
	else:
		file_list.sort()

	sizeDict = {0:'b', 1:'KiB', 2:'MiB', 3:'GiB', 4:'TiB'}
	def human_readable_size(size):
		power = 0
		while size > 1024:
			power += 1
			size /= 1024.0
		return '%.2f%s' %(size, sizeDict.get(power, ''))

	file_sizes = map(lambda x: human_readable_size(get_size(x)), file_list)
	if weechat.config_string(weechat.config_get('weechat.look.prefix_align')) == 'none' \
			and file_list:
		# lets do alignment for the file list
		L = file_sizes[:]
		L.sort(key=len)
		bigest = L[-1]
		column_len = len(bigest)
	else:
		column_len = ''
	buffer = buffer_create()
	file_list = zip(file_list, file_sizes)
	msg = 'Found %s logs.' %len(file_list)
	print_info(msg, buffer, display=True)
	for file, size in file_list:
		separator = column_len and ' '*(column_len - len(size))
		weechat.prnt(buffer, '%s%s\t%s' %(separator, size, file[home_dir_len:]))
	if file_list:
		print_info(msg, buffer)
	return WEECHAT_RC_OK

### completion
def completion_log_files(data, completion_item, buffer, completion):
	global home_dir
	for log in dir_list(home_dir):
		weechat.hook_completion_list_add(completion, log[len(home_dir):], 0, weechat.WEECHAT_LIST_POS_SORT)
	return WEECHAT_RC_OK

def completion_egrep_args(data, completion_item, buffer, completion):
	for arg in ('count', 'all', 'matchcase', 'hilight', 'exact', 'head', 'tail', 'number', 'buffer',
			'after-context', 'before-context', 'context'):
		weechat.hook_completion_list_add(completion, '--' + arg, 0, weechat.WEECHAT_LIST_POS_SORT)
	return WEECHAT_RC_OK

### Main
if __name__ == '__main__' and import_ok and \
		weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, \
		SCRIPT_DESC, '', ''):
	home_dir = get_home()

	weechat.hook_command(SCRIPT_COMMAND, cmd_grep.__doc__,
			"[log <file> | buffer <name>] [-a|--all] [-b|--buffer] [-c|--count] [-m|--matchcase] "
			"[-H|--hilight] [-e|--exact] [(-h|--head)|(-t|--tail) [-n|--number <n>]] "
			"[-A|--after-context <n>] [-B|--before-context <n>] [-C|--context <n> ] <expression>",
			# help
			"     log <file>: Search in one log that matches <file> in the logger path. Use '*' and '?' as jokers.\n"
			"  buffer <name>: Search in buffer <name>, if there's no buffer with <name> it will try to search for a log file.\n"
			"       -a --all: Search in all open buffers.\n"
			"                 If used with 'log <file>' search in all logs that matches <file>.\n"
			"    -b --buffer: Search only in buffers, not in file logs.\n"
			"     -c --count: Just count the number of matched lines instead of showing them.\n"
			" -m --matchcase: Don't do case insensible search.\n"
			"   -H --hilight: Colour exact matches in output buffer.\n"
			"     -e --exact: Print exact matches only.\n"
			"      -t --tail: Print the last 10 matching lines.\n"
			"      -h --head: Print the first 10 matching lines.\n"
			"-n --number <n>: Overrides default number of lines for --tail or --head.\n"
			"-A --after-context <n>: Shows <n> lines of trailing context after matching lines.\n"
			"-B --before-context <n>: Shows <n> lines of leading context before matching lines.\n"
			"-C --context <n>: Same as using both --after-context and --before-context simultaneously.\n"
			"   <expression>: Expression to search.\n\n"
			"egrep buffer:\n"
			"  Accepts most arguments of /egrep command, It'll repeat last search using the new "
			"arguments.\n"
			"  --all, --count, --tail, --head, --hilight, --matchcase and --exact switches are "
			"toggleable\n\n"
			"see http://docs.python.org/lib/re-syntax.html for documentation about python regular expressions.\n",
			# completion template
			"buffer %(buffers_names) %(egrep_arguments)|%*"
			"||log %(egrep_log_files) %(egrep_arguments)|%*"
			"||%(egrep_arguments)|%*",
			'cmd_grep' ,'')
	weechat.hook_command('logs', cmd_logs.__doc__, "[-s|--size] [<filter>]",
			"-s|--size: Sort logs by size.\n"
			" <filter>: Only show logs that match <filter>. Use '*' and '?' as jokers.", '--size', 'cmd_logs', '')

	weechat.hook_completion('egrep_log_files', "list of log files",
			'completion_log_files', '')
	weechat.hook_completion('egrep_arguments', "list of arguments",
			'completion_egrep_args', '')

	# settings
	for opt, val in settings.iteritems():
		if not weechat.config_is_set_plugin(opt):
			weechat.config_set_plugin(opt, val)

	# colors
	color_date = weechat.color('brown')
	color_script_nick = weechat.color('lightgreen')
	color_info = weechat.color('cyan')
	color_hilight = weechat.color('lightred')
	color_reset = weechat.color('reset')
	color_title = weechat.color('yellow')
	color_summary = weechat.color('lightcyan')

# vim:set shiftwidth=4 tabstop=4 noexpandtab textwidth=100:
