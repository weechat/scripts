# -*- coding: utf-8 -*-
#
# Copyright (C) 2003-2012 Sebastien Helleu <flashcode@flashtux.org>
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
# 2012-02-02, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.3: add option "reminder"
# 2012-01-03, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.2: make script compatible with Python 3.x
# 2011-10-30, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.1: fix colors in output of /nameday
# 2011-05-06, Sebastien Helleu <flashcode@flashtux.org>:
#     version 1.0: add some missing names and color based on gender
# 2010-01-14, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.9: add color options and options to display dates in bar item
# 2010-01-13, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.8: conversion to python (script renamed to nameday.py),
#                  conversion to WeeChat 0.3.0+
# 2007-08-10, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.7
# 2003-12-06, Sebastien Helleu <flashcode@flashtux.org>:
#     version 0.1: initial release (fete.pl)
#

SCRIPT_NAME    = 'nameday'
SCRIPT_AUTHOR  = 'Sebastien Helleu <flashcode@flashtux.org>'
SCRIPT_VERSION = '1.3'
SCRIPT_LICENSE = 'GPL3'
SCRIPT_DESC    = 'Display name days in bar item and buffer'

SCRIPT_COMMAND  = 'nameday'
SCRIPT_BAR_ITEM = 'nameday'

import_ok = True

try:
    import weechat
except ImportError:
    print('This script must be run under WeeChat.')
    print('Get WeeChat now at: http://www.weechat.org/')
    import_ok = False

try:
    import sys, time, unicodedata, re
    from datetime import date
except ImportError as message:
    print('Missing package(s) for %s: %s' % (SCRIPT_NAME, message))
    import_ok = False

# script options
nameday_settings_default = {
    'country'                : ('fr',      'country, only "fr" (french) is currently available'),
    'days'                   : ('1',       'number of days after current one to display in bar item'),
    'item_date_today'        : ('on',      'display date for today in bar item'),
    'item_date_next'         : ('off',     'display dates for tomorrow and next days in bar item'),
    'item_name_gender'       : ('off',     'display gender (St/Ste) before name'),
    'item_color_date_today'  : ('white',   'color for date in item (today)'),
    'item_color_name_today'  : ('green',   'color for name in item (today)'),
    'item_color_date_next'   : ('default', 'color for date in item (next days)'),
    'item_color_name_next'   : ('default', 'color for name in item (next days)'),
    'item_color_male_today'  : ('cyan',    'color for male names in item (today)'),
    'item_color_female_today': ('magenta', 'color for female names in item (today)'),
    'item_color_male_next'   : ('cyan',    'color for male names in item (next days)'),
    'item_color_female_next' : ('magenta', 'color for female names in item (next days)'),
    'color_male'             : ('cyan',    'color for male names'),
    'color_female'           : ('magenta', 'color for female names'),
    'reminder'               : ('',        'comma-separated list of names or dates (format: DD/MM) for which a reminder is displayed'),
}
nameday_settings = {}

nameday_item = ''
nameday_buffer = ''

