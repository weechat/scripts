#
# Copyright (c) 2010-2013 by Nils Görs <weechatter@arcor.de>
#
# checks POP3 server for mails and display mail headers
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
# Config:
# Add [mail] to your weechat.bar.status.items
#
#
# 2013-09-15: nils_2 (freenode.#weechat)
#       0.3 : add: option prefix_item
#
# 2013-07-29: nils_2 (freenode.#weechat)
#       0.2 : support of /secure for passwords
#           : added: %h variable for filename
#
# 0.1: initial version
#
# Thanks to Trashlord for the hint with hook_process()
#
# Development is currently hosted at
# https://github.com/weechatter/weechat-scripts
#
# This script needs following perl modules:
# Tie::IxHash
# Mail::POP3Client
# IO::Socket::SSL
# MIME::Base64
# Crypt::Rijndael
# You can install them using "cpan"

# do not sort my hash
use Tie::IxHash;
my %pop3_accounts;
my %mail_counts;
# user@mail.de|pop3.server:port
tie %pop3_accounts, Tie::IxHash;

###
#use strict;
use Mail::POP3Client;
use MIME::Base64;
use Crypt::Rijndael;
use Encode;

my $prgname             = "pop3_mail";
my $SCRIPT_version      = "0.3";
my $description         = "check POP3 server for mails and display mail header";
my $item_name           = "mail";


# -------------------------------[ config ]-------------------------------------
my $default_pop3list = "%h/pop3list.txt";
my %default_options = ("refresh"                        => "10",                # interval in minutes to check pop3 accounts
                       "pop3_timeout"                   => "20",                # timeout for pop3_server (in seconds)
                       "show_header"                    => "From|Subject",
                       "passphrase"                     => "enter passphrase",
                       "delete_passphrase_on_exit"      => "on",
                       "prefix_item"                    => "✉:",
                       );


# ------------------------------[ internal ]-----------------------------------
my %Hooks               = ();   # space for my hooks
my %mailcount           = ();   # how many mails for all accounts and in how many accounts?
my $bar_item            = "";
my $filename            = ();
my $weechat_version     = "";

# -------------------------------[ hook_process() command ]-------------------------------------
# arguments: user, password, server, port, timeout, (no)header
if ($#ARGV == 5 ) {             # six arguments given?
my $user = $ARGV[0];
my $password = $ARGV[1];
my $pop3server = $ARGV[2];
my $port = $ARGV[3];
my $timeout = $ARGV[4];
my $header = $ARGV[5];

if ($port eq "995") {
  $use_ssl = 1;
} else {
  $use_ssl = 0;
}
	  my $pop3 = new Mail::POP3Client(
					    #DEBUG	=> 1,
					    USER	=> $user,
					    PASSWORD	=> $password,
					    HOST	=> $pop3server,
					    TIMEOUT	=> $timeout,
#					    PORT	=> $port,
					    USESSL	=> $use_ssl, 		# if true use port 995 otherwise port 110
					  );

	  my $num_mesg = $pop3->Count;						# how many messages are there?

if ($header ne "noheader"){

  for( $i = 1; $i <= $pop3->Count(); $i++ ) {
    foreach( $pop3->Head( $i ) ) {
      my $decoded = encode("utf-8",decode("MIME-Header",$_));

      /^($header):\s+/i && print "$decoded\n";	# decode MIME and encode to UTF8
    }
    print "\n";
  }
}else{
  print "$num_mesg\n";
}
$pop3->Close();

exit;
}

