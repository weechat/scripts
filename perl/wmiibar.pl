#   Author:  Sebastian Köhler <sebkoehler@whoami.org.uk>
#
#   Copyright [2010] [Sebastian Köhler]
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

use strict;

my $show_message = 0;

# weechat stuff
weechat::register('wmiibar','Sebastian Köhler <sebkoehler@whoami.org.uk>',
                  '0.3','Apache 2.0','Show highlights in the wmii statusbar',
                  '','');

weechat::hook_command('wmiibar',"Show highlights in the wmii statusbar",
                      "",
                      "Show help for wmiibar",
                      "",
                      "print_help",
                      "");
weechat::hook_signal('weechat_pv', 'highlight', '');
weechat::hook_signal('weechat_highlight','highlight','');
weechat::hook_timer(3000,0,0,'wmii_bar','');

load_defaults();

sub highlight { 
    $show_message = 1;
}
    
sub wmii_bar {
    my $sel_tag = `wmiir read /client/sel/label 2> /dev/null`;
    
    if($sel_tag =~ /^(W|w)ee(C|c)hat \d\.\d\.\d.*$/) {
        $show_message = 0;
    }
    if($show_message) {
        open BAR, "| wmiir create /rbar/0chat &> /dev/null";
            print BAR weechat::config_get_plugin("message") . "\n";
        close BAR;
    } else {
        `wmiir remove /rbar/0chat &> /dev/null`;
    }
    return weechat::WEECHAT_RC_OK;
}

sub print_help {
    my $bold   = weechat::color("bold");
    my $unbold = weechat::color("-bold");
    
    my $help = "${bold}NAME${unbold}\n".
               "    wmiibar - Show highlights in wmii statusbar\n".
               "${bold}SETTINGS${unbold}\n".
               "    /set plugins.var.perl.wmiibar.message STRING\n".
               "        STRING will be displayed in the wmii statusbar\n".
               "        Default: \"New Message\"";
    weechat::print("",$help);
}

sub load_defaults {
    if(weechat::config_get_plugin("message") eq "") {
        weechat::config_set_plugin("message","New Message");
    }
}
