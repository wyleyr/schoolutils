"""
config/__init__.py

Load user configuration modules or sensible defaults
"""
# This file is part of the schoolutils package.
# Copyright (C) 2013 Richard Lawrence <richard.lawrence@berkeley.edu>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import os, sys, imp, datetime

USER_CONFIG_DIR = os.path.join(os.environ['HOME'], '.schoolutils')
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, 'config.py')
USER_CALCULATORS_FILE = os.path.join(USER_CONFIG_DIR, 'calculators.py')
USER_VALIDATORS_FILE = os.path.join(USER_CONFIG_DIR, 'validators.py')

CONFIG_DEFAULTS = {
    'name': '',
    'email': '',
    'institution': '',
    'gradedb_file': '',
    'current_semester': None,
    'current_year': datetime.date.today().year,
    'current_courses': [],
    'default_course': (None, None, None), # semester, year, course_num
    'default_assignment': None,
}

def add_defaults(m, defaults):
    "Add default values to a module."
    for k, v in defaults.iteritems():
        if not hasattr(m, k):
            setattr(m, k, v)

    return m
        
def user_modules():
    "Load or construct the user's config.py, calculators.py, and validators.py"
    try:
        user_config = add_defaults(imp.load_source('user_config',
                                                   USER_CONFIG_FILE),
                                   CONFIG_DEFAULTS)
    except (IOError, ImportError):
        user_config = imp.new_module('user_config')
        
    try:
        user_calculators = imp.load_source('user_calculators',
                                           USER_CALCULATORS_FILE)
    except (IOError, ImportError):
        user_calculators = imp.new_module('user_calculators')

    try:
        user_validators = imp.load_source('user_validators',
                                          USER_VALIDATORS_FILE) 
        # TODO: add defaults?
    except (IOError, ImportError):
        user_validators = validators
        
    return user_config, user_calculators, user_validators

# make config, calculators, and validators available from this module
user_config, user_calculators, user_validators = user_modules()
