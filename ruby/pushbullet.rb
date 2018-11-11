# author: Olivier 'yazgoo' Abdesselam
# license: MIT
# home repository: https://github.com/yazgoo/weechat-pushbullet

require 'rubygems'
require 'presbeus'

$presbeus = Presbeus.new(false)

def send_sms(b, command, rc, out, err)
  Weechat.print(b, ">\t#{out}")
  return Weechat::WEECHAT_RC_OK
end

def buffer_input_cb(data, b, input_data)
  device = Weechat.buffer_get_string(b, "localvar_device")
  req = $presbeus.send_sms device, data, input_data
  args = h(req).merge({"postfields" => req[:payload].to_s, "post" => 1})
  Weechat.print(b, ">\t#{input_data}")
  Weechat.hook_process_hashtable(
    "url:#{req[:url]}", args, 120 * 1000, "send_sms", b)
  return Weechat::WEECHAT_RC_OK
end

def buffer_close_cb(data, buffer)
  return Weechat::WEECHAT_RC_OK
end

def load_thread(b, command, rc, out, err)
  JSON.parse(out)["thread"].reverse.each do |c|
    Weechat.print(b, "#{c["direction"] == "outgoing" ? ">" : "<"}\t#{c["body"]}")
  end
  return Weechat::WEECHAT_RC_OK
end

def reload_thread(data, b, args)
  address = Weechat.buffer_get_string(b, "localvar_address")
  device = Weechat.buffer_get_string(b, "localvar_device")
  req = $presbeus.get_v2("permanents/#{device}_thread_#{address}")
  Weechat.hook_process_hashtable(
    "url:#{req[:url]}", h(req), 120 * 1000, "load_thread", b)
  return Weechat::WEECHAT_RC_OK
end

def load_threads(device, command, rc, out, err)
  Weechat.print('', "loading device #{device}")
  JSON.parse(out)["threads"].map{|x| Presbeus.parse_thread(x)}.each do |address, name|
    Weechat.print('', "creating buffer for #{device} #{address} #{name}")
    b = Weechat.buffer_new(name, 'buffer_input_cb', name, 'buffer_close_cb', name)
    Weechat.buffer_set(b, "localvar_set_address", address)
    Weechat.buffer_set(b, "localvar_set_device", device)
    reload_thread(nil, b, nil)
  end
  return Weechat::WEECHAT_RC_OK
end

def get_devices(data, command, rc, out, err)
  Weechat.print('', "devices:")
  JSON.parse(out)["devices"].each { |d|  Weechat.print('', "#{d["iden"]} : #{d["model"]}") }
  return Weechat::WEECHAT_RC_OK
end

def h req
  {"httpheader" => req[:headers].map { |a, b| "#{a}:#{b}" }.join("\n")}
end

def load_device(data, b, device)
  Weechat.print('', "loading treads for device #{$presbeus.default_device}")
  req = $presbeus.get_v2("permanents/#{device}_threads")
  Weechat.hook_process_hashtable(
    "url:#{req[:url]}", h(req), 120 * 1000, "load_threads", device)
end

def weechat_init
  Weechat.register('pushbullet',
                   'PushBullet', '1.0', 'GPL3', 'Pushbullet', '', '')
  Weechat.hook_command("pb_r", "reload pushbullet tread", "", "", "", "reload_thread", "")
  Weechat.hook_command("pb_d", "load device", "", "", "", "load_device", "")
  req = $presbeus.get_v2("devices")
  Weechat.hook_process_hashtable(
    "url:#{req[:url]}", h(req), 120 * 1000, "get_devices", "")
  Weechat.print('', "launch '/pb_d <device_id>' to load device")
  if !$presbeus.default_device.nil?
    load_device(nil, nil, $presbeus.default_device)
  end
  return Weechat::WEECHAT_RC_OK
end
