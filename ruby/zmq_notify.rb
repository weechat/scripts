# vim: set noet nosta sw=4 ts=4 :
#
# Mahlon E. Smith <mahlon@martini.nu>
# http://www.martini.nu/
# (See below for LICENSE.)
#
# ZMQ Notify
# ----------
#
# Catch private messages and highlights, relaying them onward to a
# ZeroMQ publisher, for subscriber consumption.
#
# Writing a client to pull messages off the queue and send them to
# growl/libnotify/dzen/sms/email/your-tv/whatever-your-heart-desires
# is left as an exercise to the reader, but it should be as trivial as
# receiving the message and unwrapping YAML.  Fun!
#
#    ctx = ZMQ::Context.new
#    zmq = ctx.socket( ZMQ::SUB )
#    zmq.connect( "tcp://example.com:2428" )
#    zmq.setsockopt( ZMQ::SUBSCRIBE, '' )
#    
#    loop do
#        pp YAML.load( zmq.recv )
#    end
#
#
#
# Install instructions:
# ---------------------
#
#   This script requires the "zmq" ruby module, available
#   from rubygems, and of course, your Weechat to be built with
#   ruby.
#
#   Load into Weechat like any other plugin, after putting it into
#   your ~/.weechat/ruby directory:
#
#        /ruby load zmq_notify.rb
#
# Options:
# --------
#
#   plugins.var.ruby.zmq_notify.endpoint
#
#       The ZMQ connection endpoint.  The socket type is always PUB.
#       Default: tcp://*:2428
#
#   plugins.var.ruby.zmq_notify.ignore_tags
#
#       A comma separated list of message types to ignore
#       completely, regardless of away state.
#       Default: "irc_quit"
#
#   plugins.var.ruby.zmq_notify.enabled
#
#       A global on/off toggle.
#       Default: "off"
#
#   plugins.var.ruby.zmq_notify.only_when_away
#
#       Only relay messages to the ZMQ socket if you are set to /away.
#       Default: "on"
#
#
# ZMQ message payload
# -------------------
#
# Highlighted message:
#
#    {:type=>"channel",
#     :highlight=>true,
#     :message=>"Something said in #ruby-lang on my highlight list!",
#     :away=>false,
#     :channel=>"#ruby-lang",
#     :server=>"freenode",
#     :date=>"1294733587",
#     :tags=>["irc_privmsg", "notify_message", "log1"]}
#
# Private message:
#
#    {:type=>"private",
#     :highlight=>false,
#     :message=>"Here we go, yo.  So what's the scenario?",
#     :away=>false,
#     :channel=>"grangeromatic",
#     :server=>"bitlbee",
#     :date=>"1294733597",
#     :tags=>["irc_privmsg", "notify_private", "log1"]}
#


### Convenience 'truth' module for Weechat config strings, because:
###
###     self.enabled.true?
###
### reads a whole lot nicer than:
###
###     Weechat.config_string_to_boolean(Weechat.config_get_plugin('enabled')) == "1"
###
### I resist the temptation to monkeypatch all of String during my
### time with Weechat.  Heh.
###
module Truthy
	def true?
		return Weechat.config_string_to_boolean( self.to_s ).to_i.zero? ? false : true
	end
end