namedays = {
    'fr': (
        # january
        ('!Marie (JOUR DE L\'AN)', '&Basile', '!Geneviève', '&Odilon', '&Edouard',
         '&Mélaine', '&Raymond,&Cédric,!Virginie', '&Lucien', '!Alix', '&Guillaume',
         '&Paulin', '!Tatiana', '!Yvette', '!Nina', '&Rémi,!Rachel',
         '&Marcel', '!Roseline', '!Prisca', '&Marius', '&Sébastien',
         '!Agnès', '&Vincent', '&Barnard', '&François de Sales', 'Conversion de St Paul',
         '!Paule', '!Angèle', '&Thomas d\'Aquin', '&Gildas', '!Martine,!Jacinthe',
         '!Marcelle'),
        # february
        ('!Ella,&Siméon', 'Présentation,&Théophane', '&Blaise', '!Véronique', '!Agathe',
         '&Gaston,!Dorothée', '!Eugénie', '!Jacqueline', '!Apolline', '&Arnaud',
         'Notre-Dame de Lourdes', '&Félix', '!Béatrice', '&Valentin', '&Claude,&Jordan',
         '!Julienne,!Lucile', '&Alexis', '!Bernadette', '&Gabin', '!Aimée',
         '&Damien', '!Isabelle', '&Lazare', '&Modeste', '&Roméo',
         '&Nestor', '!Honorine', '&Romain', '&Auguste'),
        # march
        ('&Aubin,&Albin,&Jonathan', '&Charles le Bon', '&Guénolé,&Marin', '&Casimir', '!Olive,!Olivia',
         '&Colette', '!Félicité,&Nathan', '&Ryan', '!Françoise', '&Vivien',
         '!Rosine', '!Justine,&Pol', '&Rodrigue', '!Mathilde', '!Louise',
         '!Bénédicte', '&Patrice,&Patrick', '&Cyrille', '&Joseph', '&Herbert',
         '!Clémence,!Axelle', '!Léa', '&Victorien', '!Catherine', '&Humbert',
         '!Larissa', '&Habib', '&Gontran', '!Gwladys', '&Amédée',
         '&Benjamin'),
        # april
        ('&Hugues,&Valéry', '!Sandrine', '&Richard', '&Isodore', '!Irène',
         '&Marcellin', '&Jean-Baptiste de la Salle,&Clotaire', '!Julie', '&Gautier', '&Fulbert',
         '&Stanislas', '&Jules', '!Ida', '&Maxime,!Ludivine', '&César,&Paterne',
         '&Benoît-Joseph Labre', '&Anicet', '&Parfait', '!Emma', '!Odette',
         '&Anselme', '&Alexandre', '&Georges', '&Fidèle', '&Marc',
         '!Alida', '!Zita', '!Valérie', '!Catherine de Sienne', '&Robert'),
        # may
        ('&Jérémie (FETE du TRAVAIL)', '&Boris,!Zoé', '&Philippe,&Jacques', '&Sylvain,&Florian', '!Judith',
         '!Prudence', '!Gisèle', '&Désiré (ANNIVERSAIRE 1945)', '&Pacôme', '!Solange',
         '!Estelle', '&Achille', '!Rolande,&Maël', '&Mathias,!Aglaé', '!Denise',
         '&Honoré,&Brendan', '&Pascal', '&Eric,!Corinne', '&Yves,&Erwan', '&Bernardin',
         '&Constantin', '&Emile,!Rita', '&Didier', '&Donatien', '!Sophie',
         '&Bérenger', '&Augustin', '&Germain', '&Aymar,!Géraldine', '&Ferdinand,!Jeanne',
         'Pétronille'),
        # june
        ('&Justin,&Ronan', '!Blandine', '&Kévin', '!Clotilde', '&Igor',
         '&Norbert', '&Gilbert', '&Médard', '!Diane', '&Landry',
         '&Barnabé,!Yolande', '&Guy', '&Antoine de Padoue', '&Elisée,&Valère', '!Germaine',
         '&François-Régis,&Régis', '&Hervé', '&Léonce', '&Romuald,&Gervais,!Micheline', '&Silvère',
         '&Rodolphe', '&Alban', '!Audrey', '&Jean-Baptiste', '&Salomon,&Prosper,!Aliénor,!Eléonore',
         '&Anthelme', '&Fernand', '&Irénée', '&Pierre,&Paul', '&Martial,&Adolphe'),
        # july
        ('&Thierry,!Esther', '&Martinien', '&Thomas', '&Florent', '&Antoine',
         '!Nolwen,!Mariette', '&Raoul', '&Thibaut,&Edgar,&Kilian,!Priscilla', '!Amandine,!Hermine,!Marianne', '&Ulrich',
         '&Benoît,!Olga', '&Olivier,&Jason', '&Henri,&Joël,&Enzo,&Eugène', '!Camille (FETE NATIONALE)', '&Donald,&Vladimir',
         '!Elvire', '!Charlotte,!Arlette,!Marcelline', '&Frédéric', '&Arsène', '!Marina',
         '&Victor', '!Madeleine', '!Brigitte', '!Christine,!Ségolène', '&Jacques,!Valentine',
         '!Anne,!Hannah,&Joachin', '!Nathalie', '&Samson', '!Marthe,!Béatrix,&Loup', '!Juliette',
         '&Ignace de Loyola'),
        # august
        ('&Alphonse', '&Julien', '!Lydie', '&Vianney', '&Abel',
         'Transfiguration', '&Gaëtan', '&Dominique', '&Amour', '&Laurent',
         '!Claire,!Gilberte,!Suzanne', '!Clarisse', '&Hippolyte', '&Evrard', '!Marie,&Alfred (ASSOMPTION)',
         '&Armel', '&Hyacinthe', '!Hélène,!Laetitia', '&Jean Eudes', '&Bernard,&Samuel',
         '&Christophe,!Grâce', '&Fabrice', '!Rose de Lima', '&Barthélémy', '&Louis',
         '!Natacha', '!Monique', '&Augustin,&Elouan', '!Sabine,&Médéric', '&Fiacre',
         '&Aristide'),
        # september
        ('&Gilles', '!Ingrid', '&Grégoire', '!Rosalie,!Iris,&Moïse', '!Raïssa',
         '&Bertrand,!Eva', '!Reine', '&Adrien,!Béline', '&Alain,&Omer', '!Inès',
         '&Adelphe,!Glenn,!Vinciane', '&Apollinaire', '&Aimé', 'La Ste Croix', '&Roland,!Dolorès',
         '!Edith', '&Renaud,&Lambert', '!Nadège,!Véra', '!Emilie', '&Davy',
         '&Matthieu,!Déborah', '&Maurice', '&Constant', '!Thècle', '&Hermann',
         '&Côme,&Damien', '&Vincent de Paul', '&Venceslas', '&Michel,&Gabriel,&Raphaël', '&Jérôme'),
        # october
        ('!Thérèse de l\'Enfant Jésus', '&Léger', '&Gérard', '&François d\'Assise', '!Fleur,!Chloé',
         '&Bruno', '&Serge,&Gustave', '!Pélagie,&Thaïs', '&Denis', '&Ghislain,&Virgile',
         '&Firmin', '&Wilfried,&Edwin', '&Géraud', '&Juste,!Céleste,!Gwendoline', '!Thérèse d\'Avila',
         '!Edwige', '&Baudouin,!Solène', '&Luc', '&René,!Cléo', '!Adeline,!Aline',
         '!Céline,!Ursule', '!Elodie,!Salomé', '&Jean de Capistran', '&Florentin', '&Crépin',
         '&Dimitri', '!Emeline', '&Simon,&Jude', '&Narcisse', '!Bienvenue,!Maéva',
         '&Quentin'),
        # november
        ('&Harold (TOUSSAINT)', 'Défunts', '&Hubert,&Gwenaël', '&Charles,&Aymeric', '!Sylvie,&Zacharie',
         '!Bertille,&Léonard', '!Carine', '&Geoffroy', '&Théodore', '&Léon,&Noah,&Noé,!Mélissa',
         '&Martin (ARMISTICE 1918)', '&Christian', '&Brice', '&Sidoine', '&Albert,&Arthur,&Léopold,!Victoire',
         '!Marguerite,!Mégane,!Gertrude', '!Elisabeth,!Elise,!Hilda', '!Aude', '&Tanguy', '&Edmond,&Octave',
         'Présentation de Marie', '!Cécile', '&Clément', '!Flora', '!Catherine',
         '!Delphine', '&Séverin', '&Jacques de la Marche', '&Saturnin', '&André'),
        # december
        ('!Florence', '!Viviane', '&Xavier', '!Barbara', '&Gérald',
         '&Nicolas', '&Ambroise', 'Immaculée Conception', '&Pierre Fourier', '&Romaric',
         '&Daniel', '!Chantal', '!Lucie,&Jocelyn', '!Odile', '!Ninon',
         '!Alice', '&Gaël', '&Gatien', '&Urbain', '&Abraham,&Théophile',
         '&Pierre Canisius', '!Françoise-Xavier', '&Armand', '!Adèle', '&Emmanuel,&Manuel (NOEL)',
         '&Etienne', '&Jean', '&Gaspard', '&David', '&Roger',
         '&Sylvestre,!Colombe'),
        )
    }

