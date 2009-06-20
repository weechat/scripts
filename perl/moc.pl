##############################################################################
#                                                                            #
#                                MOC                                         #
#                                                                            #
# Perl script for WeeChat.                                                   #
#                                                                            #
# Show info about current song in moc                                        #
#                                                                            #
#                                                                            #
#                                                                            #
# Copyright (C) 2006 - 2009  Jiri Golembiovsky <golemj@gmail.com>            #
#                                                                            #
# This program is free software; you can redistribute it and/or              #
# modify it under the terms of the GNU General Public License                #
# as published by the Free Software Foundation; either version 2             #
# of the License, or (at your option) any later version.                     #
#                                                                            #
# This program is distributed in the hope that it will be useful,            #
# but WITHOUT ANY WARRANTY; without even the implied warranty of             #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
# GNU General Public License for more details.                               #
#                                                                            #
# You should have received a copy of the GNU General Public License          #
# along with this program; if not, write to the Free Software                #
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,                 #
# MA  02110-1301, USA.                                                       #
#                                                                            #
##############################################################################

weechat::register( "moc", "Jiri Golembiovsky", "0.5", "GPL",
  "Show info about current song in moc", "", "" );
weechat::hook_command(
  "moc", 
  "Show info about current song in moc",
  "[i|o|ot]",
  "To set another default output type than 'i' use: /set plugins.var.perl.moc.output_type\n" .
  "i   show info about current song (default parameter if no other is given)\n" .
  "o   print results to the current channel as /msg\n" .
  "ot  print results to the current channel as /me, this parameter overrides -o parameter\n" .
  "\n" .
  "To set output format use: /set plugins.var.perl.moc.output_format\n" .
  "%A - artist           %B - album\n" .
  "%F - file/stream name %H - stream name\n" .
  "%J - total time       %K - current time\n" .
  "%L - time left        %M - total sec\n" .
  "%N - current sec      %S - status\n" .
  "%T - title            %U - song title\n" .
  "%Y - bitrate          %Z - rate\n",
  "i|o|ot",
  "moc", "" );


if( weechat::config_get_plugin( "output_format" ) eq "" ) {
  weechat::config_set_plugin( "output_format", "is listening to %T ::: %H" );
}

if( weechat::config_get_plugin( "output_type" ) eq "" ) {
  weechat::config_set_plugin( "output_type", "i" );
}

sub info {
  my $i;
  my $res = "";
  my $sout = `mocp -i`;
  my @out = split( "\n", $sout );
  my $format = weechat::config_get_plugin( "output_format" );
  #if( length( $format ) == 0 ) { $format = "is listening to %T ::: %H"; }
  if( $#out < 2  ) { return ""; }
  for( $i = 0; $i <= $#out; $i++ ) {
    if( ( index( $out[$i], ' ' ) == -1 ) ||
        ( index( $out[$i], ' ' ) == ( length( $out[$i] ) - 1 ) )
    ) {
      $out[$i] = "";
    } else {
      $out[$i] = substr( $out[$i], index( $out[$i], ' ' ) + 1 );
    }
  }
  $i = 0;
  while( $i < length( $format ) ) {
    if( substr( $format, $i, 1 ) eq '%' ) {
      $i++;
      if( substr( $format, $i, 1 ) eq 'A' ) { $res = $res . $out[3]; }
      if( substr( $format, $i, 1 ) eq 'B' ) { $res = $res . $out[5]; }
      if( substr( $format, $i, 1 ) eq 'F' ) { $res = $res . $out[1]; }
      if( substr( $format, $i, 1 ) eq 'H' ) {
        if( index( $out[1], "://" ) > 0 ) {
          $res = $res . $out[1];
        } else {
          #$res = $res . substr( $out[1], rindex( $out[1], '/' ) + 1 );
        }
      }
      if( substr( $format, $i, 1 ) eq 'J' ) { $res = $res . $out[6]; }
      if( substr( $format, $i, 1 ) eq 'K' ) { $res = $res . $out[9]; }
      if( substr( $format, $i, 1 ) eq 'L' ) { $res = $res . $out[7]; }
      if( substr( $format, $i, 1 ) eq 'M' ) { $res = $res . $out[8]; }
      if( substr( $format, $i, 1 ) eq 'N' ) { $res = $res . $out[10]; }
      if( substr( $format, $i, 1 ) eq 'S' ) { $res = $res . $out[0]; }
      if( substr( $format, $i, 1 ) eq 'T' ) { $res = $res . $out[2]; }
      if( substr( $format, $i, 1 ) eq 'U' ) { $res = $res . $out[4]; }
      if( substr( $format, $i, 1 ) eq 'Y' ) { $res = $res . $out[11]; }
      if( substr( $format, $i, 1 ) eq 'Z' ) { $res = $res . $out[12]; }
    } else {
      $res = $res . substr( $format, $i, 1 );
    }
    $i++;
  }
  return $res;
}

sub moc {
  my $out;
  my $outType = weechat::config_get_plugin( "output_type" );
  if( length( $outType ) == 0 ) { $outType = 'i'; }
  if( length( $_[2] ) ) { $outType = $_[2]; }
  if( ( $outType ne 'i' ) && ( $outType ne 'o' ) && ( $outType ne 'ot' ) ) {
    weechat::print( $_[1], "Bad parameter or default output type" );
  }
  $out = info();
  if( $outType eq 'i' ) { weechat::print( $_[1], $out ); }
  if( $outType eq 'o' ) { weechat::command( $_[1], $out ); }
  if( $outType eq 'ot' ) { weechat::command( $_[1], "/me " . $out ); }
  return weechat::WEECHAT_RC_OK;
}