# -------------------------------[ weechat program starts here ]-------------------------------------
# check out config settings
sub toggled_by_set{
	my ( $pointer, $option, $value ) = @_;
	my $plugin_name = "plugins.var.perl.$prgname.";
	if ($option eq $plugin_name."refresh"){
		$default_options{refresh} = $value;
	if (!weechat::config_is_set_plugin("refresh")){
	  $default_options{refresh} = 10;	#default 10 minutes
	  weechat::config_set_plugin("refresh", $default_options{refresh});
	}

	if ($default_options{refresh} ne "0"){
		if (defined $Hooks{timer}) {
			unhook_timer();
			hook_timer();
			return weechat::WEECHAT_RC_OK;
		}
	}
	if ($default_options{refresh} eq "0"){
		if (defined $Hooks{timer}) {
			unhook_timer();
		}
	}else{
		if (not defined $Hooks{timer}){
			weechat::config_set_plugin("refresh", "0") unless hook_timer();		# fall back to '0', if hook fails
		}
	}
        }elsif ($option eq $plugin_name."prefix_item"){
            $default_options{prefix_item} = my_eval_expression($value);
            weechat::bar_item_update($item_name);
        }elsif ($option eq $plugin_name."pop3_timeout"){
            $default_options{pop3_timeout} = $value;
        }elsif ($option eq $plugin_name."show_header"){
            $default_options{show_header} = $value;
        }elsif ($option eq $plugin_name."passphrase"){
            $default_options{passphrase} = my_eval_expression($value);
            return weechat::WEECHAT_RC_OK if (check_passphrase_length($default_options{passphrase}) eq 1);
        }elsif ($option eq $plugin_name."delete_passphrase_on_exit"){
            $default_options{delete_passphrase_on_exit} = $value;
        }

return weechat::WEECHAT_RC_OK;
}
sub hook_timer{
	count_messages();

	$Hooks{timer} = weechat::hook_timer($default_options{refresh} * 1000 * 60, 0, 0, "count_messages", "");	# period * millisec(1000) * second(60) * minutes(60)
		if ($Hooks{timer} eq '')
		{
			weechat::print("",weechat::prefix("error")."can't enable $prgname, hook failed.");
			return 0;
		}
#	$bar_item = weechat::bar_item_new($item_name, "show_mail","");
	weechat::bar_item_update($item_name);
	return 1;
}
sub unhook_timer{
	weechat::bar_item_remove($bar_item);
	$bar_item = "";
	if (defined $Hooks{timer}){
	  weechat::unhook($Hooks{timer});
	  delete $Hooks{timer};
	}
}

# user commands
sub user_cmd{
	my ($getargs) = ($_[2]);

	  return weechat::WEECHAT_RC_OK if (check_passphrase_length($default_options{passphrase}) eq 1);
	  if ($getargs eq ""){
	    weechat::command("","/help $prgname");
	    return weechat::WEECHAT_RC_OK;
	  }

	if ($getargs eq "list"){							# list all accounts
	  weechat::print("","POP3 accounts:");
	  my $i = 1;
	  my $x = keys %pop3_accounts;
	  if ($x eq 0){
	    	   weechat::print("","no accounts added yet");
	  }else{
	    while ( my($key,$password) = each %pop3_accounts) {
		  my ($user,$pop3server) = split (/\|/,$key);				# format : username|servername:port

#		  $password = decode_Rijndael($password);
		  $i = sprintf("%03d",$i);
		  my ($servername, $port) = split(/:/,$pop3server);
		  $port = $port . weechat::color("chat") . " (" . weechat::color("chat_delimiters") ."ssl" . weechat::color("chat") . ")" if ($port eq "995");
# get number of emails
		  my $account = $user.$servername;
		  my $num_mesg;
		  if (defined $mail_counts{$account}){
		    $num_mesg = $mail_counts{$account};
		  }else{
		    $num_mesg = 0;
		  }
		  $num_mesg = sprintf("% 3d",$num_mesg);
# print infos
		  weechat::print( "",
		  "  ["
		  . weechat::color("chat_delimiters")
		  . $i
		  . weechat::color("chat")
		  . "]"
		  . " mails: "
		  . weechat::color("chat_delimiters")
		  . $num_mesg
		  . weechat::color("chat")
		  . " user: "
		  . weechat::color("chat_delimiters")
		  . $user . weechat::color("chat")
		  . " server: "
		  . weechat::color("chat_delimiters")
		  . $servername
		  . weechat::color("chat")
		  . " port: "
		  . weechat::color("chat_delimiters")
		  . $port
		  . weechat::color("chat"));

#		  . " password: " . $password);
		  $i = $i + 1;
	    }
	  }
	return weechat::WEECHAT_RC_OK;
	}

	    count_messages() if ($getargs eq "check");

	    my ( $cmd, $arg ) = ( $getargs =~ /(.*?)\s+(.*?)/ );
	    return weechat::WEECHAT_RC_OK if (not defined $cmd);

	    if ($cmd eq "list" and defined $arg){
	      ( $cmd, $arg ) = ( $getargs =~ /(.*?)\s+(\d.*)/ );

		if (not defined $cmd){
		  weechat::print("",weechat::prefix("error")."$prgname: wrong arguments");
		  return weechat::WEECHAT_RC_OK;
		}
	    if ($cmd eq "list"){							# display messages on server for account
		my $i = 1;

	      if ($arg !~ /^-?\d+(?:[\.,]\d+)?$/){					# only numbers for account?
		  weechat::print("",weechat::prefix("error")."$prgname: invalid account number");
		  return weechat::WEECHAT_RC_OK;
	      }

	      foreach my $key ( keys %pop3_accounts ) {
		  my $password = $pop3_accounts{$key};
		  if ($arg == $i){
		  get_message_header($key,$password);
		    return weechat::WEECHAT_RC_OK;
		  }
		  $i = $i + 1;
		  }
		    return weechat::WEECHAT_RC_OK;
		}
	    }

	    if ($cmd eq "del" and defined($arg)){					# check command and if argument exists
	      ( $cmd, $arg ) = ( $getargs =~ /(.*?)\s+(\d.*)/ );
		my $i = 1;
		foreach my $key ( keys %pop3_accounts ) {
		  if ($arg == $i){
		    delete $pop3_accounts{$key};					# delete user account
		    save_file();
		    last;
		  }
		  $i = $i + 1;
		}
	      unhook_timer();
	      hook_timer();
	    }

	    if ($cmd eq "add" and defined($arg)){
	      my ( $cmd, $user, $host ,$password ) = ( $getargs =~ /(.*?)\s(.*?)\s(.*?)\s(.*)/ );
	      if (not defined $password or not defined $host or index($host,":") eq -1){
		weechat::print("",weechat::prefix("error")."$prgname: wrong arguments given to add account: <username[\@host]> <servername:port> <password>");
		return weechat::WEECHAT_RC_OK;
	      }
	      $user = $user."|".$host;							# username@adress|host

	      $password = encode_Rijndael($password);
	      chomp($password);
	      $pop3_accounts{$user} = $password;					# add new user account with password
	      save_file();

	      unhook_timer();
	      hook_timer();
	    }

return weechat::WEECHAT_RC_OK;
}

