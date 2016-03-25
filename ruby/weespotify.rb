# encoding: UTF-8
# Copyright (C) 2013 Paweł Pogorzelski <pawelpogorzelski@gmail.com>
# Released under GPL3.
#

SCRIPT_NAME = "weespotify".freeze
SCRIPT_AUTHOR = "Paweł Pogorzelski <pawelpogorzelski@gmail.com>".freeze
SCRIPT_VERSION = "1.1".freeze
SCRIPT_LICENSE = "GLP3".freeze
DESCRIPTION = "Now playing script for spotify (*nix only)".freeze

COMMAND_NAME = "weespotify"
COMMAND_DESCRIPTION = "display currently playing track from spotify"

class SpotifyTrack
  attr_accessor :title, :album, :artist

  SPLITTER = "♫"

  def print_output
    return "/me is listening to #{SPLITTER} #{self.title} #{SPLITTER} by #{self.artist} from the album #{self.album} on Spotify."
  end
end


def weechat_init
  Weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, DESCRIPTION, "", "")

  command_hook = Weechat.hook_command(COMMAND_NAME, COMMAND_DESCRIPTION, "", "", "", "weespotify_command", "")

  Weechat::WEECHAT_RC_OK
end


def weespotify_command(data, buffer,args)
  begin
    spotify_data = `dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Get string:'org.mpris.MediaPlayer2.Player' string:'Metadata'`
  rescue
    spotify_data = "SPOTIFY_NOT_RUNNING"
  end
  spotify_object = SpotifyTrack.new

  if spotify_data!= "SPOTIFY_NOT_RUNNING"
    spotify_array = spotify_data.to_s.split('dict entry')
    spotify_array.each {|spotify_info|
      ["title","albumArtist","album"].any? { |tested_info|
        if spotify_info.include? tested_info
          data = spotify_info.split('variant')[1]
          start_position = data.index('"')
          end_position = data.index('"',start_position+1)
          content = data[start_position+1..end_position-1]
          tested_info == 'title' ? spotify_object.title=content : nil
          tested_info == 'album' ? spotify_object.album=content : nil
          tested_info == 'albumArtist' ? spotify_object.artist=content : nil
        end
      }
    }
    Weechat.command(Weechat.current_buffer,spotify_object.print_output)
  end
end