nameday_i18n = {
    'fr': { 'm'        : 'St ',
            'f'        : 'Ste ',
            },
    }

def nameday_remove_accents(string):
    """Remove accents from string."""
    if sys.version_info >= (3,):
        # python 3.x
        return unicodedata.normalize('NFKD', string).encode('ASCII', 'ignore').decode('UTF-8')
    else:
        # python 2.x
        return unicodedata.normalize('NFKD', unicode(string, 'UTF-8')).encode('ASCII', 'ignore')

def nameday_get_country():
    """Return country."""
    global nameday_settings, namedays
    country = nameday_settings['country']
    if not namedays[country]:
        country = 'fr'
    return country

def nameday_decode(name, gender, colorMale, colorFemale):
    """Decode name: replace special chars and optionally add color."""
    global nameday_i18n, nameday_settings
    country = nameday_get_country()
    replacement = { '&': '', '!': '' }
    if colorMale:
        replacement['&'] = weechat.color(nameday_settings[colorMale])
    if colorFemale:
        replacement['!'] = weechat.color(nameday_settings[colorFemale])
    if gender:
        replacement['&'] += nameday_i18n[country]['m']
        replacement['!'] += nameday_i18n[country]['f']
    return name.replace('&', replacement['&']).replace('!', replacement['!']).replace(',', ', ')

