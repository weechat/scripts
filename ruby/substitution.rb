# -*- coding: utf-8 -*-
=begin
substitution.rb, weechat script that substitutes strings in your text
Copyright (C) 2013  Samuel Laverdière <sam113101@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see [http://www.gnu.org/licenses/].
=end

@script_desc = <<-EOD
Substitution allows you to substitute everything you want for anything you want, right before your text is sent! \
It's useful if you want to add coloring to some words, to replace abbreviations, add hard-to-type smileys, etc. \
Substitution doesn't check if a string is part of a word or is a word on its own, so if you add substitution strings \
that are too short, you might run into problems. The option general_rule is there to help. It's an expression \
containing %s which indicates how your substitutions should look. With ":%s:" (quotes not part of the expression) as \
a general rule, :str: would be substituted for its corresponding text, while str alone would not. You can set your \
substitutions to not follow the general rule if you want to. Having an empty string as a general rule will disable it \
for all substitutions.
EOD

@arguments_desc = <<-EOD
list: This will list all of your substitutions, this is the default (when you don't pass anything to the command).

add: <name> will be replaced by <text>. You can set <obey_general_rule> to false if you don't want the substitution \
to obey the general rule, whatever it might be. add will also replace a substitution if it already exists. If you \
want to use spaces, escape them with \\. For example, "/substitution add this\\ is\\ a\\ name with\\ spaces" would \
replace every occurrence of "this is a name" with "with spaces". Confusing, I know!

del: Deletes the substitution matching <name>.
EOD

def weechat_init
  Weechat.register('substitution', 'sam113101', '0.0.1', 'GPL3',
                   'Substitute strings in your messages before they are sent.', '', '')
  @config_file = Weechat.info_get('weechat_dir', '') + Weechat.info_get('dir_separator', '') + 'substitutions.bin'
  load_config
  @default_options = {
    'general_rule' => ''
  }

  @default_options.each do |key, value|
    if Weechat.config_is_set_plugin(key) == 0
      Weechat.config_set_plugin(key, value)
    end
  end
  @general_rule = Weechat.config_get_plugin('general_rule')


  Weechat.hook_command('substitution', @script_desc, 'add name text [obey_general_rule=true] || del name || [list]',
                       @arguments_desc, 'list || add || del %(substitutions)', 'command_callback', '')
  Weechat.hook_modifier('input_text_for_buffer', 'sendtext_callback', '')
  Weechat.hook_config('plugins.var.ruby.substitution.general_rule', 'config_callback', '')
  Weechat.hook_completion('substitutions', '', 'completion_callback', '')
  return Weechat::WEECHAT_RC_OK
end

def with_rule(str)
  if @general_rule['%s']
    @general_rule.sub('%s', str)
  else
    str
  end
end

def config_callback(data, option, value)
  # general_rule is the only option right now
  @general_rule = value
end

def command_callback(data, buffer, arg_str)
  action, *args = arg_str.split(/(?<!\\) /)
  args.each { |a| a.gsub!('\ ', ' ') }

  case action
  when 'list', nil
    if @substitutions.empty?
      Weechat.print('', 'You don\'t have any substitution!')
    else
      Weechat.print('', @substitutions.count.to_s + ' substitution(s):')
      @substitutions.each do |key, value|
        text = "subs\t" + key
        if value[:obey_general_rule]
          text << " %s(#{with_rule(key)})%s" % [Weechat.color('darkgray'), Weechat.color('reset')]
        end
        colored_text = Weechat.hook_modifier_exec('irc_color_decode', '1', value[:text])
        Weechat.print('', "#{text} %s=>%s #{colored_text}" % [Weechat.color('green'), Weechat.color('reset')])
      end
    end

  when 'add'
    return Weechat::WEECHAT_RC_ERROR if args.length < 2
    @substitutions[args[0]] = { text: args[1],
                               obey_general_rule: args.length >= 3 && args[2] == 'false' ? false : true }
    update_config
    Weechat.print('', 'Substitution added!')

  when 'del'
    return Weechat::WEECHAT_RC_ERROR if args.length < 1
    if @substitutions.has_key?(args[0])
      @substitutions.delete(args[0])
      update_config
      Weechat.print('', 'Substitution deleted!')
    else
      Weechat.print('', 'Never seen that before. Are you sure it exists?')
    end

  else
    return Weechat::WEECHAT_RC_ERROR
  end

  return Weechat::WEECHAT_RC_OK
end

def sendtext_callback(data, modifier, modifier_data, text)
  return text if Weechat.string_is_command_char(text) == 1
  hash = {}
  @substitutions.each { |k, v| hash[v[:obey_general_rule] ? with_rule(k) : k] = v[:text] }
  return text.gsub(Regexp.union(hash.keys.sort_by { |word| word.length }.reverse), hash)
end

def update_config
  File.open(@config_file, 'w+b') do |file|
    file.print Marshal.dump(@substitutions)
  end
end

def load_config
  if File.exists?(@config_file)
    @substitutions = Marshal.load(File.read(@config_file))
  else
    @substitutions = {}
  end
end

def completion_callback(data, completion_name, buffer, completion)
  # there's only one completion item at the moment
  @substitutions.each_key do |name|
    Weechat.hook_completion_list_add(completion, name, 0, Weechat::WEECHAT_LIST_POS_SORT)
  end
  Weechat::WEECHAT_RC_OK
end
