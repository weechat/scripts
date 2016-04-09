/*
+Copyright (c) 2015 by installgen2 <gen2@kek.club>
+
+This program is free software: you can redistribute it and/or modify
+it under the terms of the GNU General Public License as
+published by the Free Software Foundation, either version 3 of the
+License, or (at your option) any later version.
+
+This program is distributed in the hope that it will be useful,
+but WITHOUT ANY WARRANTY; without even the implied warranty ofh
+MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
+GNU General Public License for more details.
+
+You should have received a copy of the GNU General Public License
+along with this program.  If not, see <http://www.gnu.org/licenses/>
+*/

weechat.register("autospurdo", "installgen2", "1.0", "GPL3", "Speak in spurdo", "", "");
weechat.hook_command("spurdosay", "Say message in spurdo", "", "", "", "spurdoSay", "");
weechat.hook_command("togglespurdo", "Toggle automatic spurdo conversion", "", "", "", "toggleSpurdo", "");
weechat.hook_command_run("/input return", "spurdoModifier", "");

function spurdoSay (data, buffer, args) {
	var message = toSpurdo(args);
	weechat.command("", "/say " + message)
	return weechat.WEECHAT_RC_OK;
}

var spurdoEnabled = false;
function spurdoModifier (data, buffer, command) {
	if (!spurdoEnabled || command != "/input return") return weechat.WEECHAT_RC_OK;

	text = weechat.buffer_get_string(buffer, "input");

	if (text[0] == "/") return weechat.WEECHAT_RC_OK;

	weechat.buffer_set(buffer, "input", toSpurdo(text))
	return weechat.WEECHAT_RC_OK;
}

function toggleSpurdo (data, buffer, args) {
	if (spurdoEnabled) {
		spurdoEnabled = false;
		weechat.print("", "Disabled automatic spurdo");
	} else {
		spurdoEnabled = true;
		weechat.print("", "Enabled automatic spurdo");
	}

	return weechat.WEECHAT_RC_OK;
}


// The following shit is from https://github.com/installgen2/libspurdo

// Return a random ebin face
var ebinFaces = [":D", ":DD", ":DDD", ":-D", ":-DD", "XD", "XXD", "XDD", "XXDD"];
function getEbinFace () {
	return ebinFaces[Math.floor(Math.random() * ebinFaces.length)];
}

// define replacements
var replacements = [
	["wh", "w"],
	["th", "d"],

	["af", "ab"],
	["ap", "ab"],
	["ca", "ga"],
	["ck", "gg"],
	["co", "go"],
	["ev", "eb"],
	["ex", "egz"],
	["et", "ed"],
	["iv", "ib"],
	["it", "id"],
	["ke", "ge"],
	["nt", "nd"],
	["op", "ob"],
	["ot", "od"],
	["po", "bo"],
	["pe", "be"],
	["pi", "bi"],
	["up", "ub"],
	["va", "ba"],

	["ck", "gg"],
	["cr", "gr"],
	["kn", "gn"],
	["lt", "ld"],
	["mm", "m"],
	["nt", "dn"],
	["pr", "br"],
	["ts", "dz"],
	["tr", "dr"],

	["bs", "bz"],
	["ds", "dz"],
	["es", "es"],
	["fs", "fz"],
	["gs", "gz"],
	[" is", " iz"],
	["ls", "lz"],
	["ms", "mz"],
	["ns", "nz"],
	["rs", "rz"],
	["ss", "sz"],
	["ts", "tz"],
	["us", "uz"],
	["ws", "wz"],
	["ys", "yz"],

	["alk", "olk"],
	["ing", "ign"],

	["ic", "ig"],
	["ng", "nk"],

	["kek", "geg"],
	["epic", "ebin"],
	["some", "sum"],
	["meme", "maymay"],
];

function toSpurdo (string) {
	// Convert to lowercase (TODO: add upercase handling)
	string = string.toLowerCase();

	// apply replacements
	replacements.forEach(function(filter) {
		var replaceFrom = new RegExp(filter[0], "gm"),
			replaceTo = filter[1];

		string = string.replace(replaceFrom, replaceTo);
	});

	// Replace "," and "." with ebin faces
	while (string.match(/\.|,(?=\s|$)/m)) {
		string = string.replace(/\.|,(?=\s|$)/m, " " + getEbinFace());
	}

	// append an ebin face if not found
	var ebinFaceFound = false;
	ebinFaces.forEach(function (face) {
		if (string.indexOf(face) != -1) {
			ebinFaceFound = true;
		}
	});

	if (!ebinFaceFound) {
		string += " " + getEbinFace();
	}

	// return spurdo'd text
	return string;
}
