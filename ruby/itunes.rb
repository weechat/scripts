SCRIPT_NAME = "itunes".freeze
SCRIPT_AUTHOR = "mdszy <mdszy@me.com>".freeze
SCRIPT_VERSION = "1.0".freeze
SCRIPT_LICENSE = "CC-BY-SA".freeze
DESCRIPTION = "An iTunes control / now playing script".freeze

COMMAND_NAME = "itunes"
COMMAND_DESCRIPTION = "Control iTunes and output the currently playing track"
COMMAND_ARGS = "[[np | nowplaying] [-out]] | [launch] | [next] | [prev] | [shuffle] | [play] | [pause]"
ARGS_DESCRIPTION = <<-EOF
[[np | nowplaying] [-out]]: Shows currently playing song. If used with the -out option, will output currently playing song to the active query as a message

Everything else, pretty obvious, they're used to control iTunes.
EOF
ARGS_COMPLETION = <<-EOF
EOF

def weechat_init
  Weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, DESCRIPTION, "", "")

  command_hook = Weechat.hook_command(COMMAND_NAME, COMMAND_DESCRIPTION, COMMAND_ARGS, ARGS_DESCRIPTION, ARGS_COMPLETION, "itunes_command", "")

  Weechat::WEECHAT_RC_OK
end

def itunes_command(data, buffer, args)
  args = args.split(' ')
  case args[0]
  when 'next'
    run_applescript('tell application "iTunes" to play next track', "false")
  when 'prev'
    run_applescript('tell application "iTunes" to play previous track', "false")
  when 'play', 'pause'
    run_applescript('tell application "iTunes" to playpause', "false")
  when 'np', 'nowplaying'
    output = "false"
    if args[1] == '-out'
      output = "true"
    end

    script = <<-EOF
tell application "iTunes"
  set the_title to get the name of the current track
  set the_artist to get the artist of the current track
  return the_title & " - " & the_artist
end tell
    EOF

    run_applescript(script, output)
  when 'launch'
    run_applescript('tell application "iTunes" to activate', "false")
  when 'shuffle'
    script = <<-EOF
tell application "iTunes"
	if shuffle of current playlist is true then
		set shuffle of current playlist to false
		return "Shuffle off."
	else
		set shuffle of current playlist to true
		return "Shuffle on."
	end if
end tell
    EOF
    run_applescript(script, "false")
  else
    Weechat.print(Weechat.current_buffer, "Unrecognized command")
  end

  return Weechat::WEECHAT_RC_OK
end

def run_applescript(applescript, output)
  Weechat.hook_process("echo '#{applescript}' | osascript", 20 * 1000, "run_applescript_callback", output)
  return Weechat::WEECHAT_RC_OK
end

def run_applescript_callback(data, command, rc, out, err)
  buffer = Weechat.current_buffer

  case data
  when "true"
    output = true
  when "false"
    output = false
  else
    output = false
  end

  if rc != 0
    Weechat.print(buffer, err)
  end

  if out != ""
    output ? Weechat.command(buffer, out) : Weechat.print(buffer, out)
  end

  return Weechat::WEECHAT_RC_OK
end
