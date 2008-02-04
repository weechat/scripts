# NickServ identifer plugin
# Version 0.1
# Released under GNU GPL v2
# PhoeniX <leonid.phoenix@gmail.com>
def weechat_init
  Weechat.register "nickserv", "0.1", "deinit", "NickServ identifer plugin."
  Weechat.add_command_handler "nickserv", "nickserv","","a|d|l|u|help", "", "a|d|l|u|help"
  Weechat.add_message_handler "notice", "on_notice"
  #initialize rules
  $ruleset=Array.new
  i=0
  while !(rule_str=Weechat.get_plugin_config("rule"+i.to_s)).empty?
    a rule_str.split(' ')
    i+=1
  end
  return Weechat::PLUGIN_RC_OK
end

def on_notice(server, args)
  #get mask, nick and messae from notice
  mask=args.split(':')[1].split(' ')[0]
  nick=args.split(':')[1].split(' ')[2]
  message=args.split(':')[2]
  #find matching rule and execute action
  $ruleset\
    .find_all{|row| !(mask=~Regexp.new(row[:mask])).nil?}\
    .find_all{|row| !(nick=~Regexp.new(row[:nick])).nil?}\
    .find_all{|row| !(message=~Regexp.new(row[:message])).nil?}\
    .each{|row| Weechat.command row[:action]}
  return Weechat::PLUGIN_RC_OK
end

#add
def a(argv)
  if argv.size<3
    help
    return nil
  end
  $ruleset.push({:mask => argv.shift , :message => argv.shift, :nick => argv.shift , :action => argv*' '})
end
#list
def l(argv)
  $ruleset.each_index{|i| Weechat.print_server "#{i}\t| #{$ruleset[i][:mask]} #{$ruleset[i][:message]} #{$ruleset[i][:nick]} #{$ruleset[i][:action]}"}
end
#delete
def d(argv)
  if(argv.size==1)
    $ruleset.delete_at(argv[0].to_s)
  else
    help
  end
end
#update
def u(argv)
  if argv.size<4
    help
    return nil
  end
  index=argv.shift.to_i
  $ruleset[index]={:mask => argv.shift , :message => argv.shift, :nick => argv.shift , :action => argv*' '}
end

def help(argv)
  helpmessage=<<EOM
  available commands are:
  a RULE - add a rule
  d NUM  - delete NUM'th RULE
  l      - list rules
  u NUM RULE - update  NUM'th rule

  where RULE is MASK MESSAGE NICK COMMAND
  where MASK, MESSAGE and NICK are singleword regexp
  and COMMAND is some weechat command
  e.g.
  /nichserv a NickServ!service@RusNet IDENTIFY PhoeniX /quote NickServ IDENTIFY pa$$word
EOM
  Weechat.print_server helpmessage
  return Weechat::PLUGIN_RC_OK
end

#calling a function, defined in this script, on /nickserv funcname argv
def nickserv(server,arg)
  arr=arg.split(' ')
  command=arr.shift
  if (respond_to?(command))
    send(:"#{command}", arr)
  else
    help
  end
  return Weechat::PLUGIN_RC_OK
end

def deinit
  #saving rules
  $ruleset.each_index{|i| Weechat.set_plugin_config("Rule"+i.to_s, "#{$ruleset[i][:mask]} #{$ruleset[i][:message]} #{$ruleset[i][:nick]} #{$ruleset[i][:action]}")}
  return Weechat::PLUGIN_RC_OK
end