def nameday_get_month_day(month, day, gender, colorMale, colorFemale):
    """Get name day for given day/month."""
    global namedays
    try:
        country = nameday_get_country()
        name = namedays[country][month][day]
        return nameday_decode(name, gender, colorMale, colorFemale)
    except:
        return ''

def nameday_get_date(name_date, gender, colorMale, colorFemale):
    """Get name day for given date."""
    return nameday_get_month_day(name_date.month - 1, name_date.day - 1, gender, colorMale, colorFemale)

def nameday_completion_namedays_cb(data, completion_item, buffer, completion):
    """Complete with name days, for command '/nameday'."""
    global namedays
    country = nameday_get_country()
    for names in namedays[country]:
        for string in names:
            pos = string.find('(')
            if pos > 0:
                string = string[0:pos].strip()
            for name in string.split(','):
                name2 = nameday_decode(name, gender=False, colorMale='', colorFemale='')
                weechat.hook_completion_list_add(completion,
                                                 name2,
                                                 0, weechat.WEECHAT_LIST_POS_SORT)
                weechat.hook_completion_list_add(completion,
                                                 nameday_remove_accents(name2),
                                                 0, weechat.WEECHAT_LIST_POS_SORT)
    return weechat.WEECHAT_RC_OK

def nameday_buffer_input_cb(data, buffer, input_data):
    """Input callback for buffer."""
    if input_data.lower() == 'q':
        weechat.buffer_close(buffer)
    return weechat.WEECHAT_RC_OK

def nameday_buffer_close_cb(data, buffer):
    """Callback called when buffer is closed."""
    global nameday_buffer
    nameday_buffer = ''
    return weechat.WEECHAT_RC_OK

def nameday_display_list(buffer):
    """Display list of name days in buffer."""
    global namedays
    country = nameday_get_country()
    today = date.today()
    month = 0
    while month < len(namedays[country]):
        day = 0
        while day < len(namedays[country][month]):
            color = ''
            if today.month - 1 == month and today.day - 1 == day:
                color = weechat.color('yellow')
            weechat.prnt(buffer, '%s%02d/%02d  %s' % (color,
                                                      (day + 1), (month + 1),
                                                      nameday_get_month_day(month, day, gender=True, colorMale='color_male', colorFemale='color_female')))
            day += 1
        month += 1

def nameday_list():
    """Open buffer and display list of name days."""
    global nameday_buffer
    if nameday_buffer:
        weechat.buffer_set(nameday_buffer, 'display', '1')
    else:
        nameday_buffer = weechat.buffer_search('python', 'nameday');
        if not nameday_buffer:
            nameday_buffer = weechat.buffer_new('nameday', 'nameday_buffer_input_cb', '',
                                                'nameday_buffer_close_cb', '');
        if nameday_buffer:
            weechat.buffer_set(nameday_buffer, 'localvar_set_no_log', '1')
            weechat.buffer_set(nameday_buffer, 'time_for_each_line', '0')
            weechat.buffer_set(nameday_buffer, 'display', '1')
            weechat.buffer_set(nameday_buffer, 'title', 'Name days  |  Commands: list, listfull')
            nameday_display_list(nameday_buffer)

