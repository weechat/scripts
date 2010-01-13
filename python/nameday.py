# -*- coding: utf-8 -*-
#
# Copyright (c) 2003-2010 by FlashCode <flashcode@flashtux.org>
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

#
# Display name days in bar item and buffer.
# Currently, only french calendar is supported.
# (this script requires WeeChat 0.3.0 or newer)
#
# History:
#
# 2010-01-13, FlashCode <flashcode@flashtux.org>:
#     version 0.8: conversion to python (script renamed to nameday.py),
#                  conversion to WeeChat 0.3.0+
# 2007-08-10, FlashCode <flashcode@flashtux.org>:
#     version 0.7
# 2003-12-06, FlashCode <flashcode@flashtux.org>:
#     version 0.1: initial release (fete.pl)
#

import_ok = True

try:
    import weechat
except:
    print "This script must be run under WeeChat."
    print "Get WeeChat now at: http://www.weechat.org/"
    import_ok = False

import time, unicodedata
from datetime import date

SCRIPT_NAME    = "nameday"
SCRIPT_AUTHOR  = "FlashCode <flashcode@flashtux.org>"
SCRIPT_VERSION = "0.8"
SCRIPT_LICENSE = "GPL3"
SCRIPT_DESC    = "Display name days in bar item and buffer"

# script options
nameday_settings = {
    "country" : "fr", # country, only 'fr' (french) is currently available
    "days"    : "1",  # number of days after current one to display in bar item
}

nameday_item = ""
nameday_buffer = ""

