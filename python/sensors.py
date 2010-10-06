# *--coding: utf8--*
#Copyright (c) 2010 by 0x1cedd1ce <0x1cedd1ce@freeunix.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# This script needs sensors. sensord must be running.
# A weechat plugin to display sensors data

import weechat, re

if weechat.register('sensors', '0x1cedd1ce', '1.0', 'GPL3', 'Display sensors data', '', ''):
    weechat.hook_command(
        'sensors', 
        'Display sensors data',
        '[CPU|MB|SB|NB|OPT]', 
        'CPU : Processor\nMB : Motherboard\nSB : Southbridge\nNB : Northbridge\nOPT : Optional Sensors',
        'CPU|MB|SB|NB|OPT',
        'show_data', 
        '')

functions = {'CPU': '"CPU Temp"', 'MB': '"MB Temp"', 'SB': '"SB Temp"', 'NB': '"NB Temp"', 'OPT': '-e "OPT_FAN. Temp"'}

lines = []
out_buffer = ''
out = False

def make_output(line):
    if line != '':
        #weechat.prnt('', line)
        data = re.match(r'(\w+) Temperature:\s+.(\d+\.?\d?)°C\s+\(high = .(\d+\.?\d?)°C, crit = .(\d+\.?\d?)°C\)', line)
        if len(data.groups()) == 4:
            (tag, cur_temp, high_temp, crit_temp) = data.groups()
            if out:
                weechat.command(out_buffer, tag)
                weechat.command(out_buffer, '//—\\__________________________________________________________________________________________________')
            else:
                weechat.prnt(out_buffer, tag)
                weechat.prnt(out_buffer, '/—\\__________________________________________________________________________________________________')
            if out:
                if float(cur_temp) < float(high_temp):
                    color = u'\u00033,3'
                elif float(cur_temp) < float(crit_temp):
                    color = u'\u00038,8'
                else:
                    color = u'\u00034,4'
            else:
                if float(cur_temp) < float(high_temp):
                    color = weechat.color("green,green")
                elif float(cur_temp) < float(crit_temp):
                    color = weechat.color("yellow,yellow")
                else:
                    color = weechat.color("red,red")
            skala = ''
            scale = 100 / float(crit_temp)
            if high_temp[0:2] != crit_temp[0:2]:
                for x in range(round(float(high_temp) * scale)):
                    skala += ' '
            skala += high_temp[0:2]
            for x in range(100 - len(skala)):
                skala += ' '
            skala += crit_temp[0:2]
            bar = ''
            i = 0
            for x in range(100):
                if x > (float(cur_temp) * scale):
                    break
                elif x < 2:
                    bar += ' '
                elif x == 2:
                    if out:
                        bar += u' \u001f'
                    else:
                        bar += weechat.color('underline')
                else:
                    bar += '#'
            if out:
                normal_color = u'\u000f'
                if float(cur_temp) >= float(crit_temp):
                    bar2 = u'\u001f\u00030,4 ' + cur_temp + normal_color
                else:
                    bar2 = u'\u001f' + cur_temp
                    for x in range(100 - len(bar) - len(bar2) + 2*len(u'\u001f')):
                        bar2 += ' '
                    bar2 += u'\u000f'
            else:
                normal_color = weechat.color('chat')
                if float(cur_temp) >= float(crit_temp):
                    bar2 = weechat.color('white,red') + cur_temp + normal_color
                else:
                    bar2 = weechat.color('underline') + cur_temp
                    for x in range(100 - len(bar) - len(bar2) + 2*len(weechat.color('underline'))):
                        bar2 += ' '
                    bar2 += weechat.color('-underline')
            if out:
                weechat.command(out_buffer, '|{0}{1}{2}{3}{2}|'.format(color, bar, normal_color, bar2))
                weechat.command(out_buffer, '\\—/{0}'.format(skala[3:]))
            else:
                weechat.prnt(out_buffer, '|{0}{1}{2}{3}{2}|'.format(color, bar, normal_color, bar2))
                weechat.prnt(out_buffer, '\\—/{0}'.format(skala[3:]))
    return weechat.WEECHAT_RC_OK

def callback(data, command, rc, stdout, stderr):
    global lines
    if stdout != '':
        lines += stdout.splitlines()
    if int(rc) >= 0:
        for x in lines:
            make_output(x)
    return weechat.WEECHAT_RC_OK
def show_data(data, buffer, args):
    global lines
    global out_buffer
    global out
    out_buffer = buffer
    lines = []
    largs = args.split()
    if len(largs) == 1:
        if largs[0] == '-o':
            grep_expr = 'Temp'
            out = True
        else:
            grep_expr = functions.get(largs[0].upper(), 'Temp')
            out = False
    elif len(largs) == 2 and largs[0] == '-o':
        out = True
        grep_expr = functions.get(largs[1].upper(), 'Temp')
    else:
        grep_expr = 'Temp'
        out = False
    weechat.hook_process('sensors | grep {0}'.format(grep_expr), 10000, 'callback', 'Temp')
    return weechat.WEECHAT_RC_OK

