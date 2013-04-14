# WeeChat pm and highlight notifications via notify-send
#
# modelled after 'WeeChat ubus notifications' by Arvid Picciani
#
# license: GPL3
# contact: shmibs@gmail.com
# history:
#	1.4		another small bug-fix
#	1.3		a small fix to formatting $message
#	1.2		use config options
#	1.1 	restructured code for (greater) sanity
#	1.0 	first working version

use strict;
use warnings;
use constant SCRIPT_NAME => 'notify_send';

weechat::register(SCRIPT_NAME, 'shmibs', '1.4', 'GPL3', 'execute a user-defined system command upon highlight or private message (with smart delays to avoid spam)', '', '');

# global var declarations
my %pv_times;
my %highlight_times;
my %settings_default=(
    'wait_pm'        => [ '180', 'necessary time delay between private messages (seconds) for command to be executed' ],
    'wait_highlight' => [ '60', 'necessary time delay between highlights (seconds) for command to be executed' ],
    'ignore_nicks'   => [ '', 'comma-separated list of nicks to ignore' ],
    'command'        => [ 'notify-send $type: $name', 'system command to be executed ($type, $name, and $message will be interpreted as values)' ]
);
my %settings=();

#------------------------------------[ START CONFIGURATION ]------------------------------------

sub config_changed {
    my ($pointer, $name, $value) = @_;
    $name = substr($name, length("plugins.var.perl.".SCRIPT_NAME."."), length($name));
    $settings{$name} = $value;
    return weechat::WEECHAT_RC_OK;
}

sub config_init{
	my $version = weechat::info_get("version_number", "") || 0;
	foreach my $option (keys %settings_default) {
		if (!weechat::config_is_set_plugin($option)) {
			weechat::config_set_plugin($option, $settings_default{$option}[0]);
			$settings{$option} = $settings_default{$option}[0];
		} else {
			$settings{$option} = weechat::config_get_plugin($option);
		}
		if ($version >= 0x00030500) {
			weechat::config_set_desc_plugin($option, $settings_default{$option}[1]." (default: \"".$settings_default{$option}[0]."\")");
		}
	}
}

config_init();
weechat::hook_config("plugins.var.perl.".SCRIPT_NAME.".*", "config_changed", "");

#-------------------------------------[ END CONFIGURATION ]-------------------------------------

my @signals=qw(weechat_pv weechat_highlight);

# message received hook
foreach(@signals) {
	weechat::hook_signal($_,'new_notification','');
}

sub new_notification {
	# $_[1] is the type (either weechat_highlight, weechat_pv)
	# $_[2] is the actual content

	# get the username and message contents
	my $name=substr($_[2],0,index($_[2],'	'));
	my $message=substr($_[2],index($_[2],'	'));
	if($name eq ' *'){
		$name=substr($_[2],index($_[2],' *')+3);
		$message=substr($name,index($name,' '));
		$name=substr($name,0,index($name,' '));
	}
	$message =~ s/	//;
	$name =~ s/@|\+//;

	# get the type of the message
	my $type;
	if($_[1] eq 'weechat_pv') {
		$type='PM';
	} else {
		$type='HL';
	}

	# boolean to determine whether or not a notification should
	# be sent
	my $send='true';

	# ignore messages from nicks in ignore_nicks option
	foreach(split(/,/,$settings{'ignore_nicks'})) {
		$send='false' if($name eq $_);
	}

	# determine whether a notification of the same type has been
	# made recently. if so, ignore it
	if($type eq 'PM'){
		if(exists $pv_times{$name}) {
			if(time-$pv_times{$name} < int($settings{'wait_pm'})) {
				$send='false';
			}
		}
		$pv_times{$name} = time;
	} else {
		if(exists $highlight_times{$name}) {
			if(time-$highlight_times{$name} < int($settings{'wait_highlight'})) {
				$send='false';
			}
		}
		$highlight_times{$name} = time;
	}

	# run system command
	if($send eq 'true') {
		my ($command,$args) = split(/ /,$settings{'command'},2);
		$args =~ s/\$type/$type/g;
		$args =~ s/\$name/$name/g;
		$args =~ s/\$message/$message/g;
		system($command, $args);
	}

	return weechat::WEECHAT_RC_OK;
}
