#
# (c) 2013 Hendrik 'henk' Jaeger <weechat@henk.geekmail.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

def weechat_init
  Weechat.register(
    "samechannel",
    "henk",
    "0.0.1",
    "GPL3",
    "Lists multiple occurences of the same nick(s) in a set of channels.",
    "",
    ""
  )

  Weechat.hook_command(
    "samechannel",
    "Lists multiple occurences of the same nick(s) in a set of channels.",
    "[[-s|--servers] servername[,...]] [[-c|--channels] channelname[,...]] [[-n|--nicks] nickname[,...]]",
    "--servers servername[,servername],...]
--channels channelname[@servername][,channelname[@servername],...]
--nicks nickname[,nickname,...]
Options used to set filters. All given names are treated as regular expressions. If no names are given, no filters are set.

WARNING: If you are joined to MANY or even just a few very crowded channels, this script may have to do a lot of comparisons!

NOTE: Only nicknames from channels the client is joined to are available for comparison!

EXAMPLES:
    /samechannel --channels foo
    Lists nicks found in more than two channels on all servers.

    /samechannel --nicks barbaz,hons --servers example,foobarbaz
    Lists channels from the servers example and foobarbaz for each given nick.

    /samechannel --nicks foo --channels ^#example.*@.*free.*$
    Lists channels you share with nick foo that begin with 'example' from every server with 'free' in their names.",
    "-servers %(irc_servers)
    || -servers %(irc_servers) -channels %(irc_channels)
    || -servers %(irc_servers) -nicks %(irc_server_nicks)
    || -channels %(irc_channels)
    || -channels %(irc_channels) -servers %(irc_servers)
    || -channels %(irc_channels) -nicks %(irc_server_nicks)
    || -nicks %(irc_server_nicks)
    || -nicks %(irc_server_nicks) -servers %(irc_servers)
    || -nicks %(irc_server_nicks) -channels %(irc_channels)",
    "samechannel_cb",
    ""
  )

  require 'shellwords'
  require 'optparse'

  $hdata_ircserver = Weechat.hdata_get('irc_server')
  $hdata_ircchannel = Weechat.hdata_get('irc_channel')
  $hdata_ircnick = Weechat.hdata_get('irc_nick')

  return Weechat::WEECHAT_RC_OK
end

def samechannel_cb( data, buffer, args )
  options = get_options( args.shellsplit )

  serverchannelptrs = Hash.new
  nickcount = Hash.new

  serverptrs = find_servers(options[:serverfilter])

  serverptrs.each do |serverptr|
    serverchannelptrs[serverptr] = find_channels(options[:channelfilter], serverptr)
  end

  serverchannelptrs.each_pair do |serverptr, channelptrs|
    servername = Weechat.hdata_string($hdata_ircserver, serverptr, 'name')
    own_nick = Weechat.hdata_string($hdata_ircserver, serverptr, 'nick')

    channelptrs.each do |channelptr|
      channelname = Weechat.hdata_string($hdata_ircchannel, channelptr, 'name')

      find_nicks(options[:nickfilter], channelptr).each do |nickptr|
        nickname = Weechat.hdata_string($hdata_ircnick, nickptr, 'name')
        next if nickname == own_nick
        (nickcount[nickname] ||= Array.new) << [channelname, servername].join('@')
      end
    end
  end

  duplicate_nicks = nickcount.delete_if do |nickname, nickpaths|
    nickpaths.length <= 1
  end
  duplicate_nicks_sorted = duplicate_nicks.sort do |a, b|
    a[1].length <=> b[1].length
  end
  duplicate_nicks_sorted.each do |nickname, nickpaths|
    Weechat.print("", "#{Weechat.color('yellow')}#{nickname}#{Weechat.color('chat')} appeared #{nickpaths.length} times: #{nickpaths.join(', ')}")
  end

  return Weechat::WEECHAT_RC_OK
end

def find_nicks( names, channelptr )
  all_nicks = hhh_get_ptrarray($hdata_ircnick, Weechat.hdata_pointer($hdata_ircchannel, channelptr, 'nicks'))
  if names
    all_nicks.find_all do |nickptr|
      nickname = Weechat.hdata_string($hdata_ircnick, nickptr, 'name')
      foundnames = names.any? do |name|
        Regexp.new(name).match(nickname)
      end
    end
  else
    return all_nicks
  end
end

def find_channels( names, serverptr )
  servername = Weechat.hdata_string($hdata_ircserver, serverptr, 'name')
  all_channels = hhh_get_ptrarray($hdata_ircchannel, Weechat.hdata_pointer($hdata_ircserver, serverptr, 'channels'))
  if names
    all_channels.find_all do |channelptr|
      channelname = Weechat.hdata_string($hdata_ircchannel, channelptr, 'name')
      foundnames = names.any? do |name|
        name_re = Regexp.new(name)
        if /.*@.*/.match(name)
          name_re.match(channelname + '@' + servername)
        else
          name_re.match(channelname)
        end
      end
    end
  else
    return all_channels
  end
end

def find_servers( names )
  serverptrlist = Weechat.hdata_get_list($hdata_ircserver, 'irc_servers')
  if names
    matching_servers = names.map do |name|
      foundserverptr = Weechat.hdata_search($hdata_ircserver, serverptrlist, '${irc_server.name} =~ ' + name, 1)
    end
  else
    return hhh_get_ptrarray($hdata_ircserver, serverptrlist)
  end
end

def hhh_get_ptrarray( hdata, pointer )
  pointers = Array.new
  begin
    pointers << pointer unless pointer.empty?
  end until (pointer = Weechat.hdata_move(hdata, pointer, 1)).empty?
  return pointers
end

def get_options( args )
  options = Hash.new

  opt_parser = OptionParser.new do |opts|
    opts.on("-c", "--channels channelname[,channelname,...]",
            "Only channels matching the given (partial) channelname(s) will be considered.)") do |channels|
      options[:channelfilter] = channels.split(',')
    end

    opts.on("-n", "--nicks nickname[,nickname,...]",
            "Only nicks matching the given (partial) nickname(s) will be considered.)") do |nicks|
      options[:nickfilter] = nicks.split(',')
    end

    opts.on("-s", "--servers servername[,servername,...]",
            "Only servers matching the given (partial) servername(s) will be considered.)") do |servers|
      options[:serverfilter] = servers.split(',')
    end
  end

  opt_parser.parse(args)

  return options
end
