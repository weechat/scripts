#
# Copyright (C) 2021 Sébastien Helleu <flashcode@flashtux.org>
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

.PHONY: all check flake8 pylint

all: lint check

lint: flake8 pylint mypy

flake8:
	flake8 ./tools/check_scripts.py --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 ./tools/check_scripts.py --count --exit-zero --max-complexity=10 --statistics

pylint:
	pylint ./tools/check_scripts.py

mypy:
	mypy ./tools/check_scripts.py

# this target will be removed once the ignored scripts are fixed
partial-check:
	./tools/check_scripts.py -i announce_url_title.py,country.py,gateway_rename.scm,inotify.py,menu.pl,notifo.py,weather.py,wtwitter.py -r .

check:
	./tools/check_scripts.py -r .