def nameday_print(days):
    """Print name day for today and option N days in future."""
    global nameday_i18n
    today = date.today()
    current_time = time.time()
    string = '%02d/%02d: %s' % (today.day, today.month,
                                nameday_get_date(today, gender=True,
                                                 colorMale='color_male',
                                                 colorFemale='color_female'))
    if days < 0:
        days = 0
    elif days > 50:
        days = 50
    if days > 0:
        string += '%s (' % weechat.color('reset')
        for i in range(1, days + 1):
            if i > 1:
                string += '%s, ' % weechat.color('reset')
            date2 = date.fromtimestamp(current_time + ((3600 * 24) * i))
            string += '%02d/%02d: %s' % (date2.day, date2.month,
                                         nameday_get_date(date2, gender=True,
                                                          colorMale='color_male',
                                                          colorFemale='color_female'))
        string += '%s)' % weechat.color('reset')
    weechat.prnt('', string)

def nameday_reminder(month=0, day=0, tag='notify_highlight'):
    """Display reminder for given date (or nothing if no reminder defined for today)."""
    global namedays, nameday_settings
    country = nameday_get_country()
    if month < 1 or day < 1:
        today = date.today()
        month = today.month
        day = today.day
    nameday = nameday_remove_accents(namedays[country][month - 1][day - 1]).lower()
    nameday_words = re.sub('[^a-z ]', '', nameday.replace(',', ' ')).split()
    reminder = False
    for name in nameday_settings['reminder'].split(','):
        if name:
            pos = name.find('/')
            if pos >= 0:
                if day == int(name[:pos]) and month == int(name[pos+1:]):
                    reminder = True
                    break
            else:
                wordsfound = True
                for word in name.strip().lower().split():
                    if word and word not in nameday_words:
                        wordsfound = False
                if wordsfound:
                    reminder = True
                    break
    if reminder:
        weechat.prnt_date_tags('', 0, tag,
                               '*\tReminder: %02d/%02d: %s' %
                               (day, month,
                                nameday_get_month_day(month - 1, day - 1,
                                                      gender=True,
                                                      colorMale='color_male',
                                                      colorFemale='color_female')))

def nameday_search(name):
    """Search a name."""
    global namedays
    user_nameday = nameday_remove_accents(name).lower()
    country = nameday_get_country()
    month = 0
    while month < len(namedays[country]):
        day = 0
        while day < len(namedays[country][month]):
            nameday = nameday_remove_accents(namedays[country][month][day])
            if (nameday.lower().find(user_nameday) >= 0):
                weechat.prnt('', '%02d/%02d: %s' % ((day + 1), (month + 1),
                                                    nameday_get_month_day(month, day,
                                                                          gender=True,
                                                                          colorMale='color_male',
                                                                          colorFemale='color_female')))
            day += 1
        month += 1

def nameday_search_reminders():
    """Search and display dates for reminders."""
    global namedays
    country = nameday_get_country()
    month = 0
    while month < len(namedays[country]):
        day = 0
        while day < len(namedays[country][month]):
            nameday_reminder(month + 1, day + 1, '')
            day += 1
        month += 1

def nameday_cmd_cb(data, buffer, args):
    """Command /nameday."""
    if args:
        if args == '*':
            nameday_list()
        elif args == '!':
            nameday_search_reminders()
        elif args.isdigit():
            nameday_print(int(args))
        elif args.find('/') >= 0:
            pos = args.find('/')
            if pos > 0:
                day = int(args[:pos])
                month = int(args[pos+1:])
                name = nameday_get_month_day(month - 1, day - 1, gender=True, colorMale='color_male', colorFemale='color_female')
                if name != '':
                    weechat.prnt('', '%02d/%02d: %s' % (day, month, name))
        else:
            nameday_search(args)
    else:
        nameday_print(1)
        nameday_reminder()
    return weechat.WEECHAT_RC_OK

def nameday_item_cb(data, buffer, args):
    """Callback for building nameday item."""
    global nameday_item
    return nameday_item

