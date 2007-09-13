# =============================================================================
#  wee-now-playing.rb (c) 2006, 2007 Tassilo Horn <tassilo@member.fsf.org>
#
#  Licence     : GPLv3 or later
#  Description : Print what Amarok or moc is playing
#  Syntax      : /np
#                => <nick> is listening to <Artist> - <Title>
#  Precond     : needs Ruby (1.8) and amaroK (<2.0) or moc (Music on Console)
#
# =============================================================================

def get_np_info
  artist = title = ""
  catch( :info_available ) do
    # AMAROK
    # ======
    # The dcopfind returns the string "DCOPRef(amarok,)" if amaroK is
    # running, "" otherwise. So if the string is longer than 0 we can get
    # the track.
    if `dcopfind amarok`.length > 0
      artist = `dcop amarok player artist`.chomp
      title = `dcop amarok player title`.chomp
      throw( :info_available )
    end

    # MOCP
    # ====
    # Amarok was not running, so check if mocp plays something!
    if !`ps -e | grep mocp`.empty?
      info_string = `mocp -i`
      if !(info_string =~ /^State: STOP/)
        info_string.grep(/^Artist:|^SongTitle:/) do |line|
          if line =~ /^Artist:/
            artist = line.gsub!(/^Artist:/, '').strip!
          else
            title = line.gsub!(/^SongTitle:/, '').strip!
          end
        end
        throw( :info_available )
      end
    end
  end

  # Fix vulnerability where names with \n or \r can execute IRC commands:
  # See http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2007-4398
  artist.gsub!(/[\n\r]/, ' ')
  title.gsub!(/[\n\r]/, ' ')

  if !artist.empty? && !title.empty?
    "#{artist} - #{title}"
  else
    ""
  end
end

def bye(server='', args='')
  return Weechat::PLUGIN_RC_OK
end

def print_now_playing(server='', args='')
  np_string = get_np_info
  if np_string.empty?
    np_string = "nothing"
  end
  Weechat.command( "/me listenes to " + np_string + "." )
end

def weechat_init
  Weechat.register("wee-now-playing", "0.2", "bye", "print now-playing infos")
  Weechat.add_command_handler("np", "print_now_playing")
  return Weechat::PLUGIN_RC_OK
end