### The actual Weechat plugin.
###
class ZMQNotify
	include Weechat

	DEBUG = false

	SIGNATURE = [
		'zmq_notify',
		'Mahlon E. Smith',
		'0.1',
		'BSD',
		'Send private messages and highlights to a ZMQ socket.',
		'weechat_unload',
		'UTF-8'
	]

	DEFAULT_OPTIONS = {
		:endpoint       => 'tcp://*:2428',
		:ignore_tags    => 'irc_quit',
		:enabled        => 'off',
		:only_when_away => 'on'
	}


	### Prepare configuration and bind a ZMQ endpoint.
	###
	def initialize

		@zmq = @ctx = nil

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

		self.bind
		self.print_info "Initalized!"
	end

	# The ZMQ socket and context.
	#
	attr :zmq, true
	attr :ctx, true


	########################################################################
	### W E E C H A T   H O O K S
	########################################################################

	### Validate values for config changes, and take appropriate action
	### on any changes that immediately require it.
	###
	def config_changed( data, option, new_value )
		option = option.match( /\.(\w+)$/ )[1]
		bounce_connection = false
		new_value.extend( Truthy )

		case option

			# reset the connection if needed
			#
			when 'endpoint'
				instance_variable_set( "@#{option}".to_sym, new_value )
				bounce_connection = true

			# Disconnect/reconnect to endpoint
			#
			when 'enabled'
				self.enabled = new_value
				new_value.true? ? self.bind : self.unbind

			# ... just change the setting, no validation/action needed.
			else
				instance_variable_set( "@#{option}".to_sym, new_value )
		end

		# Refresh the endpoint connection.
		#
		if bounce_connection
			self.unbind
			self.bind
		end

		return WEECHAT_RC_OK
	end


	### Process all incoming messages, filtering out anything we're not
	### interested in seeing.
	###
	def notify_msg( data, buffer, date, tags, visible, highlight, prefix, message )

		return WEECHAT_RC_OK unless self.enabled.true?

		# Grab the channel metadata.
		data = {}
		%w[ away type channel server ].each do |meta|
			data[ meta.to_sym ] = Weechat.buffer_get_string( buffer, "localvar_#{meta}" );
		end
		data[ :away ] = data[ :away ].empty? ? false : true

		# Are we currently marked as away?
		return WEECHAT_RC_OK if self.only_when_away.true? && ! data[ :away ]

		# Only bother with the message if it is a highlight, or a private message.
		return WEECHAT_RC_OK if highlight.to_i.zero? && data[ :type ] != 'private'

		# Are we specifically ignoring this message tag type?
		#
		ignored = self.ignore_tags.split( ',' )
		tags    = tags.split( ',' )
		return WEECHAT_RC_OK unless ( ignored & tags ).empty? 

		notify = {
			:highlight => ! highlight.to_i.zero?,
			:type      => data[ :type ],
			:channel   => data[ :channel ],
			:away      => data[ :away ],
			:server    => data[ :server ],
			:date      => date,
			:tags      => tags,
			:message   => message
		}

		# Ship it off.
		#
		self.print_info "Message notification: %p" % [ notify ] if DEBUG
		self.zmq.send( notify.to_yaml )

		return WEECHAT_RC_OK

	rescue => err
		self.disable "%s, %s" % [ err.class.name, err.message ]
		return WEECHAT_RC_OK
	end


	########################################################################
	### I N S T A N C E   M E T H O D S
	########################################################################

	### Instantiate a ZMQ endpoint.
	###
	def bind
		return unless self.enabled.true?

		self.print_info "Setting up endpoint at %s" % [ self.endpoint ]

		self.ctx = ZMQ::Context.new if self.ctx.nil?
		self.zmq = self.ctx.socket( ZMQ::PUB )
		self.zmq.bind( self.endpoint )

	rescue => err
		self.print_info "Unable to create endpoint: %s, %s" % [ err.class.name, err.message ]
		self.zmq = nil
	end


	### Tear down the ZMQ endpoint.
	###
	def unbind
		return if self.zmq.nil?
		self.zmq.close
	end


	### Disable the plugin on repeated error.
	### TODO:  Set a timer to attempt a re-connect?
	###
	def disable( reason )
		self.print_info "Disabling plugin due to error: %s" % [ reason ]
		Weechat.config_set_plugin( 'enabled', 'off' )
	end



	#########
	protected
	#########

	### Quick wrapper for sending info messages to the weechat main buffer.
	###
	def print_info( msg )
		Weechat.print '', "%sZMQ\t%s" % [
			Weechat.color('yellow'),
			msg
		]
	end
end



### Weechat entry point.
###
def weechat_init
	require 'rubygems'
	require 'zmq'
	require 'yaml'

	Weechat::register *ZMQNotify::SIGNATURE
	$zmq = ZMQNotify.new
	Weechat.hook_print( '', '', '', 1, 'notify_msg', '' )
	Weechat.hook_config( 'plugins.var.ruby.zmq_notify.*', 'config_changed', '' )

	return Weechat::WEECHAT_RC_OK

rescue LoadError => err
	Weechat.print '', "zmq_notify: %s, %s\n$LOAD_PATH: %p" % [
		err.class.name,
		err.message,
		$LOAD_PATH
	]
	Weechat.print '', 'zmq_notify: Unable to initialize due to missing dependencies.'
	return Weechat::WEECHAT_RC_ERROR
end


### Hook for manually unloading this script.
###
def weechat_unload
	$zmq.unbind
	return Weechat::WEECHAT_RC_OK
end


### Allow Weechat namespace callbacks to forward to the ZMQNotify object.
###
require 'forwardable'
extend Forwardable
def_delegators :$zmq, :notify_msg, :config_changed


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

