#####################################################################
# xmms perl script for weechat                                      #
#                                                                   #
# Displays some useless xmms-infopipe values                        #
# (c) 2006 by Cédric Chalier <ounaid AT gmail DOT com>              # 
#                                                                   #
# This program is free software; you can redistribute it and/or     #
# modify it under the terms of the GNU General Public License       #
# as published by the Free Software Foundation; either version 2    #
# of the License, or (at your option) any later version.            #
#                                                                   #
# This program is distributed in the hope that it will be useful,   #
# but WITHOUT ANY WARRANTY; without even the implied warranty of    #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the     #
# GNU General Public License for more details.                      #
#                                                                   #
# You should have received a copy of the GNU General Public License #
# along with this program; if not, write to the Free Software       #
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,        #
# MA  02110-1301, USA.                                              #
#                                                                   #
#####################################################################
#  db[x] variables are:                                             #
# -----------------------------------------------------------       #
# | 0 | XMMS protocol version      |  7 | uSecTime                  #
# | 1 | InfoPipe Plugin version    |  8 | Time                      #
# | 2 | Status                     |  9 | Current bitrate           #
# | 3 | Tunes in playlist          | 10 | Samping Frequency         #
# | 4 | Currently playing          | 11 | Channels                  #
# | 5 | uSecPosition               | 12 | Title                     #
# | 6 | Position                   | 13 | File                      #
#                                                                   #
#####################################################################

# FlashCode <flashcode@flashtux.org>, 2007-11-02, version 1.2:
#   Fix vulnerability where names with \n or \r can execute IRC commands:
#   See http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2007-4398

weechat::register ("xmms", "1.2", "", "xmms info script (usage: /xmms)");
weechat::add_command_handler ("xmms", xmmsinfo);

sub xmmsinfo {
    if (! -e "/tmp/xmms-info")
    {} 
    else 
    {
        open (fi, "/tmp/xmms-info");
        @db2 = <fi>;
        foreach $l (0 .. 14)
        {
            ($c,$tmp) = split(": " ,$db2[$l]);
            chomp($tmp);
            push @db,$tmp;
        }
    }
    $db[12] =~ s/[\n\r]/ /g;
    if (($db[7]!=-1) && ($db[7]!=0)) 
    {
        weechat::command("/me np: $db[12]");
    }
    else
    {
        $db[13] =~ s/[\n\r]/ /g;
        weechat::command("/me np: $db[12] ($db[13])");
    }
    @db = ();
    @db2 = ();
    close (fi);
}
# $id: xmms-weechat.pl,v 1.1 2006/05/23 00:50:10 linkz Exp $