namedays = {
    "fr": (
        # janvier
        ( '!Marie - JOUR de l\'AN', '&Basile', '!Geneviève', '&Odilon', '&Edouard',
          '&Mélaine', '&Raymond', '&Lucien', '!Alix', '&Guillaume', '&Paulin',
          '!Tatiana', '!Yvette', '!Nina', '&Rémi', '&Marcel', '!Roseline',
          '!Prisca', '&Marius', '&Sébastien', '!Agnès', '&Vincent', '&Barnard',
          '&François de Sales', '-Conversion de St Paul', '!Paule', '!Angèle',
          '&Thomas d\'Aquin', '&Gildas', '!Martine', '!Marcelle' ),
        # février
        ( '!Ella', '-Présentation', '&Blaise', '!Véronique', '!Agathe',
          '&Gaston', '!Eugénie', '!Jacqueline', '!Apolline', '&Arnaud',
          '-Notre-Dame de Lourdes', '&Félix', '!Béatrice', '&Valentin', '&Claude',
          '!Julienne', '&Alexis', '!Bernadette', '&Gabin', '!Aimée',
          '&Pierre Damien', '!Isabelle', '&Lazare', '&Modeste', '&Roméo', '&Nestor',
          '!Honorine', '&Romain', '&Auguste' ),
        # mars
        ( '&Aubin', '&Charles le Bon', '&Guénolé', '&Casimir', '&Olive', '&Colette',
          '!Félicité', '&Jean de Dieu', '!Françoise', '&Vivien', '!Rosine',
          '!Justine', '&Rodrigue', '!Mathilde', '!Louise de Marillac', '!Bénédicte',
          '&Patrice', '&Cyrille', '&Joseph', '&Herbert', '!Clémence', '!Léa',
          '&Victorien', '!Catherine de Suède', '-Annonciation', '!Larissa',
          '&Habib', '&Gontran', '!Gwladys', '&Amédée', '&Benjamin' ),
        # avril
        ( '&Hugues', '!Sandrine', '&Richard', '&Isodore', '!Irène', '&Marcellin',
          '&Jean-Baptiste de la Salle', '!Julie', '&Gautier', '&Fulbert',
          '&Stanislas', '&Jules', '!Ida', '&Maxime', '&Paterne',
          '&Benoît-Joseph Labre', '&Anicet', '&Parfait', '!Emma', '!Odette',
          '&Anselme', '&Alexandre', '&Georges', '&Fidèle', '&Marc', '!Alida',
          '!Zita', '!Valérie', '!Catherine de Sienne', '&Robert' ),
        # mai
        ( '&Jérémie - FETE du TRAVAIL', '&Boris', '&Philippe / Jacques', '&Sylvain',
          '!Judith', '!Prudence', '!Gisèle', '&Désiré - ANNIVERSAIRE 1945',
          '&Pacôme', '!Solange', '!Estelle', '&Achille', '!Rolande', '&Mathias',
          '!Denise', '&Honoré', '&Pascal', '&Eric', '&Yves', '&Bernardin',
          '&Constantin', '&Emile', '&Didier', '&Donatien', '!Sophie', '&Bérenger',
          '&Augustin', '&Germain', '&Aymar', '&Ferdinand', '-Visitation' ),
        # juin
        ( '&Justin', '!Blandine', '&Kévin', '!Clotilde', '&Igor', '&Norbert',
          '&Gilbert', '&Médard', '!Diane', '&Landry', '&Barnabé', '&Guy',
          '&Antoine de Padoue', '&Elisée', '!Germaine', '&Jean-François Régis',
          '&Hervé', '&Léonce', '&Romuald', '&Silvère', '&Rodolphe', '&Alban',
          '!Audrey', '&Jean-Baptiste', '&Salomon', '&Anthelme', '&Fernand',
          '&Irénée', '&Pierre / Paul', '&Martial' ),
        # juillet
        ( '&Thierry', '&Martinien', '&Thomas', '&Florent', '&Antoine', '!Mariette',
          '&Raoul', '&Thibaut', '!Amandine', '&Ulrich', '&Benoît', '&Olivier',
          '&Henri / Joël', '!Camille - FETE NATIONALE', '&Donald',
          '-N.D. du Mont Carmel', '!Charlotte', '&Frédéric', '&Arsène', '!Marina',
          '&Victor', '!Marie-Madeleine', '!Brigitte', '!Christine', '&Jacques',
          '&Anne', '!Nathalie', '&Samson', '!Marthe', '!Juliette',
          '&Ignace de Loyola' ),
        # août
        ( '&Alphonse', '&Julien', '!Lydie', '&Jean-Marie Vianney', '&Abel',
          '-Transfiguration', '&Gaëtan', '&Dominique', '&Amour', '&Laurent',
          '!Claire', '!Clarisse', '&Hippolyte', '&Evrard',
          '!Marie - ASSOMPTION', '&Armel', '&Hyacinthe', '!Hélène', '&Jean Eudes',
          '&Bernard', '&Christophe', '&Fabrice', '!Rose de Lima', '&Barthélémy',
          '&Louis', '!Natacha', '!Monique', '&Augustin', '!Sabine', '&Fiacre',
          '&Aristide' ),
        # septembre
        ( '&Gilles', '!Ingrid', '&Grégoire', '!Rosalie', '!Raïssa', '&Bertrand',
          '!Reine', '-Nativité de Marie', '&Alain', '!Inès', '&Adelphe',
          '&Apollinaire', '&Aimé', '-La Ste Croix', '&Roland', '!Edith', '&Renaud',
          '!Nadège', '!Emilie', '&Davy', '&Matthieu', '&Maurice', '&Constant',
          '!Thècle', '&Hermann', '&Côme / Damien', '&Vincent de Paul', '&Venceslas',
          '&Michel / Gabriel', '&Jérôme' ),
        # octobre
        ( '!Thérèse de l\'Enfant Jésus', '&Léger', '&Gérard', '&François d\'Assise',
          '!Fleur', '&Bruno', '&Serge', '!Pélagie', '&Denis', '&Ghislain', '&Firmin',
          '&Wilfried', '&Géraud', '&Juste', '!Thérèse d\'Avila', '!Edwige',
          '&Baudouin', '&Luc', '&René', '!Adeline', '!Céline', '!Elodie',
          '&Jean de Capistran', '&Florentin', '&Crépin', '&Dimitri', '!Emeline',
          '&Simon / Jude', '&Narcisse', '!Bienvenue', '&Quentin' ),
        # novembre
        ( '&Harold - TOUSSAINT', '-Défunts', '&Hubert', '&Charles', '!Sylvie',
          '!Bertille', '!Carine', '&Geoffroy', '&Théodore', '&Léon',
          '&Martin - ARMISTICE 1918', '&Christian', '&Brice', '&Sidoine', '&Albert',
          '!Marguerite', '!Elisabeth', '!Aude', '&Tanguy', '&Edmond',
          '-Présentation de Marie', '!Cécile', '&Clément', '!Flora', '!Catherine',
          '!Delphine', '&Séverin', '&Jacques de la Marche', '&Saturnin', '&André' ),
        # décembre
        ( '!Florence', '!Viviane', '&Xavier', '!Barbara', '&Gérald', '&Nicolas',
          '&Ambroise', '-Immaculée Conception', '&Pierre Fourier', '&Romaric',
          '&Daniel', '!Jeanne de Chantal', '!Lucie', '!Odile', '!Ninon', '!Alice',
          '&Gaël', '&Gatien', '&Urbain', '&Abraham', '&Pierre Canisius',
          '!Françoise-Xavier', '&Armand', '!Adèle', '&Emmanuel - NOEL', '&Etienne',
          '&Jean', '-Sts Innocents', '&David', '&Roger', '&Sylvestre' ),
        )
    }

