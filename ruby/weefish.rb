##
# weefish.rb
#
# Copyright (c) 2010 by Tobias Petersen <tp@unreal.dk>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
# 
# FiSH encryption / decryption for Weechat
# based on blowfish, it is compatible with other
# FiSH scripts created for mIRC, irssi and XChat
#
# Thanks to someone without a name, for creating the FiSH script in ruby
# No DH1080 key exchange, only manual key, sorry!
#
# Usage:
#   Set key for a given nick/channel, or the active nick/channel:
#     /setkey [nick/channel] <secure key>
#   Delete key for a given nick/channel, or the active nick/channel:
#     /delkey [nick/channel] <secure key>
#
# History:
#   2012-02-08 bazerka <bazerka@irssi.org>
#     version 0.4: fix in_privmsg to work with user targeted privmsg.
#                  bypass decrypting in_privmsg when no key is found.
#   2011-03-08 tp <tp@unreal.dk>
#     version 0.3: fixed crypt/blowfish bug for ruby >= 1.9
#   2010-09-06, tp <tp@unreal.dk>
#     version 0.2: fixed some message printing
#   2010-09-05, tp <tp@unreal.dk>
#     version 0.1: initial release

require "crypt/blowfish"

def message buffer, message
  Weechat.print buffer, "#{Weechat.prefix('error')}#{Weechat.color('bold')}weefish:#{Weechat.color('-bold')} #{message}"
end

def weechat_init
  Weechat.register "weefish", "Tobias Petersen", "0.4", "GPL3", "FiSH encryption/decryption", "", ""
  
  Weechat.hook_modifier "irc_in_privmsg", "in_privmsg", ""
  Weechat.hook_modifier "irc_out_privmsg", "out_privmsg", ""
  
  Weechat.hook_command "setkey", "Set the encryption key for the active nick/channel", "[nick/channel] <secure key>", "", "", "setkey", ""
  Weechat.hook_command "delkey", "Delete the encryption key for the active nick/channel", "[nick/channel] <secure key>", "", "", "delkey", ""
  
  return Weechat::WEECHAT_RC_OK
end

if RUBY_VERSION.to_f >= 1.9
  module ::Crypt
    class Blowfish
      def setup_blowfish
        @sBoxes = Array.new(4) { |i| INITIALSBOXES[i].clone }
        @pArray = INITIALPARRAY.clone
        keypos = 0
        0.upto(17) { |i|
          data = 0
          4.times {
            data = ((data << 8) | @key[keypos].ord) % ULONG
            keypos = (keypos.next) % @key.length
          }
          @pArray[i] = (@pArray[i] ^ data) % ULONG
        }
        l = 0
        r = 0
        0.step(17, 2) { |i|
          l, r = encrypt_pair(l, r)
          @pArray[i]   = l
          @pArray[i+1] = r
        }
        0.upto(3) { |i|
          0.step(255, 2) { |j|
            l, r = encrypt_pair(l, r)
            @sBoxes[i][j]   = l
            @sBoxes[i][j+1] = r
          }
        }
      end
    end
  end
end

def setkey data, buffer, key
  network, channel = Weechat.buffer_get_string(buffer, "name").split ".", 2
  
  unless key.empty?
    if key.scan(" ").length == 0
      if network == "server"
        message buffer, "No active nick/channel. Usage: /setkey <nick/channel> <secure key>"
      else
        message buffer, "Key for #{channel} (#{network}) successfully set!"
        Weechat.config_set_plugin "key.#{network}.#{channel}", key
      end
    else
      network = channel if network == "server"
      channel, key = key.split " ", 2
      
      message buffer, "Key for #{channel} (#{network}) successfully set!"
      Weechat.config_set_plugin "key.#{network}.#{channel}", key
    end
  else
    message buffer, "No parameters. Usage: /setkey [nick/channel] <secure key>"
  end
end

def delkey data, buffer, string
  network, channel = Weechat.buffer_get_string(buffer, "name").split ".", 2
  
  if string.empty?
    if network == "server"
      message buffer, "No active nick/channel. Usage: /delkey <nick/channel>"
    else
      Weechat.config_unset_plugin "key.#{network}.#{channel}"
      message buffer, "Key for #{channel} (#{network}) successfully deleted!"
    end
  else
    network = channel if network == "server"
    Weechat.config_unset_plugin "key.#{network}.#{string.split.first}"
    message buffer, "Key for #{string.split.first} (#{network}) successfully deleted!"
  end
