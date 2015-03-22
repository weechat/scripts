# vim: set noet nosta sw=4 ts=4 :
#
# Colorizer
# Michael B. Hix <m@hix.io>
# http://code.hix.io/projects/colorizer
#
# Color certain parts of text in certain buffers based on rules.
#

#
# Options:
#
#	plugins.var.ruby.colorizer.buffer_regex
#		Buffers with names matching this regex are colorized. All buffers are
#		colorized if this option is empty.
#
#	plugins.var.ruby.colorizer.rule.count
#		This is the maximum number of rules to load.
#
#   plugins.var.ruby.colorizer.rule.X
#		X is zero or a positive integer. Rules are strings consisting of a regular
#		expression followed immediately by a slash and a Weechat color name. The
#		regular expressions are case-insensitive.
#
#		Text matching the regular expression is colored with the given color. The
#		last match "wins" and overlapping matches are not detected.
#
#		For example: "strelka|mongrel2/lightgreen"
#

#
# Changelog:
#
# 0.1: Initial release.
#

SCRIPT_NAME    = 'colorizer'
SCRIPT_AUTHOR  = 'Michael B. Hix'
SCRIPT_DESC    = 'Colorize text in buffers based on rules.'
SCRIPT_VERSION = '0.1'
SCRIPT_LICENSE = 'BSD'

# A default coloring rule.
#
DEFAULT_RULE = {
	:value => '',
	:description => 'A colorizing rule of the form: <regular_expression>/<weechat_color_name> Empty rules are ignored.',
}.freeze

# Configuration defaults are supplied and set for the user if they're not already set.
#
DEFAULTS = {
	'rule.0' => DEFAULT_RULE,
	'rule.1' => DEFAULT_RULE,
	'rule.2' => DEFAULT_RULE,
	'rule.3' => DEFAULT_RULE,
	'rule.4' => DEFAULT_RULE,
	'rule.count' => {
		:value => 10,
		:description => 'The maximum number of rules to look for in your config.',
	},
	'buffer_regex' => {
		:value => '',
		:description => 'Only colorize text in buffers with names that match this regex. Leaving this empty matches all buffer names.',
	},
}.freeze

########################################################################
### I N I T
########################################################################

def weechat_init
	Weechat.register SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, '', ''

	Weechat.hook_modifier( 'weechat_print', 'colorize_cb', '' )

	DEFAULTS.each_pair do |option, opts|
		value = opts[:value]
		description = opts[:description]

		cur_value = Weechat.config_get_plugin( option )

		if cur_value.nil? || cur_value.empty?
			Weechat.config_set_plugin( option, value.to_s )
		end

		Weechat.config_set_desc_plugin( option, description )
	end

	parse_config

	Weechat.hook_config( "plugins.var.ruby.#{SCRIPT_NAME}.*", 'config_cb', '' )

	return Weechat::WEECHAT_RC_OK
end

################################################################################
### U T I L I T I E S
################################################################################

# Provide a way to print legible stack traces.
#
def pp_error( e, message = '' )
	return unless e.is_a? Exception
	unless message.nil? or message.empty?
		Weechat.print( '', '%s%s' % [Weechat.prefix('error'), message] )
	end
	Weechat.print( '', '%s%s: %s' % [Weechat.prefix( 'error' ), SCRIPT_NAME, e.to_s] )
	e.backtrace.each do |line|
		Weechat.print( '', '%s%s' % [Weechat.prefix( 'error' ), line] )
	end
end

# Re-build rules and any regular expressions when the config changes.
#
def parse_config
	rules = {}
	count = Weechat::config_get_plugin( 'rule.count' ).to_i ||
		DEFAULTS['rule.count']

	count.times do |i|
		key = "rule.#{i}"
		next unless Weechat::config_is_set_plugin( key )

		conf = Weechat::config_get_plugin( key )
		regex,color,_ = conf.split( /(?<!\\)\//, 3 )

		next if regex.nil? or regex.empty? or color.nil? or color.empty?

		begin
			rules[/(#{regex})/i] = color
		rescue Exception => e
			pp_error( e, 'There was a problem with rule %d:' % [i] )
		end
	end

	@rules = rules

	begin
		@buffer_regex = /#{Weechat::config_get_plugin( 'buffer_regex' )}/i
	rescue Exception => e
		pp_error( e, 'There was a problem with buffer_regex:' )
	end
end

################################################################################
### C A L L B A C K S
################################################################################

# Handle configuration changes.
#
def config_cb( data, option, value )
	parse_config
	return Weechat::WEECHAT_RC_OK
end

# Handle message printing.
#
def colorize_cb( data, modifier, modifier_data, message )
	_,buffer,_ = modifier_data.split( ';' )
	return message unless @buffer_regex =~ buffer

	reset = Weechat.color( 'reset' )
	@rules.each do |reg, color_str|
		color = Weechat.color( color_str )
		message.gsub!( reg, '%s\1%s' % [color,reset] )
	end

	return message
end

__END__
__LICENSE__

Copyright (c) 2014 Michael B. Hix
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
