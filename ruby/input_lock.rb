# vim: set noet nosta sw=4 ts=4 :
#
# Copyright (c) 2011-2022, Mahlon E. Smith <mahlon@martini.nu>
# 
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, this
#       list of conditions and the following disclaimer.
# 
#     * Redistributions in binary form must reproduce the above copyright notice, this
#       list of conditions and the following disclaimer in the documentation and/or
#       other materials provided with the distribution.
# 
#     * Neither the name of the author, nor the names of contributors may be used to
#       endorse or promote products derived from this software without specific prior
#       written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


#
# History:
#
# 2022-11-27, Mahlon E. Smith <mahlon@martini.nu>
#   version 0.2: refactor, add optional automatic lock timer
# 2011-04-25, Mahlon E. Smith <mahlon@martini.nu>
#   version 0.1: initial release
#


#
# Description
# -----------
#
# Global toggle for disabling text input.  Commands are still allowed.
# This is a simple "don't look stupid" protector, if you're entering
# text and don't realize your focus is on the wrong window.  ;)
#
#
# Installation
# ------------
#
#   Load into Weechat like any other plugin, after putting it into
#   your ~/.weechat/ruby directory:
#
#        /ruby load input_lock.rb
#
#   It's strongly recommended to make some keybindings to easily toggle
#   the state of the lock.  Here's what I use:  ('i' for input!)
#
#        /key bind meta-i /set plugins.var.ruby.input_lock.enabled true
#        /key bind meta-I /set plugins.var.ruby.input_lock.enabled false
#
#   You can add notification of the current state by adding '[il]' to
#   your weechat.bar.input.items.
#
#
# Options
# -------
#
#   plugins.var.ruby.input_lock.enabled
#
#       The current state of the lock.
#
#       Default: "false"
#
#
#   plugins.var.ruby.input_lock.idleauto
#
#       Automatically enable the lock after a configured idle time,
#       in seconds.  "0" disables this feature.
#
#       Default: "0"
#


SIGNATURE = [
	'input_lock',
	'Mahlon E. Smith <mahlon@martini.nu>',
	'0.2',
	'BSD',
	'Reject all text input to avoid accidental public stupidity.',
	'',
	''
].freeze

# String -> bool matcher
TRUTH = /^(?:on|y(?:es)?|t(?:rue)?)$/

# plugin -> buffer combinations where the input lock
# is ignored.
WHITELIST = {
	'core'   => 'weechat',  # main weechat buffer
	'fset'   => 'fset',     # interactive settings
	'script' => 'scripts'   # script browser
}

# Default options
@opts = {
	enabled: false,
	idleauto: 0
}



### Weechat entry point.
###
def weechat_init
	Weechat::register *SIGNATURE
	self.init_config
	self.init_hooks
	Weechat.bar_item_new( 'il', 'il_bar_item', '' )
	return Weechat::WEECHAT_RC_OK
end


### Set configuration options.
###
def init_config
	@opts.each_pair do |opt, default|
		# Unset - set to defaults (first run)
		if Weechat.config_is_set_plugin( opt.to_s ).zero?
			Weechat.config_set_plugin( opt.to_s, default.to_s )

		# Previously set, use for current runtime.
		else
			@opts[opt] = self.get_config( opt )
		end
	end
end


### Fetch a value from options, casting to the appropriate ruby type.
###
def get_config( key )
	return case @opts[ key ]
		when String
			Weechat.config_get_plugin( key.to_s )
		when Integer
			Weechat.config_get_plugin( key.to_s ).to_i
		when TrueClass, FalseClass
			TRUTH.match( Weechat.config_get_plugin( key.to_s ) ).nil? ? false : true
	end
end


### Register various weechat hooks.
###
def init_hooks
	Weechat.hook_signal( 'input_text_changed', 'update_bar', '' )
	Weechat.hook_signal( 'buffer_switch', 'update_bar', '' )
	Weechat.hook_modifier( 'input_text_content', 'input_lock', '' )
	Weechat.hook_config( 'plugins.var.ruby.input_lock.*', 'config_changed', '' )
	self.reset_timer if @opts[ :idleauto ] > 0 && ! @opts[ :enabled ]
end


### Start the idle timer.
###
def reset_timer
	@opts[ :idle ] = 0
	Weechat.hook_timer( 1000, 0, 1, 'idle_timer', '' )
end


### Returns true if the current buffer is on the whitelist.
def check_whitelist( buffer )
	buf_plugin = Weechat.buffer_get_string( buffer, "localvar_plugin" );
	buf_name   = Weechat.buffer_get_string( buffer, "localvar_name" );
	WHITELIST.each_pair do |plugin, name|
		return true if buf_plugin == plugin && buf_name == name
	end

	return false
end


### Quick wrapper for sending info messages to the weechat main buffer.
###
def print_info( msg )
	Weechat.print '', "%sLOCK\t%s" % [
		Weechat.color( 'yellow' ),
		msg
	]
end



########################################################################
### W E E C H A T   H O O K S
########################################################################

### Validate values for config changes, and take appropriate action
### on any changes that immediately require it.
###
def config_changed( data, option, value )
	option = option.split( '.' ).last

	case option
		when 'enabled'
			@opts[ :enabled ] = TRUTH.match( value ).nil? ? false : true
			self.update_bar

			# reset the idle timer if configured
			if @opts[ :idleauto ] > 0 && ! @opts[ :enabled ]
				self.reset_timer
			end

		when 'idleauto'
			@opts[ :idleauto ] = value.to_i
			self.reset_timer if value.to_i > 0
	end

	return Weechat::WEECHAT_RC_OK
end


### Decide whether or not to allow entered text into the input buffer.
###
def input_lock( data, modifier, buffer, string )
	# reset the idle time and return the text immediately if disabled
	unless @opts[ :enabled ]
		@opts[ :idle ] = 0
		return string
	end

	# do nothing if in a whitelisted buffer
	return string if self.check_whitelist( buffer )

	# compat with the excellent Go script
	go_running = Weechat.info_get( 'go_running', '' );
	return string if go_running == '1'

	# allow commands to get through, everything else is squashed!
	return string.start_with?( '/' ) ? string : ''
end


### Refresh the lock state in the input bar.
###
def update_bar( data=nil, item=nil, window=nil )
	Weechat.bar_item_update( 'il' )
	return Weechat::WEECHAT_RC_OK
end


### The content of the 'il' bar item.
###
def il_bar_item( data, item, window )
	return @opts[ :enabled ] ?
		Weechat.color('red') + 'LOCK' + Weechat.color('') :
		''
end


### Automatically lock input after configured idle time has elapsed.
###
def idle_timer(data, remaining_calls)
    return Weechat::WEECHAT_RC_OK if @opts[ :enabled ]

	# Lock!
	if @opts[ :idle ] >= @opts[ :idleauto ]
		Weechat.config_set_plugin( 'enabled', 'true' )

	# Increment idle timer.
	else
		@opts[ :idle ] += 1
		Weechat.hook_timer( 1000, 0, 1, 'idle_timer', '' )
	end

    return Weechat::WEECHAT_RC_OK
end

