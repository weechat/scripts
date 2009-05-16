# This script is a port from the original fortune.pl irssi script written by
# Ivo Marino <eim@cpan.org>. This script is in the public domain
# 
# Original WeeChat Author: Julien Louis <ptitlouis@sysif.net>
#
# Port to WeeChat 0.3.0: Sid Vicious (aka Trashlord) <dornenreich666@gmail.com>

weechat::register("fortune", "ptitlouis", "0.2", "Public domain", "Send a random fortune cookie to a specified nick", "", "");

weechat::hook_command("fortune", "Send a random fortune cookie to a specified nick",
	"<nick> [lang]", 
	"<nick> The nickname to send the fortune cookie\n" .
	" [lang] The cookie language (Default: en)\n",
	"", "fortune", "");

sub fortune {

    my ($data, $buffer, $param) = @_;
    my $rc = weechat::WEECHAT_RC_OK;
    my $cookie = '';
    if ($param) {
        (my $nick, my $lang) = split (' ', $param);
        $lang = 'en' unless ($lang eq 'de'|| $lang eq 'it' || $lang eq
                             'en' || $lang eq 'fr' );
        weechat::print($buffer, "Nick: " . $nick . ", Lang: \"" . $lang . "\"");
        
        if ($lang eq 'de') {
            $cookie = `fortune -x`;
        } 
        elsif ($lang eq 'it') {
            $cookie = `fortune -a italia`;
        } 
        else {
            $cookie = `fortune -a fortunes literature riddles`;
        }
        
        $cookie =~ s/\s*\n\s*/ /g;
        if ($cookie) {
            weechat::command($buffer, $nick . ": " . $cookie, $channel);
        }
        
        else {
            weechat::print($buffer, "No cookie.");
            $rc = weechat::WEECHAT_RC_ERROR;
        }
    }
    else {
        weechat::print ($buffer, "Usage: /fortune <nick> [language]");
        $rc = weechat::WEECHAT_RC_ERROR;
    }
    
    return $rc;
}