def nameday_build_item():
    """Build nameday item."""
    global nameday_settings, nameday_item
    nameday_item = ''
    display_date_today = nameday_settings['item_date_today'].lower() == 'on'
    display_date_next = nameday_settings['item_date_next'].lower() == 'on'
    display_gender = nameday_settings['item_name_gender'].lower() == 'on'
    color_date_today = weechat.color(nameday_settings['item_color_date_today'])
    color_name_today = weechat.color(nameday_settings['item_color_name_today'])
    color_date_next = weechat.color(nameday_settings['item_color_date_next'])
    color_name_next = weechat.color(nameday_settings['item_color_name_next'])
    color_default = weechat.color('default')
    today = date.today()
    if display_date_today:
        nameday_item += '%s%02d/%02d%s: ' % (color_date_today,
                                             today.day, today.month,
                                             color_default)
    nameday_item += '%s%s' % (color_name_today,
                              nameday_get_date(today, gender=display_gender,
                                               colorMale='item_color_male_today',
                                               colorFemale='item_color_female_today'))
    days = 0
    try:
        days = int(nameday_settings['days'])
    except:
        days = 0
    if days < 0:
        days = 0
    if days > 10:
        days = 10
    if days > 0:
        nameday_item += '%s (' % color_default
        current_time = time.time()
        for i in range(1, days + 1):
            if i > 1:
                nameday_item += ', '
            date2 = date.fromtimestamp(current_time + ((3600 * 24) * i))
            if display_date_next:
                nameday_item += '%s%02d/%02d%s: ' % (color_date_next,
                                                     date2.day, date2.month,
                                                     color_default)
            nameday_item += '%s%s' % (color_name_next,
                                      nameday_get_date(date2, gender=display_gender,
                                                       colorMale='item_color_male_next',
                                                       colorFemale='item_color_female_next'))
        nameday_item += '%s)' % color_default
    return nameday_item

def nameday_timer_cb(data, remaining_calls):
    """Called each day at midnight to change item content."""
    nameday_build_item()
    weechat.bar_item_update('nameday')
    nameday_reminder()
    return weechat.WEECHAT_RC_OK

def nameday_load_config():
    global nameday_settings_default, nameday_settings
    version = weechat.info_get('version_number', '') or 0
    for option, value in nameday_settings_default.items():
        if weechat.config_is_set_plugin(option):
            nameday_settings[option] = weechat.config_get_plugin(option)
        else:
            weechat.config_set_plugin(option, value[0])
            nameday_settings[option] = value[0]
        if int(version) >= 0x00030500:
            weechat.config_set_desc_plugin(option, value[1])

def nameday_config_cb(data, option, value):
    """Called each time an option is changed."""
    nameday_load_config()
    nameday_build_item()
    weechat.bar_item_update('nameday')
    return weechat.WEECHAT_RC_OK

if __name__ == '__main__' and import_ok:
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENSE, SCRIPT_DESC,
                        '', ''):
        # load config
        nameday_load_config()

        # new command
        weechat.hook_completion('namedays', 'list of name days',
                                'nameday_completion_namedays_cb', '')
        weechat.hook_command(SCRIPT_COMMAND,
                             'Display name days',
                             '[* | number | date | name | !]',
                             '     *: display list of name days in a new buffer\n'
                             'number: display name day for today and <number> days in future\n'
                             '  date: display name day for this date, format is day/month (for example: 31/01)\n'
                             '  name: display date for this name\n'
                             '     !: display reminder dates for names defined in option "reminder"\n\n'
                             'A bar item "nameday" can be used in a bar.\n\n'
                             'Examples:\n'
                             '  /nameday *          display list of name days in a new buffer\n'
                             '  /nameday            display name day for today and tomorrow\n'
                             '  /nameday 2          display name day for today, tomorrow, and after tomorrow\n'
                             '  /nameday 20/01      display name day for january, 20th\n'
                             '  /nameday sébastien  display day for name "sébastien"',
                             '*|!|%(namedays)', 'nameday_cmd_cb', '')

        # new item
        nameday_build_item()
        weechat.bar_item_new(SCRIPT_BAR_ITEM, 'nameday_item_cb', '')

        # timer
        weechat.hook_timer(3600 * 24 * 1000, 3600 * 24, 0, 'nameday_timer_cb', '')

        # config
        weechat.hook_config('plugins.var.python.' + SCRIPT_NAME + '.*', 'nameday_config_cb', '')

        # reminder
        nameday_reminder()
