# vim: set noet nosta sw=4 ts=4 :
#
# Mahlon E. Smith <mahlon@martini.nu>
# http://www.martini.nu/
# (See below for LICENSE.)
#
# AMQP Notify
# -----------
#
# Catch private messages and highlights, relaying them onward to a
# RabbitMQ AMQP exchange for client consumption.
#
#	http://www.rabbitmq.com/
#
# This may seem like a bit of overengineering, but when you have all
# your chat/twitter/irc protocols going through Weechat on a remote
# shell as I do, along with numerous client machines at different
# locations, I found this to be a reliable way to make sure I /notice/
# when someone is trying to get my attention, and I'm not watching the
# terminal at that exact moment.  Works great with bitlbee!
#
# Writing a client to pull messages off the queue and send them to
# growl/libnotify/dzen/sms/email/your-tv/whatever-your-heart-desires
# is left as an exercise to the reader, but it should be as trivial as
# receiving the message and unwrapping YAML.  Fun!
#
#
# Install instructions:
# ---------------------
#
#   This script requires the "Bunny" ruby module, available
#   from rubygems, and of course, your Weechat to be built with
#   ruby.
#
#   Load into Weechat like any other plugin, after putting it into
#   your ~/.weechat/ruby directory:
#
#        /ruby load amqp_notify.rb
#
# Options:
# --------
#
#   plugins.var.ruby.amqp_notify.rabbitmq_host
#
#       The hostname of the rabbitmq server/broker.
#       Default: Empty string
#
#   plugins.var.ruby.amqp_notify.user
#
#       Username credential for rabbitmq.
#       Default: Empty string
#
#   plugins.var.ruby.amqp_notify.pass
#
#       Password credential for rabbitmq.
#       Default: Empty string
#
#   plugins.var.ruby.amqp_notify.vhost
#
#       The virtual host within rabbitmq, if any.
#       Default: "/"
#
#   plugins.var.ruby.amqp_notify.exchange_type
#
#       What kind of exchange?  direct|fanout|topic
#       Default: "fanout"
#
#       The fanout type allows many different clients
#       to simultanously receive notifications.
#
#   plugins.var.ruby.amqp_notify.exchange_name
#
#       The name of the Weechat notification exchange.
#       Default: "chat-notify"
#
#   plugins.var.ruby.amqp_notify.exchange_key
#
#       A routing key, for 'topic' and 'direct' exchange types.
#       Default: Empty string
#
#   plugins.var.ruby.amqp_notify.ignore_tags
#
#       A comma separated list of message types to ignore
#       completely, regardless of away state.
#       Default: "irc_quit"
#
#   plugins.var.ruby.amqp_notify.enabled
#
#       A global on/off toggle.
#       Default: "off"
#
#   plugins.var.ruby.amqp_notify.only_when_away
#
#       Only relay messages to AMQP if you are set to /away.
#       Default: "on"
#
#
# AMQP Payload
# ------------
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
class AMQPNotify
	include Weechat

	DEBUG = false

	SIGNATURE = [
		'amqp_notify',
		'Mahlon E. Smith',
		'0.1',
		'BSD',
		'Send private messages and highlights to an AMQP exchange.',
		'weechat_unload',
		'UTF-8'
	]

	DEFAULT_OPTIONS = {
		:rabbitmq_host  => 'localhost',
		:user           => nil,
		:pass           => nil,
		:vhost          => '/',
		:exchange_type  => 'fanout',
		:exchange_name  => 'chat-notify',
		:exchange_key   => nil,
		:ignore_tags    => 'irc_quit',
		:enabled        => 'off',
		:only_when_away => 'on'
	}


	### Prepare configuration and set up initial communication with the AMQP exchange.
	###
	def initialize

		@amqp = @exchange = nil

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

	# The RabbitMQ broker and publishing exchange.
	#
	attr :amqp,     true
	attr :exchange, true


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
			when 'rabbitmq_host', 'user', 'pass', 'exchange_key', 'exchange_name'
				instance_variable_set( "@#{option}".to_sym, new_value )
				bounce_connection = true

			# revert the setting change if the type is invalid, bounce
			# connection if it checks out.
			#
			when 'exchange_type'
				if %w[ direct topic fanout ].include?( new_value )
					self.exchange_type = new_value
					bounce_connection = true
				else
					self.print_info "'%s' is not a valid exchange type." % [ new_value ]
					Weechat.config_set_plugin( option, self.exchange_type )
				end

			# revert the setting change if the vhost doesn't begin with
			# a '/'.  Otherwise, bounce the connection.
			#
			when 'vhost'
				if new_value =~ /^\//
					self.vhost = new_value
					bounce_connection = true
				else
					self.print_info "vhosts must begin with a slash (/)."
					Weechat.config_set_plugin( option, self.vhost )
				end

			# Disconnect/reconnect to AMQP
			#
			when 'enabled'
				self.enabled = new_value
				new_value.true? ? self.bind : self.unbind

			# ... just change the setting, no validation/action needed.
			else
				instance_variable_set( "@#{option}".to_sym, new_value )
		end

		# Cycle the connection with RabbitMQ with the updated settings.
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
		self.exchange.publish( notify.to_yaml, :key => self.exchange_key )

		return WEECHAT_RC_OK

	rescue => err
		self.disable "%s, %s" % [ err.class.name, err.message ]
		return WEECHAT_RC_OK
	end


	########################################################################
	### I N S T A N C E   M E T H O D S
	########################################################################

	### Connect to the RabbitMQ broker.
	###
	def bind
		return unless self.enabled.true?

		self.print_info "Attempting connection to %s" % [ self.rabbitmq_host ]
		self.amqp = Bunny.new(
			:host  => self.rabbitmq_host,
			:user  => self.user,
			:pass  => self.pass,
			:vhost => self.vhost
		)
		self.amqp.start

		self.exchange = self.amqp.exchange(
			self.exchange_name,
			:type => self.exchange_type
		)

	rescue => err
		self.print_info "Unable to connect to AMQP: %s, %s" % [ err.class.name, err.message ]
		self.amqp = nil
	end


	### Disconnect from the RabbitMQ broker.
	###
	def unbind
		return if self.amqp.nil?
		self.amqp.stop
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
		Weechat.print '', "%sAMQP\t%s" % [
			Weechat.color('yellow'),
			msg
		]
	end
end



### Weechat entry point.
###
def weechat_init
	require 'rubygems'
	require 'bunny'
	require 'yaml'

	Weechat::register *AMQPNotify::SIGNATURE
	$amqp = AMQPNotify.new
	Weechat.hook_print( '', '', '', 1, 'notify_msg', '' )
	Weechat.hook_config( 'plugins.var.ruby.amqp_notify.*', 'config_changed', '' )

	return Weechat::WEECHAT_RC_OK

rescue LoadError => err
	Weechat.print '', "amqp_notify: %s, %s\n$LOAD_PATH: %p" % [
		err.class.name,
		err.message,
		$LOAD_PATH
	]
	Weechat.print '', 'amqp_notify: Unable to initialize due to missing dependencies.'
	return Weechat::WEECHAT_RC_ERROR
end


### Hook for manually unloading this script.
###
def weechat_unload
	$amqp.unbind
	return Weechat::WEECHAT_RC_OK
end


### Allow Weechat namespace callbacks to forward to the AMQPNotify object.
###
require 'forwardable'
extend Forwardable
def_delegators :$amqp, :notify_msg, :config_changed


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

