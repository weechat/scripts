# vim: set noet nosta sw=4 ts=4 :
#
# Mahlon E. Smith <mahlon@martini.nu>
# http://www.martini.nu/
# (See below for LICENSE.)
#
# Input Lock
# ----------
#
# Global toggle for disabling text input.  Commands are still allowed.
# This is a simple "don't look stupid" protector, if you're entering
# text and don't realize your focus is on the wrong window.  ;)
#
#
# Install instructions:
# ---------------------
#
#   Load into Weechat like any other plugin, after putting it into
#   your ~/.weechat/ruby directory:
#
#        /ruby load input_lock.rb
#
#   It's strongly recommended to make some keybindings to easily toggle
#   the state of the lock.  Here's what I use:  ('i' for input!)
#
#        /key bind meta-i /set plugins.var.ruby.input_lock.enabled off
#        /key bind meta-I /set plugins.var.ruby.input_lock.enabled on
#
#   You can add notification of the current state by adding '[il]' to
#   your weechat.bar.input.items.
#
#
# Options:
# --------
#
#   plugins.var.ruby.input_lock.enable
#
#       The state of the lock.
#       Default: "off"
#


### Convenience 'truth' module for Weechat config strings.
###
module Truthy
	def true?
		return Weechat.config_string_to_boolean( self.to_s ).to_i.zero? ? false : true
	end
end


### The Weechat plugin.
###
class InputLock
	include Weechat

	DEBUG = false

	SIGNATURE = [
		'input_lock',
		'Mahlon E. Smith',
		'0.1',
		'BSD',
		'Reject all text input, to avoid accidental public stupidity.',
		'',
		''
	]

	DEFAULT_OPTIONS = {
		:enabled => 'off'
	}


	### Prepare configuration.
	###
	def initialize
		DEFAULT_OPTIONS.each_pair do |option, value|

			# install default options if needed.
			#
			if Weechat.config_is_set_plugin( option.to_s ).zero?
				self.print_info "Setting value '%s' to %p" % [ option, value ] if DEBUG
				Weechat.config_set_plugin( option.to_s, value.to_s )
			end

			# read in existing config values, attaching
			# them to instance variables.
			#
			val = Weechat.config_get_plugin( option.to_s )
			val.extend( Truthy )
			instance_variable_set( "@#{option}".to_sym, val )
			self.class.send( :attr, option.to_sym, true )
		end

		Weechat.bar_item_new( 'il', 'il_bar_item', '' )
	end


	########################################################################
	### W E E C H A T   H O O K S
	########################################################################

	### Validate values for config changes, and take appropriate action
	### on any changes that immediately require it.
	###
	### (This is overcomplex for the single 'enable toggle' case, but
	### leaving the logic in place on the likely chance there will be
	### added future options.)
	###
	def config_changed( data, option, new_value )
		option = option.match( /\.(\w+)$/ )[1]
		new_value.extend( Truthy )

		case option
			when 'enabled'
				self.enabled = new_value
				self.update_bar
				self.print_info "Setting enabled to %p" % [ new_value ] if DEBUG
		end

		return WEECHAT_RC_OK
	end


	### Decide whether or not to allow entered text into the input buffer.
	###
	def input_lock( data, modifier, buffer, string )
		# do nothing if not enabled
		return string unless self.enabled.true?

		# text in the weechat buffer is always allowed
		buf_plugin = Weechat.buffer_get_string( buffer, "localvar_plugin" );
		buf_name   = Weechat.buffer_get_string( buffer, "localvar_name" );
		return string if buf_plugin == 'core' && buf_name == 'weechat'

		go_running = Weechat.info_get( "go_running", "" );
		return string if go_running == '1'

		# allow commands to get through, everything else is squashed!
		return string.index('/').nil? ? '' : string
	end


	### Refresh the lock state in the input bar.
	###
	def update_bar( data=nil, item=nil, window=nil )
		Weechat.bar_item_update( 'il' )
		return WEECHAT_RC_OK
	end

	### The content of the 'il' bar item.
	###
	def il_bar_item( data, item, window )
		return self.enabled.true? ?
			Weechat.color('red') + 'LOCK' + Weechat.color('') :
			''
	end


	#########
	protected
	#########

	### Quick wrapper for sending info messages to the weechat main buffer.
	###
	def print_info( msg )
		Weechat.print '', "%sLOCK\t%s" % [
			Weechat.color('yellow'),
			msg
		]
	end
end



### Weechat entry point.
###
def weechat_init
	Weechat::register *InputLock::SIGNATURE
	$lock = InputLock.new
	Weechat.hook_signal( 'input_text_changed', 'update_bar', '' )
	Weechat.hook_signal( 'buffer_switch', 'update_bar', '' )
	Weechat.hook_modifier( 'input_text_content', 'input_lock', '' )
	Weechat.hook_config( 'plugins.var.ruby.input_lock.*', 'config_changed', '' )
	return Weechat::WEECHAT_RC_OK
end


### Allow Weechat namespace callbacks to forward to the InputLock object.
###
require 'forwardable'
extend Forwardable
def_delegators :$lock, :config_changed, :input_lock, :update_bar, :il_bar_item


__END__
__LICENSE__

Copyright (c) 2011, Mahlon E. Smith <mahlon@martini.nu>

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this
      list of conditions and the following disclaimer.

    * Redistributions in binary form must reproduce the above copyright notice, this
      list of conditions and the following disclaimer in the documentation and/or
      other materials provided with the distribution.

    * Neither the name of the author, nor the names of contributors may be used to
      endorse or promote products derived from this software without specific prior
      written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

