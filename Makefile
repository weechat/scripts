#
# SPDX-FileCopyrightText: 2021-2025 Sébastien Helleu <flashcode@flashtux.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later
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
#

CHECKER ?= weechat-script-lint

.PHONY: all check

all: check

# this target will be removed once the ignored scripts are fixed
partial-check:
	"$(CHECKER)" --ignore-files autosort.py,gateway_rename.scm,ircrypt.py,latex_unicode.py,menu.pl --recursive .

check:
	"$(CHECKER)" --recursive .
