"""
config/__init__.py

Load user configuration modules or sensible defaults
"""
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
