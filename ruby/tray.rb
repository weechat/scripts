# Tray notifer plugin.
# Version 0.3
# Released under GNU GPL v2
# PhoeniX <leonid.phoenix@gmail.com>
#
# Changelog
# 0.3 - all message handlers are now optional (options handle_*)
#     - fix: check konch presence
#     - double click on tray icon raises konsole window (if weechat runs in konsole)
# 0.2 - tray icon
#     - tray icon tooltip
#     - tray icon tooltip templates
#     - tray icon reseting
#     - fully configurable via config file
# 0.1 - Initial version, was lost
# This script requires Konch (http://konch.kdex.org/)
# TODO: /tray help for help
require 'strscan'
require 'iconv'
require 'fileutils'

# reading config and default walues handling
def method_missing(name, *args, &block)
  if instance_variable_defined? "@#{name.to_s}"
    instance_variable_get "@#{name.to_s}"
  else
    val=if (Weechat.get_plugin_config(name.to_s).empty?) 
          then args*'' 
        else 
          Weechat.get_plugin_config(name.to_s)
        end
    instance_variable_set("@#{name.to_s}", val )
  end
end


$konchscript=<<EOS
#!/bin/bash
ID=$1
EVENT=$2
shift 2
PARMS=\"$@\"
function fifo
{ for fifo in ~/.weechat/weechat_fifo_*
    do
        echo -e "*/$@" >$fifo
    done
}

case $EVENT in
  init)
    echo 'popup Weechat tray plugin started'
  ;;
  click)
    fifo "tray reset"
  ;;
  dclick)
    fifo "tray toggle"
  ;;
  quit)
    rm $0
  ;;
esac
EOS

def weechat_init
  # registering
  Weechat.register "tray", "0.3", "deinit", "Tray notifer plugin."
  # handlers 
  Weechat.add_command_handler "tray", "tray","","reset|toggle", "", "reset|toggle"
  Weechat.add_message_handler "weechat_pv","on_query"     if handle_query("true")=="true"
  Weechat.add_message_handler "weechat_highlight","on_hl" if handle_highlight("true")=="true"
  Weechat.add_message_handler "privmsg","on_privmsg"      if handle_message("true")=="true"
  Weechat.add_message_handler "part",   "on_part"         if handle_part("true")=="true"
  Weechat.add_message_handler "quit",   "on_quit"         if handle_quit("true")=="true"
  Weechat.add_message_handler "join",   "on_join"         if handle_join("true")=="true"
  Weechat.add_keyboard_handler "on_kbd"
  #config && defaults
  message_template("%channel% :: <font color='#0095FF'>%nick%</font>: %msg%")
  message_action_template("%channel% :: <font color='#0095FF'>%nick%</font> %msg%")
  query_template("<font color='#EE82EE'>@%nick%</font>: %msg%")
  query_action_template("<font color='#EE82EE'>@%nick%</font> -> %msg%")
  highlight_template("%channel% :: <font color='#0095FF'>%nick%</font>: <font color='#CD2E2E'>%msg%</font>")
  highlight_action_template("%channel% :: <font color='#0095FF'>%nick%</font> -> <font color='#CD2E2E'>%msg%</font>")
  join_template("%channel% += <font color='#16A716'>%nick%</font>")
  part_template("%channel% -= <font color='#16A716'>%nick%</font>: %msg%")
  quit_template("&lt;&lt; <font color='#16A716'>%nick%</font>: %msg%")
  default_icon("terminal")
  logsize("20")
  
  $log=Array.new
  $arg=Hash.new
  $overlay=false
  $triggered=false
  
  # starting konch
  return Weechat::PLUGIN_RC_KO if `which konch`.empty? # there's no konch
  $konch=`konch --icon #{default_icon} 2>/dev/null`
  $konch.chomp!
  
  # giving new name (mouse menu header) and script
  `dcop #{$konch} Konch setName "WeeChat"`
  File.open("#{ENV['HOME']}/.weechat/konch", 'w'){|f| f<<$konchscript}
  FileUtils.chmod 0755, "#{ENV['HOME']}/.weechat/konch"
  `dcop #{$konch} Konch setScript #{ENV['HOME']}/.weechat/konch`
  
  # utf8 to locale converter
  enc=ENV['LANG'].include?('.') ? ENV['LANG'].split('.')[-1] : 'C'
  $converter = Iconv.new( enc +'//IGNORE', 'UTF-8')

  return Weechat::PLUGIN_RC_OK
end

def parseargs args
  hash=Hash.new
  #hash['nick'], hash['ident'], hash['host'], hash['msg_type'], hash['channel'], hash['msg']=args.scan(/:([^!]*)!([^@]*)@(\S*)\s(\S*)\s(\S*)\s:(.*)/)[0]
  ss=StringScanner.new(args)
  ss.pos=ss.pos+1
  hash['nick']=   ss.scan(/[^!]*/)
  ss.pos=ss.pos+1
  hash['ident']=  ss.scan(/[^@]*/)
  ss.pos=ss.pos+1
  hash['host']=   ss.scan(/\S*/)
  ss.pos=ss.pos+1
  hash['msg_type']=ss.scan(/\S*/)
  ss.pos=ss.pos+1
  case hash['msg_type']
    when "PRIVMSG"
      hash['channel']=ss.scan(/\S*/)
      ss.pos=ss.pos+2
      tail=ss.scan(/.*/)
      tail=tail.gsub /[\x01\x02\x03\x1f\x16\x0f]/, ''
      hash['action']=tail.include?("ACTION")
      hash['msg']=tail.sub /^ACTION/, ''
    when "QUIT"
      ss.pos=ss.pos+1
      hash['msg']=ss.scan(/.*/).gsub(/[\x01\x02\x03\x1f\x16\x0f]/, '')
    when "JOIN"
      ss.pos=ss.pos+1
      hash['channel']=ss.scan(/.*/)
    when "PART"
      hash['channel']=ss.scan(/\S*/)
      ss.pos=ss.pos+2
      hash['msg']=ss.scan(/.*/).gsub(/[\x01\x02\x03\x1f\x16\x0f]/, '')
  else
    File.open("#{ENV['HOME']}/.weechat/msg.log", 'a') {|f| f.puts args}
  end
  return hash