end

def in_privmsg data, signal, server, args
  if args =~ /^(:(.*?)!.*? PRIVMSG (.*?) :)(\+OK|mcps) (.*)$/
	# If the PRIVMSG target ($3) is our current nick, we need the source nick ($2) to select the key
    # config variable. Otherwise, assume it's a channel and use that to select the key instead.
    selector = $3 == Weechat.info_get("irc_nick", server) ? $2 : $3
    key = Weechat.config_string Weechat.config_get("plugins.var.ruby.weefish.key.#{server}.#{selector}")
    
    # If we couldn't find a key, don't attempt to decrypt the message as Crypt::Blowfish will raise an
    # invalid key length error on initialisation.
	unless key.empty?
      fish = IRC::FiSH.new key
      if decrypted = fish.decrypt($5)
        return $1+decrypted
      end
    end
  end
  return args
end

def out_privmsg data, signal, server, args
  if args =~ /^(PRIVMSG (.*?) :)(.*)$/
    key = Weechat.config_string Weechat.config_get("plugins.var.ruby.weefish.key.#{server}.#{$2}")
    
    unless key.empty?
      fish = IRC::FiSH.new key
      return "#{$1}+OK #{fish.encrypt $3}"
    else
      return args
    end
  end
  return args
end

module IRC
  class BadInputError < StandardError; end
  
  class MBase64
    B64 = "./0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    def self.decode encoded
      return nil if not encoded.length % 12 == 0
      
      decoded = String.new
      
      k = -1
      while (k < encoded.length - 1) do
        right = 0
        left = 0
        
        (0..5).each do |i|
          k = k + 1
          right |= B64.index(encoded[k]) << (i * 6)
        end
        
        (0..5).each do |i|
          k = k + 1
          left |= B64.index(encoded[k]) << (i * 6)
        end
        
        (0..3).each do |i|
          decoded += ((left & (0xFF << ((3 - i) * 8))) >> ((3 - i) * 8)).chr
        end
        
        (0..3).each do |i|
          decoded += ((right & (0xFF << ((3 - i) * 8))) >> ((3 - i) * 8)).chr
        end
      end
      
      return decoded
    end
    
    def self.encode decoded
      if not decoded.length % 8 == 0
        raise IRC::BadInputError,
          "can only encode strings which are a multiple of 8 characters."
      end
      
      encoded = String.new
      
      k = -1
      
      while (k < decoded.length - 1) do
        k = k.next
        left = (decoded[k].ord << 24)
        k = k.next
        left += (decoded[k].ord << 16)
        k = k.next
        left += (decoded[k].ord << 8)
        k = k.next
        left += decoded[k].ord
        
        k = k.next
        right = (decoded[k].ord << 24)
        k = k.next
        right += (decoded[k].ord << 16)
        k = k.next
        right += (decoded[k].ord << 8)
        k = k.next
        right += decoded[k].ord
        
        (0..5).each do
          encoded += B64[right & 0x3F].chr
          right = right >> 6
        end
        (0..5).each do
          encoded += B64[left & 0x3F].chr
          left = left >> 6
        end
      end
      
      return encoded
    end
  end
  
  class FiSH
    def initialize key
      @blowfish = Crypt::Blowfish.new key
    end
    
    def encrypt text
      text = pad(text, 8)
      result = ""
      
      num_block = text.length / 8
      num_block.times do |n|
        block = text[n*8..(n+1)*8-1]
        enc = @blowfish.encrypt_block(block)
        result += MBase64.encode(enc)
      end
      
      return result
    end
    
    def decrypt text
      return nil if not text.length % 12 == 0
      
      result = ""
      
      num_block = (text.length / 12).to_i
      num_block.times do |n|
        block = MBase64.decode( text[n*12..(n+1)*12-1] )
        result += @blowfish.decrypt_block(block)
      end
      
      return result.gsub /\0*$/, ""
    end
    
    private
    
    def pad text, n=8
      pad_num = n - (text.length % n)
      if pad_num > 0 and pad_num != n
        pad_num.times { text += 0.chr }
      end
      return text
    end
  end
  
end