sub init
{
    weechat::config_set_plugin("pop3_list", $default_pop3list ) if ( weechat::config_get_plugin("pop3_list") eq "" );
    read_file();

    # get absolute path of script
    my $infolist_pnt = weechat::infolist_get("perl_script","",$prgname);
    weechat::infolist_next($infolist_pnt);
    $filename = weechat::infolist_string($infolist_pnt,"filename");
    weechat::infolist_free($infolist_pnt);

#set default config
foreach my $option (keys %default_options)
{
    if ( !weechat::config_is_set_plugin($option) )
    {
        weechat::config_set_plugin($option, $default_options{$option});
    }else
    {
        $default_options{$option} = weechat::config_get_plugin($option);
    }
}
    $default_options{passphrase} = my_eval_expression($default_options{passphrase});
    $default_options{prefix_item} = my_eval_expression($default_options{prefix_item});

    return if (check_passphrase_length($default_options{passphrase}) eq 1);
}

sub show_mail {
    if ( (keys %pop3_accounts) == 1 ){
      return sprintf ("$default_options{prefix_item} %d", $mailcount{mails_over_all});
    }else{
      return sprintf ("$default_options{prefix_item} %d (%d)", $mailcount{mails_over_all}, $mailcount{accounts_with_mails});
    }
}

# -------------------------------[ hook_process callback ]-------------------------------------
sub hook_process_cb{
my ($data, $command, $return_code, $out, $err) = @_;

return weechat::WEECHAT_RC_OK if ( $return_code > 0 );				# something went wrong!


my (undef, undef, $nick, undef, $server, undef) = split /\s+/, $command, 6;
my $account = $nick.$server;
chomp($out);									# kill LF

$mailcount{num_mesg} = $out;							# save number of messages
$mailcount{num_mesg} = 0 if ($out == -1);					# something wrong with account!
$mailcount{accounts_with_mails} = $mailcount{accounts_with_mails} + 1 if ($out > 0);	# how many accounts have mails?

$mail_counts{$account} = $mailcount{num_mesg};					# save number of mails for the account
$mailcount{mails_over_all} = $mailcount{mails_over_all} + $mailcount{num_mesg};	# all counted messages from all accounts

if ( $bar_item ne "" and $mailcount{mails_over_all} == 0 or not defined $mailcount{mails_over_all} ){
	weechat::bar_item_remove($bar_item);
	$bar_item = "";
}elsif ( ($mailcount{mails_over_all} > 0) and ($bar_item eq "") ){
	$bar_item = weechat::bar_item_new($item_name, "show_mail","");
}

weechat::bar_item_update($item_name);
return weechat::WEECHAT_RC_OK;
}

