# Author: Justin Anderson
# Email: jandersonis@gmail.com
# Homepage: https://github.com/tinifni/gntp-notify
# Version: 1.1
# License: GPL3
# Depends on ruby_gntp (https://github.com/snaka/ruby_gntp)

require 'rubygems'
require 'ruby_gntp'

def weechat_init
  Weechat.register("gntp_notify",
                   "Justin Anderson",
                   "1.1",
                   "GPL3",
                   "GNTP Notify: Growl notifications using ruby_gntp.",
                   "",
                   "")

  hook_notifications

  @growl = GNTP.new("Weechat")
  @growl.register({
    :notifications => [{:name    => "Private",
                        :enabled => true},
                       {:name    => "Highlight",
                        :enabled => true}]
  })

  return Weechat::WEECHAT_RC_OK
end

def hook_notifications
  Weechat.hook_signal("weechat_pv", "show_private", "")
  Weechat.hook_signal("weechat_highlight", "show_highlight", "")
end

def unhook_notifications(data, signal, message)
  Weechat.unhook(show_private)
  Weechat.unhook(show_highlight)
end

def show_private(data, signal, message)
  message[0..1] == '--' ? sticky = false : sticky = true
  show_notification("Private", "Weechat Private Message",  message, sticky)
  return Weechat::WEECHAT_RC_OK
end

def show_highlight(data, signal, message)
  message[0..1] == '--' ? sticky = false : sticky = true
  show_notification("Highlight", "Weechat",  message, sticky)
  return Weechat::WEECHAT_RC_OK
end

def show_notification(name, title, message, sticky = true)
  @growl.notify({
    :name   => name,
    :title  => title,
    :text   => message,
    :icon   => "https://github.com/tinifni/gntp-notify/raw/master/weechat.png",
    :sticky => sticky
  })
end
