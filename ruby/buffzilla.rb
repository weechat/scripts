# buffzilla.rb
# Dave Williams <dave@dave.io>
# https://github.com/daveio/Weechat-scripts
# Licensed under the Apache License 2.0
# LicenseSHA256 b40930bbcf80744c86c46a12bc9da056641d722716c378f5659b9e555ef833e1
#
# head -n 5 buffzilla.rb | gpg --sign -ba
# -----BEGIN PGP SIGNATURE-----
#
# iQIbBAABCgAGBQJX6orKAAoJEHGMOmFhi24ljzwP+JHCCeEp2kdWOs9ixJDp+tZT
# qSBT1CMCeqmDpLmWGZirbKKaTnENokHhRiFHd5oaAGXfwTPPkfoK/fCPLB0GvYDY
# 7Fh9wvcp3kA5BS+piM8XuxKWi/dF0CXjDU2BwcZurWfu6ncbiPNxMn+SFu/L2R66
# IY6X9GEo/XF+rN4sapNyt0NK9OlyXHgpwqlJ8tfYoX1dfw/VUI3noAfIqh4D28Nv
# vYxfKSwy23BsogPqaWSEp2IrEM1ZqLYcJPBtO+yXx8VLNnmkGCxHyTvqXilEUxKQ
# yDdxAccBsmO1jHZceuT4YstgPwdIlfap0Gm6VNVxZZEUrXioVVMzdux/XKaxjH15
# d0nDkSAS0tVnpw+N2c4yFXFc+W+CXQQ2EZfRU1+/bCdueuMEmzvlrwXQjCI85d3K
# 8bXeHasJo/D8dPbF9Nbecoln/1GZYNtogUPSfZPKFBAWanSq4FK5p0YoL0sF/gxR
# W69kvZBJCDeNuJRcoL2YzJLYzYGjB4uj5qVp4Z/xS1J6xMajPBcE/BlofifinqoN
# apgvftUUBAPGCO88r6vyihsxkmV87LdIHmhvdsshFX0pgEpXjqiuPxTEi1lWXy2d
# wXyvq6MOpeycxd/zXVoxK9iGwwoumuEteyEiKkrWKniSv32QjLu7ufdaF01j7iCp
# MoqmKzbGK/oFbpDwI/4=
# =PgGj
# -----END PGP SIGNATURE-----
#
#  _      __  __  _ _ _
# | |__  _   _ / _|/ _|__(_) | | __ _
# | '_ \| | | | |_| ||_  / | | |/ _` |
# | |_) | |_| |  _|  _/ /| | | | (_| |
# |_.__/ \__,_|_| |_|/___|_|_|_|\__,_|
#
# A script for lazy people who use many quiet channels
#
# The purpose of buffzilla is simply to copy from all buffers into an
# additional buffer, for read only. To respond, switch to the real channel
# buffer in the usual way.
#
# The main benefit of this is that you can clear either this buffer or the real
# buffers without affecting scrollback in the other.
#
# Currently this script has no configuration, and is hard-coded to repeat
# everything from everywhere except anything tagged with 'irc_smart_filter'.
# If I get the time, I'll implement config to make it a bit more flexible.

DEBUG = false

if DEBUG
  require 'pp'
end

SIGNATURE = [
  'buffzilla',
  'Dave Williams',
  '0.1',
  'Apache 2.0',
  'Copy all activity to a single read-only buffer.',
  'weechat_unload',
  'UTF-8'
]

def weechat_init
  Weechat.register *SIGNATURE
  $bzbuf = Weechat.buffer_new("buffzilla", "", "", "", "")
  Weechat.hook_print("", "", "", 0, "zillify", "")
  Weechat.buffer_set($bzbuf, "title", "Buffzilla")
  return Weechat::WEECHAT_RC_OK
end

def weechat_unload
  Weechat.buffer_close($bzbuf)
end

def zillify(data, buffer, date, tags, displayed, highlight, prefix, message)
  data = {}
  %w(away type channel server).each do |meta|
    data[meta.to_sym] = Weechat.buffer_get_string(buffer, "localvar_#{meta}")
  end

  packet = {
    highlight:  ! highlight.to_i.zero?,
    type:       data[ :type ],
    channel:    data[ :channel ],
    away:       data[ :away ],
    server:     data[ :server ],
    date:       date,
    tags:       tags,
    message:    message
  }
  tags_list = packet[:tags].split(",")
  nick_tag = tags_list.find {|t| t.start_with? "nick_" }

  if DEBUG
    Weechat.print($bzbuf, "#{packet.pretty_inspect}")
  else
    unless tags_list.include? "irc_smart_filter"
      if nick_tag
        nick_cleaned = nick_tag.gsub(/^nick_/, "")
        Weechat.print($bzbuf,
          "#{nick_cleaned}@#{packet[:channel]} | #{packet[:message]}")
      else
        Weechat.print($bzbuf, "#{packet[:channel]} | #{packet[:message]}")
      end
    end
  end

  return Weechat::WEECHAT_RC_OK
end