# mail header
sub hook_process_cb2{
my ($data, $command, $return_code, $out, $err) = @_;
return weechat::WEECHAT_RC_OK if ( $return_code > 0 );

my (undef, undef, $nick, undef, $server, undef) = split /\s+/, $command, 6;

my @array=split(/\n\n/,$out);
my $i = 1;
  weechat::print( "", "mails for \"$nick\" on server \"$server\":");

foreach (@array) {
  weechat::print( "", weechat::color("chat_delimiters")
		. "[" . weechat::color("chat_buffer")
		. " mail " . $i
		. weechat::color("chat_delimiters")
		. " ]" . weechat::color("chat")
		. "\n$_" );
$i++;

}
return weechat::WEECHAT_RC_OK;
}
# -------------------------------[ POP3 routines ]-------------------------------------
sub count_messages{
    $mailcount{num_mesg} = 0;
    $mailcount{mails_over_all} = 0;
    $mailcount{accounts_with_mails} = 0;


    foreach my $key ( keys %pop3_accounts ) {
      my ($user,$pop3server,$port) = split (/:|\|/,$key);					# format : username|servername:port
      my $password = decode_Rijndael($pop3_accounts{$key});
	  weechat::hook_process("perl $filename $user $password $pop3server $port $default_options{pop3_timeout} noheader", 1100 * $default_options{pop3_timeout},"hook_process_cb","");
    }

return weechat::WEECHAT_RC_OK;
}

sub get_message_header {
   my ($key,$password) = @_;
   my $i;
   my $use_ssl = 0;

    if ($default_options{show_header} eq "" or not defined $default_options{show_header}){
	weechat::print("",weechat::prefix("error")."$prgname: option \"plugins.var.perl.$prgname.show_header\" not set.");
	return;
    }

      my ($user,$pop3server,$port) = split (/:|\|/,$key);			# format : username|servername:port
      my $account = $user.$pop3server;
    if (not defined $mail_counts{$account} or $mail_counts{$account} eq 0){
	weechat::print("",weechat::prefix("error")."$prgname: no mails on server \"$pop3server\" for \"$user\"");
	return;
    }

      $password = decode_Rijndael($password);

	  weechat::hook_process("perl $filename $user $password $pop3server $port $default_options{pop3_timeout} \"$default_options{show_header}\"", 1100 * $default_options{pop3_timeout},"hook_process_cb2","");
}

# -------------------------------[ AES encode / decode: key must be 128, 192 or 256 bits long ]-------------------------------------
sub encode_Rijndael{
  my ( $plaintext ) = @_; # Your string to be encrypted

  my $base64 = "";

  my $rcipher = Crypt::Rijndael->new ($default_options{passphrase}, Crypt::Rijndael::MODE_CBC());
  $rcipher->set_iv($default_options{passphrase}); # You may wish this IV to be something different from the Secret Key


  if(length($plaintext) % 16 != 0 ) {
  $plaintext .= ' ' x (16 - (length($plaintext) % 16)); }
  my $rencrypted = $rcipher->encrypt($plaintext);		# encrypt

  $base64 = encode_base64($rencrypted);				# base64 it
  return $base64;
}

sub decode_Rijndael{
  my ( $base64 ) = @_; # enctypted base64 string

  my $rcipher = Crypt::Rijndael->new ($default_options{passphrase}, Crypt::Rijndael::MODE_CBC());
  $rcipher->set_iv($default_options{passphrase}); # You may wish this IV to be something different from the Secret Key

  $base64 = decode_base64($base64);

#  if(length($plaintext) % 16 != 0 ) {
#  $plaintext .= ' ' x (16 - (length($plaintext) % 16)); }
  my $rencrypted = $rcipher->decrypt($base64);
  $rencrypted =~ s/\s+\z//;					# remove space from end of string

  return $rencrypted;
}

sub check_passphrase_length
{
    my ( $passphrase ) = @_;
    my $len = length($passphrase);
    if (! ($len == 16) or ($len == 24) or ($len == 32) )
    {
        weechat::print("",weechat::prefix("error")."$prgname: wrong key length: passphrase must be 128, 192 or 256 bits long");
        return 1; #false
    }
return 0; #true
}

sub my_eval_expression
{
    my $value = $_[0];
    if ( ($weechat_version ne "") && ($weechat_version >= 0x00040200) )
    {
        my $eval_expression = weechat::string_eval_expression($value,{},{},{});
        return $eval_expression if ($eval_expression ne "");
    }
return $value;
}


