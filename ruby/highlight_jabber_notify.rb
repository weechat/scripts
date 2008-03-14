require 'rubygems'
require 'xmpp4r-simple'

"""
@authors    : Cyril Mougel <cyril.mougel@gmail.com>, Martin Catty <martin@noremember.org>
@goal       : This weechat's plugin send xmpp notification on your jabber
              account when you have been highlighted on a irc's channel or
              when you received private message.
              Just copy this script in your .weechat/ruby/autoload and set this
              3 variables in your plugins.rc :
                - ruby.highlight_jabber_notify.jid
                - ruby.highlight_jabber_notify.password
                - ruby.highlight_jabber_notify.recipient
@licence    : GPL v2.
@started_at : 2008-03-03
@updated_at : 2008-03-14
@url        : http://blog.noremember.org/public/highlight_jabber_notify.rb
@version    : 0.1.1
"""

# Plugin initialization
def weechat_init
  Weechat.register("highlight_jabber_notify", "0.1.1", "", "A plugin which send jabber's notifications on irc's highlights or private messages.")
  Weechat.add_message_handler('weechat_highlight', 'highlight')
  Weechat.add_message_handler('weechat_pv', 'pv')
  Weechat.set_plugin_config("port", "5222") if Weechat.get_plugin_config("port").empty?
  check_config ? Weechat::PLUGIN_RC_OK : Weechat::PLUGIN_RC_KO
end

# Print usage
def usage
  Weechat.print %q{
    You need the following informations in your config :
      - jid
      - password
      - recipient
  }
end

# Check that each required parameters have been found in the configuration file.
def check_config
  %w(jid password recipient).each do |param|
    (usage and return false) if Weechat.get_plugin_config(param).to_s.empty?
  end
  true
end

# Highlight callback
def highlight(server, args)
  JabberNotification.notify("You have been highlighted on server #{server}, with the following message : #{args}")
  return Weechat::PLUGIN_RC_OK
end

# Pv callback
def pv(server, args)
  JabberNotification.notify("You have received a private message on server #{server}, with the following message : #{args}")
  return Weechat::PLUGIN_RC_OK
end

# JabberNotification uses static variables to avoid repeated instanciation which
# are still the same.
class JabberNotification
  def self.authenticate
    Jabber::Simple.new(Weechat.get_plugin_config('jid'), Weechat.get_plugin_config('password'))
  end

  def self.jid
    begin
      @@im ||= self.authenticate
      @@im.reconnect unless @@im.connected?
    rescue Jabber::AuthenticationFailure => e
      Weechat.print "Failed to authenticate : #{e.to_s}."
      @@im = nil
    end
    @@im
  end

  def self.recipient
    @@recipient ||= Weechat.get_plugin_config('recipient')
  end

  def self.notify(message)
    unless self.jid.nil? # First call authenticate, next just return @@im
      begin
        @@im.deliver(self.recipient, message)
      rescue Exception => e
        Weechat.print "Failed to deliver message due to : #{e.to_s}."
        retry
      ensure
        self.close
      end
    end
  end

  # Close the Jabber Connection
  def self.close
    if not @@im.nil? and @@im.connected?
      # programm need to sleep, otherwise message may be lost.
      sleep 3
      @@im.disconnect
    end
  end
end