end

# checks, contains source defined in config highlights or not
def highlight?(source)
  Weechat.get_config('irc_highlight').each(',') do |entry|
    return true if source.include?(entry.gsub('*',''))
  end
  return false
end

# handles regular channel messages
def on_privmsg (server, args_src)
  $arg=parseargs args_src
  #skipping unregular messages
  return Weechat::PLUGIN_RC_OK if ( \
    #it's a query
    ($arg['channel']==Weechat.get_info("nick")) || \
    #it's a highlight
    ($arg['msg'].include?(Weechat.get_info("nick"))) || \
    highlight?($arg['msg']) 
    )
  if $arg['action']
    do_notify message_action_template, "setIcon openterm"
  else
    do_notify message_template, "overlay presence_online"
    $overlay=true
  end
  return Weechat::PLUGIN_RC_OK
end

# other handlers
def on_query (server, args_src)
  $arg=parseargs args_src
  if $arg['action']
    do_notify query_action_template, "blink 500", :popup => true
  else
    do_notify query_template, "blink 500", :popup => true
  end
  return Weechat::PLUGIN_RC_OK
end

def on_hl(server, args_src)
  $arg=parseargs args_src
  if $arg['action']
    do_notify highlight_action_template, "blink 500", :popup => true
  else
    do_notify highlight_template, "blink 500", :popup => true
  end
  return Weechat::PLUGIN_RC_OK
end

def on_join(server, args_src)
  $arg=parseargs args_src
  do_notify join_template, "setIcon openterm"
  return Weechat::PLUGIN_RC_OK
end
def on_part(server, args_src)
  $arg=parseargs args_src
  do_notify part_template, "setIcon openterm"
  return Weechat::PLUGIN_RC_OK
end
def on_quit(server, args_src)
  $arg=parseargs args_src
  do_notify quit_template, "setIcon openterm"
  return Weechat::PLUGIN_RC_OK
end

def do_notify(logline, command, options = {})
  # template expansion
  logline=logline.gsub(/%.*?%/){|key| $arg[key[1..-2]] }
  # removing dangerous shell symbols
  logline=logline.gsub("'", "").gsub('"','')
  # set encoding to locale to execute in a shell
  logline=$converter.iconv logline
  #last read line separator
  $log<< "<hr>" unless $triggered
  $log<<logline
  $log.shift while $log.size > logsize.to_i
  # make log a list and pass it to konch
  tooltip="<p><ul>"+$log.map{|l| "<li>"+l+"</li>\n"}.join+"</ul></p>"
  `dcop #{$konch} Konch setTooltip \'#{tooltip}\'`
  `dcop #{$konch} Konch #{command}`
  `dcop #{$konch} Konch overlay presence_online` if $overlay
  `dcop #{$konch} Konch passivePopup \'#{logline}\'` if ((!options[:popup].nil?) && (options[:popup]))
  $triggered=true
end

# reseting icon and tooltip log
def reset(arg=[])
  $log.delete "<hr>"
  # make log a list and pass it to konch
  tooltip="<p><ul>"+$log.map{|l| "<li>"+l+"</li>\n"}.join+"</ul></p>"
  `dcop #{$konch} Konch setTooltip \'#{tooltip}\'`
  `dcop #{$konch} Konch resetIcon`
  `dcop #{$konch} Konch setIcon #{default_icon}`
  $overlay=false
  $triggered=false
  return Weechat::PLUGIN_RC_OK
end

def on_kbd(a,b,c)
  return Weechat::PLUGIN_RC_OK unless $triggered
  reset
  return Weechat::PLUGIN_RC_OK
end

# raises konsole window, if running inside it
def toggle(arg=[])
  reset
  return unless ENV['KONSOLE_DCOP'].nil?
  konsole=ENV['KONSOLE_DCOP'].scan(/\((.*),/)
  `dcop #{konsole} konsole-mainwindow#1 hide`
  `dcop #{konsole} konsole-mainwindow#1 restore`
end

# set/list internal variables/settings
def set(argv)
  if argv.empty?
    instance_variables.sort.each{|var| var=var[1..-1]; Weechat.print_server var+" = "+ send(:"#{var}")}
  else
    instance_variable_set("@"+argv[0], argv.size<2 ? "" : argv[1]) 
  end
end

# calling a function, defined in this script, on /tray funcname
def tray(server,arg)
  arr=arg.split(' ')
  command=arr.shift
  if (respond_to?(command))
    send(:"#{command}", arr)
  else
    help
  end
  return Weechat::PLUGIN_RC_OK
end

# saving/deinitializing
def deinit
  instance_variables.each do |varname|
    Weechat.set_plugin_config(varname[1..-1], instance_variable_get(varname))
  end
  # shutting down konch
  `dcop #{$konch} Konch quit`
  return Weechat::PLUGIN_RC_OK
end