# -------------------------------[ load, save, shutdown, debug routine ]-------------------------------------
sub save_file
{
    my $x = keys %pop3_accounts;
    if ($x ne 0)                        # messages in pop3_accounts?
    {
        my $pop3list = weechat_dir();
        open (WL, ">", $pop3list) || DEBUG("write pop3_list: $!");
        while ( my($user,$passwort) = each %pop3_accounts)
        {
            print WL "$user $passwort\n";
        }
        close WL;
    }
    else
    {
        my $pop3list = weechat_dir();
        unlink($pop3list);
    }
}
sub read_file
{
    my $pop3list = weechat_dir();
    return unless -e $pop3list;
    open (WL, "<", $pop3list) || DEBUG("$pop3list: $!");
    while (<WL>)
    {
        chomp;                                                  # kill LF
        my ( $user, $password ) = split / /;                    # <user> <password>
        if (not defined $user)
        {
            close WL;
            weechat::print("",weechat::prefix("error")."$prgname: $pop3list is not valid...");
            return;
        }
        $pop3_accounts{$user} = $password  if length $_;
    }
    close WL;
}

sub weechat_dir
{
    my $dir = weechat::config_get_plugin("pop3_list");
    if ( $dir =~ /%h/ )
    {
        my $weechat_dir = weechat::info_get( 'weechat_dir', '');
        $dir =~ s/%h/$weechat_dir/;
    }
    return $dir;
}

sub shutdown{
# remove my hooks
  if (defined $Hooks{timer}) {
      weechat::unhook($Hooks{timer});
  }
  if (defined $Hooks{command}) {
      weechat::unhook($Hooks{command});
  }
  if (defined $Hooks{config}) {
      weechat::unhook($Hooks{config});
  }
  if ($default_options{delete_passphrase_on_exit} eq "on"){
       weechat::config_unset_plugin("passphrase","");
  }

  return weechat::WEECHAT_RC_OK;
}
sub DEBUG {weechat::print('', "***\t" . $_[0]);}

# first function called by a WeeChat-script.
weechat::register($prgname, "Nils Görs <weechatter\@arcor.de>", $SCRIPT_version,
                  "GPL3", $description, "shutdown", "");
$weechat_version = weechat::info_get("version_number", "");

init();

$Hooks{config}  = weechat::hook_config( "plugins.var.perl.$prgname.*", "toggled_by_set", "" );
$Hooks{command} = weechat::hook_command($prgname, $description,
		"[list <account>] | [add user(\@host) server:port password] | [del number] | check",

                "list         : display account(s)\n".
                "list <number>: display mail header(s) for specified account\n".
                "add          : add new account (template: <username> <server:port> <password>)\n".
                "del <number> : delete an account\n".
                "check        : check POP3 account(s) manually\n".
                "\n".
                "This script is using Rijndael(AES) encryption to protect your pop3 password(s) in config file.\n".
                "Keep in mind that the passphrase is not encrypted. Use /rmodifier function to hide passphrase.\n".
                "Using Weechat 0.4.2 or higher its recommended to use /secure to protect passphrase.\n".
                "\n".
                "Options:\n".
                "plugins.var.perl.$prgname.passphrase                   : to encrypt pop3 passwords in config file (default: empty)\n".
                "                                                          Since WeeChat 0.4.2 its possible to encrypt passphrase (see /help secure) eg: \${sec.data.pop3_passphrase}\n".
                "plugins.var.perl.$prgname.pop3_list                    : file to store account, server and password (default: %h/pop3list.txt)\n".     "plugins.var.perl.$prgname.pop3timeout                  : set a timeout (in seconds) for socket operations (default: 20)\n".
                "plugins.var.perl.$prgname.refresh                      : checks pop3 account (in minutes) (default: 10)\n".
                "plugins.var.perl.$prgname.show_header                  : displays mail headers (default: From|Subject)\n".
                "plugins.var.perl.$prgname.prefix_item                  : displays a prefix (default: ✉:). Since WeeChat 0.4.2 you can use \${color:xxx}\n".
                "plugins.var.perl.$prgname.delete_passphrase_on_exit    : delete passphrase on exit (default: on)\n".
                "\n".
                "You have to edit option \"delete_passphrase_on_exit\" manually each time when weechat or script (re)starts. Switching option to \"off\" will keep passphrase in weechat-config.\n".
                "\n".
                "Add item [mail] to your \"weechat.bar.status.items\"\n".
                "\n".
                "Examples:\n".
                "Add account with hostname and ssl/tls protocol to monitore:\n".
                "/$prgname add myuser\@host.de pop3.server.de:995 mypassword\n".
                "Add account without hostname and without ssl/tls protocol to monitore:\n".
                "/$prgname add myuser pop3.server.de:110 mypassword\n".
                "Delete account with number 001 from list:\n".
                "/$prgname del 1\n",
                "add|del|list|check", "user_cmd", "");


hook_timer() if ($default_options{refresh} ne "0");

weechat::bar_item_update($item_name);