nameday_i18n = {
    "fr": { "m"        : "St ",
            "f"        : "Ste ",
            },
    }

def nameday_get_country():
    """ Return country. """
    global namedays
    country = weechat.config_get_plugin("country")
    if not namedays[country]:
        country = "fr"
    return country

def nameday_transcode(name, add_prefix=True):
    global nameday_i18n
    country = nameday_get_country()
    if name.startswith('&'):
        if add_prefix:
            name = "%s%s" % (nameday_i18n[country]["m"], name[1:])
        else:
            name = name[1:]
    elif name.startswith('!'):
        if add_prefix:
            name = "%s%s" % (nameday_i18n[country]["f"], name[1:])
        else:
            name = name[1:]
    elif name.startswith('-'):
        name = name[1:]
    return name

def nameday_get_month_day(month, day):
    """ Get name day for given day/month. """
    global namedays
    try:
        country = nameday_get_country()
        name = namedays[country][month][day]
        return nameday_transcode(name)
    except:
        return ""

def nameday_get_date(name_date):
    """ Get name day for given date. """
    return nameday_get_month_day(name_date.month - 1, name_date.day - 1)

def nameday_completion_namedays_cb(data, completion_item, buffer, completion):
    """ Complete with name days, for command '/nameday'. """
    global namedays
    country = nameday_get_country()
    for names in namedays[country]:
        for name in names:
            name2 = nameday_transcode(name, False)
            weechat.hook_completion_list_add(completion,
                                             name2,
                                             0, weechat.WEECHAT_LIST_POS_SORT)
            weechat.hook_completion_list_add(completion,
                                             unicodedata.normalize('NFKD', unicode(name2, "UTF-8")).encode('ASCII', 'ignore'),
                                             0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def nameday_buffer_input_cb(data, buffer, input_data):
    if input_data.lower() == "q":
        weechat.buffer_close(buffer)
    return weechat.WEECHAT_RC_OK

def nameday_buffer_close_cb(data, buffer):
    """ Callback called when buffer is closed. """
    global nameday_buffer
    nameday_buffer = ""
    return weechat.WEECHAT_RC_OK

def nameday_display_list(buffer):
    """ Display list of name days in buffer. """
    global namedays
    country = nameday_get_country()
    today = date.today()
    month = 0
    while month < len(namedays[country]):
        day = 0
        while day < len(namedays[country][month]):
            color = ""
            if today.month - 1 == month and today.day - 1 == day:
                color = weechat.color("yellow")
            weechat.prnt(buffer, "%s%02d/%02d  %s" % (color,
                                                      (day + 1), (month + 1),
                                                      nameday_get_month_day(month, day)))
            day += 1
        month += 1

def nameday_list():
    """" Open buffer and display list of name days. """
    global nameday_buffer
    if nameday_buffer:
        weechat.buffer_set(nameday_buffer, "display", "1")
    else:
        nameday_buffer = weechat.buffer_search("python", "nameday");
        if not nameday_buffer:
            nameday_buffer = weechat.buffer_new("nameday", "nameday_buffer_input_cb", "",
                                                "nameday_buffer_close_cb", "");
        if nameday_buffer:
            weechat.buffer_set(nameday_buffer, "localvar_set_no_log", "1")
            weechat.buffer_set(nameday_buffer, "time_for_each_line", "0")
            weechat.buffer_set(nameday_buffer, "display", "1")
            weechat.buffer_set(nameday_buffer, "title", "Name days  |  Commands: list, listfull")
            nameday_display_list(nameday_buffer)

def nameday_print(days):
    """ Print name day for today and option N days in future. """
    global nameday_i18n
    country = nameday_get_country()
    today = date.today()
    current_time = time.time()
    string = "%02d/%02d: %s" % (today.day, today.month, nameday_get_date(today))
    if days < 0:
        days = 0
    elif days > 50:
        days = 50
    if days > 0:
        string += " ("
        for i in range(1, days + 1):
            if i > 1:
                string += ", "
            date2 = date.fromtimestamp(current_time + ((3600 * 24) * i))
            string += "%02d/%02d: %s" % (date2.day, date2.month, nameday_get_date(date2))
        string += ")"
    weechat.prnt("", string)

def nameday_search(name):
    """ Search a feast. """
    global namedays
    user_nameday = unicodedata.normalize('NFKD', unicode(name, "UTF-8")).encode('ASCII', 'ignore').lower()
    country = nameday_get_country()
    month = 0
    while month < len(namedays[country]):
        day = 0
        while day < len(namedays[country][month]):
            nameday = unicodedata.normalize('NFKD', unicode(namedays[country][month][day], "UTF-8")).encode('ASCII', 'ignore')
            if (nameday.lower().find(user_nameday) >= 0):
                weechat.prnt("", "%02d/%02d: %s" % ((day + 1), (month + 1),
                                                    nameday_get_month_day(month, day)))
            day += 1
        month += 1

def nameday_cmd_cb(data, buffer, args):
    """ Command /nameday. """
    if args:
        if args == "*":
            nameday_list()
        elif args.isdigit():
            nameday_print(int(args))
        elif args.find("/") >= 0:
            pos = args.find("/")
            if pos > 0:
                day = int(args[:pos])
                month = int(args[pos+1:])
                name = nameday_get_month_day(month - 1, day - 1)
                if name != "":
                    weechat.prnt("", "%02d/%02d: %s" % (day, month, name))
        else:
            nameday_search(args)
    else:
        nameday_print(1)
    return weechat.WEECHAT_RC_OK

def nameday_item_cb(data, buffer, args):
    """ Callback for building nameday item. """
    global nameday_item
    return nameday_item

def nameday_build_item():
    global nameday_item
    today = date.today()
    nameday_item = "%s" % nameday_get_date(today)
    days = 0
    try:
        days = int(weechat.config_get_plugin("days"))
    except:
        days = 0
    if days < 0:
        days = 0
    if days > 10:
        days = 10
    if days > 0:
        nameday_item += " ("
        current_time = time.time()
        for i in range(1, days + 1):
            if i > 1:
                nameday_item += ", "
            date2 = date.fromtimestamp(current_time + ((3600 * 24) * i))
            nameday_item += "%s" % nameday_get_date(date2)
        nameday_item += ")"
    return nameday_item

def nameday_timer_cb(data, remaining_calls):
    """ Called each day at midnight to change item content. """
    nameday_build_item()
    weechat.bar_item_update("nameday")
    return weechat.WEECHAT_RC_OK

def nameday_config_cb(data, option, value):
    nameday_build_item()
    weechat.bar_item_update("nameday")
    return weechat.WEECHAT_RC_OK

if __name__ == "__main__" and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        "", ""):
        # set default settings
        for option, default_value in nameday_settings.iteritems():
            if not weechat.config_is_set_plugin(option):
                weechat.config_set_plugin(option, default_value)
        # new command
        weechat.hook_completion("namedays", "list of name days",
                                "nameday_completion_namedays_cb", "")
        weechat.hook_command("nameday",
                             "Display name days",
                             "[* | number | date | name]",
                             "     *: display list of name days in a new buffer\n"
                             "number: display name day for today and <number> days in future\n"
                             "  date: display name day for this date, format is day/month (for example: 31/01)\n"
                             "  name: display date for this name\n\n"
                             "A bar item \"nameday\" can be used in a bar.\n\n"
                             "Examples:\n"
                             "  /nameday *      display list of name days in a new buffer\n"
                             "  /nameday        display name day for today and tomorrow\n"
                             "  /nameday 2      display name day for today, tomorrow, and after tomorrow\n"
                             "  /nameday 31/01  display name day for january, 31\n"
                             "  /nameday roger  display day for name \"roger\"",
                             "*|%(namedays)", "nameday_cmd_cb", "")
        # new item
        nameday_build_item()
        weechat.bar_item_new("nameday", "nameday_item_cb", "")
        # timer
        weechat.hook_timer(3600 * 24 * 1000, 3600 * 24, 0, "nameday_timer_cb", "")
        # config
        weechat.hook_config("plugins.var.python." + SCRIPT_NAME + ".*", "nameday_config_cb", "")
