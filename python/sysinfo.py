#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#                    Version 2, December 2004
#
# Copyright (C) 2026 Paul
#
# Everyone is permitted to copy and distribute verbatim or modified
# copies of this license document, and changing it is allowed as long
# as the name is changed.
#
#            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
#   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION
#
#  0. You just DO WHAT THE FUCK YOU WANT TO.

import weechat
import platform
import os

# Register the plugin within WeeChat
SCRIPT_NAME    = "sysinfo"
SCRIPT_AUTHOR  = "wigums"
SCRIPT_VERSION = "1.2"
SCRIPT_LICENSE = "WTFPL"
SCRIPT_DESC    = "Displays system specifications including accurate RAM splits in the current channel"

if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION, SCRIPT_LICENSE, SCRIPT_DESC, "", ""):
    # Register the custom /sysinfo command
    weechat.hook_command(
        "sysinfo",
        "Send system specifications to the current channel",
        "",  
        "Displays OS version, Kernel, CPU, and RAM allocation info.",
        "",  
        "sysinfo_cb", 
        ""
    )

def get_slackware_version():
    """Reads the exact version string from /etc/slackware-version."""
    try:
        if os.path.exists("/etc/slackware-version"):
            with open("/etc/slackware-version", "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return "Slackware"

def get_mem_info():
    """Parses /proc/meminfo to calculate Total, Used, and Available system memory."""
    try:
        mem_stats = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].replace(':', '')
                    mem_stats[key] = int(parts[1]) # values are in kB
        
        if 'MemTotal' in mem_stats and 'MemAvailable' in mem_stats:
            # Calculate used memory cleanly (Total - Available) to ignore cache bloat
            total_gb = mem_stats['MemTotal'] / 1024 / 1024
            avail_gb = mem_stats['MemAvailable'] / 1024 / 1024
            used_gb  = total_gb - avail_gb
            
            return f"{round(used_gb, 2)} GB / {round(total_gb, 2)} GB (Free: {round(avail_gb, 2)} GB)"
    except Exception:
        return "Unknown RAM"
    return "Unknown RAM"

def get_cpu_info():
    """Parses /proc/cpuinfo to get a clean model name string."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if 'model name' in line:
                    return line.split(':', 1)[1].strip()
    except Exception:
        return platform.processor()
    return platform.processor()

def sysinfo_cb(data, buffer, args):
    """Callback function executed when /sysinfo is typed."""
    # Gather specs using our helper functions
    distro = get_slackware_version()
    kernel = platform.release()
    arch   = platform.machine()
    cpu    = get_cpu_info()
    ram    = get_mem_info()
    
    # Construct the output line
    output = f"💻 \x02[SysInfo]\x02 OS: {distro} {arch} | Kernel: {kernel} | CPU: {cpu} | RAM: {ram}"
    
    # Send the output string straight down the active pipe of the current window
    weechat.command(buffer, f"/say {output}")
    
    return weechat.WEECHAT_RC_OK
