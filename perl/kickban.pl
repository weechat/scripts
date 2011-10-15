# kickban.pl by ArZa <arza@arza.us>: A new, customizable kickban command

# This program is free software: you can modify/redistribute it under the terms of
# GNU General Public License by Free Software Foundation, either version 3 or later
# which you can get from <http://www.gnu.org/licenses/>.
# This program is distributed in the hope that it will be useful, but without any warranty.

# This script provides command /kickban2. You probably want to alias it to /kb: /alias kb kickban2

# Changelog:
# 15.10.2011 0.2 fix bug with ban when host isn't found in memory
# 08.07.2011 0.1 initial release

weechat::register("kickban", "ArZa <arza\@arza.us>", "0.2", "GPL3", "A new, customizable kickban command", "", "");
weechat::hook_command(
  "kickban2",
  "A new, customizable kickban command", "[-nuhsd#] nick[,nick2...] [reason]",
"The ban mask can be specified by setting plugins.var.perl.kickban.banmask or by a switch (default: u,h):
  n: nick
  u: username
  h: full host
  s: subdomain
  d: domain

Timeout for unban in minutes can be set by setting plugins.var.perl.kickban.time or by a number in a switch. (default: 0, don't unban)

Multiple nicks is supported. If nick isn't found in the channel, the mask is looked up automatically. (v>=0.3.4)

The default kick reason can be set by plugins.var.perl.kickban.kick_reason.

Whether kicking will be done before banning can be speficied by plugins.var.perl.kickban.kick_first.
There may be a delay of irc.server_default.anti_flood_prio_high between commands.

Examples:

Kick nick lamer and ban its nick!*\@*.domain:
  /kickban2 -nd lamer
Kick nicks badone and badtwo with reason \"Bye bye\", and ban them by *!user\@*.domain for ten minutes:
  /kickban2 -10ud badone,badtwo Bye bye",
  "%(nick)", "kickban", "");

my $version=weechat::info_get("version_number", "") || 0;
weechat::hook_hsignal("irc_redirection_sigwhois_whois", "get_whois", "") if $version>=0x00030400;

my ($buffer, %banmask, $time, $reason);

init_config();

sub init_config {
  
  if($version>=0x00030500){ # descriptions for settings
    weechat::config_set_desc_plugin("banmask", "mask used for banning, default: u,h (*!user\@host)");
    weechat::config_set_desc_plugin("time", "time in minutes to unban after banning, 0=never (default)");
    weechat::config_set_desc_plugin("kick_first", "kick before ban (default: on)");
    weechat::config_set_desc_plugin("kick_reason", "default kick reason");
  }
  
  my %options = ( # default options
                 "banmask" => "u,h",
                 "time" => "0",
                 "kick_first" => "on",
                 "kick_reason" => "",
                );
  
  foreach my $option (keys %options){ # sync the defaults
    weechat::config_set_plugin($option, $options{$option}) unless weechat::config_is_set_plugin($option);
  }
  
}

sub kickban {
  
  if(!$_[2]){ weechat::command("", "/help kickban2"); return weechat::WEECHAT_RC_OK; }
  
  $buffer=$_[1];
  my @args=split(/ /, $_[2]);
  $time=weechat::config_get_plugin("time");
  %banmask=();
  my @nicks;
  
  for(my $i=0; $i<=$#args+1; $i++){ my $arg=$args[$i] || last; # go through arguments
    if($arg=~/^\-/){ # begins '-': banmask/time switches
      foreach("n","u","h","s","d"){ $banmask{$_}=1 if $arg=~/$_/; } # set banmask type
      if($arg=~/(\d+)/){ $time=$1; } # any number = unban time
    }else{ # the rest is nicks (and reason)
      @nicks=split(/,/, $arg);
      $reason=join(' ', @args[$i+1..$#args]); # the reason
      last;
    }
  }
  
  return weechat::WEECHAT_RC_ERROR unless @nicks; # return if didn't get nicks
  
  if(!%banmask){ $banmask{$_}=1 foreach (split(/,/, weechat::config_get_plugin("banmask"))); } # get the banmask from the setting if it's not given as an argument
  
  if($banmask{"h"}){ $banmask{"s"}=$banmask{"d"}=1; } # host -> subdomain and domain
  
  $reason=weechat::config_get_plugin("kick_reason") unless $reason; # get the reason from the setting if it's not given as an argument
  
  my $infolist = weechat::infolist_get( # get the irc_nick infolist of current channel or return
                                       "irc_nick",
                                       "",
                                       weechat::buffer_get_string($buffer, "localvar_server").
                                        ','.
                                        weechat::buffer_get_string($buffer, "localvar_channel")
                                      ) || return weechat::WEECHAT_RC_ERROR;
  
  while(weechat::infolist_next($infolist)){ # go through the infolist
    foreach my $nick (@nicks) { # go through nicks to be kicked
      if(lc(weechat::infolist_string($infolist, "name")) eq lc($nick)){ # if match (case insensitive)
        my $host=weechat::infolist_string($infolist, "host") || next;
        my $ban=gen_mask($nick, split(/@/, $host)); # split variable host from infolist to user and host, get banmask
        weechat::command($buffer, "/kick $nick $reason") if weechat::config_get_plugin("kick_first") ne "off"; # kick before ban
        weechat::command($buffer, "/ban $ban"); # ban
        weechat::command($buffer, "/kick $nick $reason") if weechat::config_get_plugin("kick_first") eq "off"; # kick after ban
        weechat::command($buffer, "/wait ".60*$time." /unban $ban") if $time;
        undef $nick;
      }
    }
  }
  
  weechat::infolist_free($infolist);
  
  if($version>=0x00030400){ # hook_hsignal reguires v>=0.3.4
    my $server=weechat::buffer_get_string($buffer, "localvar_server"); # current server
    foreach my $nick (@nicks) { # the nicks that weren't found in the channel
      if($nick){
        weechat::hook_hsignal_send("irc_redirect_command", { "server" => "$server", "pattern" => "whois", "signal" => "sigwhois" }); # redirection
        weechat::hook_signal_send("irc_input_send", weechat::WEECHAT_HOOK_SIGNAL_STRING, "$server;;1;;/whois $nick"); # send whois command
      }
    }
  }
  
}

sub get_whois { my %hashtable=%{$_[2]}; # get the answer for whois
  if($hashtable{"output"}=~/^:\S+ 311 \S+ (\S+) (\S+) (\S+)/){
    my $ban=gen_mask($1,$2,$3);
    weechat::command($buffer, "/ban $ban"); # ban
    weechat::command($buffer, "/wait ".60*$time." /unban $ban") if $time; # unban
    return weechat::WEECHAT_RC_OK;
  }elsif($hashtable{"output"}=~/^:\S+ 401 \S+ (\S+)/){
    weechat::print("", weechat::prefix("error")."Kickban: Didn't find nick $1");
    return weechat::WEECHAT_RC_OK;
  }
}

sub gen_mask { my ($nick, $user, $fullhost) = @_; # generate banmask
  
  my ($ban, $sub, $domain);
  
  if($fullhost=~/\w/){ # if there are letters in the host (it's not an ip)
    my @hostparts=split(/\./, $fullhost); # split host to subdomain and domain
    if(@hostparts>2){ # if there are at least three parts
      $sub=join(".", @hostparts[0..$#hostparts-2]); # subdomain is the beginning
      $domain=$hostparts[$#hostparts-1].".".$hostparts[$#hostparts]; # domain is the last two parts
    }
  }
  
  if($banmask{"n"}){ # if nick is in banmask
    $ban=$nick."!";
  }else{
    $ban="*!";
  }
  
  if($banmask{"u"}){ # if user is in banmask
    $ban.=$user."\@";
  }else{
    $ban.="*\@";
  }
  
  if($banmask{"s"}){ # if subdomain is in banmask
    if($banmask{"d"} || !$sub){ # use the full host if also domain is in banmask or anyway if subdomain isn't specified
      $ban.=$fullhost;
    }else{
      $ban.=$sub.".*";
    } 
  }elsif($banmask{"d"}){ # if domain is in banmask but subdomain isn't
    if($domain){ $ban.="*.$domain"; }
    else{ $ban.=$fullhost; } # use the full host anyway if domain isn't separated from subdomain
  }else{
    $ban.="*";
  }
  
  return $ban;
  
}
