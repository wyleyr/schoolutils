"""
validators.py

Validator functions for grading utilities
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

import datetime

from schoolutils.config import user_validators

def user_override(f):
    "Decorator: makes a validator overrideable by user's validators.py"
    return getattr(user_validators, f.__name__, f)

# Validators:
def number_in_range(s, constructor, mn, mx):
    """Convert s to a number and validate that it occurs in a given range.
       Min bound is inclusive; max bound is exclusive."""
    n = constructor(s)
    if not (mn <= n and n < mx):
        raise ValueError("Number %s outside acceptable range [%s, %s)" %
                         (n, mn, mx))
    return n

def int_in_range(s, mn, mx):
    return number_in_range(s, int, mn, mx)

def float_in_range(s, mn, mx):
    return number_in_range(s, float, mn, mx)

def year(s):
    "Convert s to a calendar year"
    return int_in_range(s, 1985, 2100)

def month(s):
    "Convert s to a calendar month"
    return int_in_range(s, 1, 13)

def day(s):
    "Convert s to a calendar day"
    return int_in_range(s, 1, 32)

def date(s):
    """Convert s to a datetime.date.
       s is assumed to be in YYYY-MM-DD format"""
    y, m, d = s.strip().split('-')
    y = year(y)
    m = month(m)
    d = day(d)
    return datetime.date(y, m, d)

@user_override
def grade_type(s):
    """Ensure s is a valid grade type.

       By default, converts s to lowercase and ensures it is one of
       'letter', 'points', or 'percentage'.
    """
    t = s.strip().lower()
    if t not in ['letter', 'points', 'percentage']:
        raise ValueError("Not a grade type: %s" % s)

    return t

@user_override
def grade_weight(s):
    """Ensure s is a valid grade weight.

       By default, this function is just an alias for float(); provide
       your own in your validators.py.
    """
    return float(s)

@user_override
def percentage_grade(s):
    """Convert s to a percentage grade.

       By default, this function accepts any string convertable to a
       float() value from 0.0 through (but not including) 100.1.
    """
    return float_in_range(s, 0, 100.1)

@user_override
def four_point_grade(s):
    """Convert s to a grade on a 4.0 scale.

       By default, this function accepts any string convertable to a
       float() value from 0.0 through (but not including) 5.0.
    """
    return float_in_range(s, 0.0, 5.0)

@user_override
def letter_grade(s):
    """Ensure s is a letter grade.

       By default, this function checks that s.upper() is a standard
       American letter grade, including 'F' (fail) and 'I' (incomplete).
    """
    letter_grades = [
        'A+', 'A', 'A-',
        'B+', 'B', 'B-',
        'C+', 'C', 'C-',
        'D+', 'D', 'D-',
        'F', 'I'
    ]
    g = s.strip().upper()
    if g not in letter_grades:
        raise ValueError("Not a letter grade: %s" % s)
    return g
    
@user_override
def semester(s):
    """Ensure s is a semester-designating string.

       By default, this function converts s to title case and ensures
       it is one of 'Fall', 'Spring', 'Summer' or 'Winter'.
    """
    S = s.strip().title()
    if S not in ['Fall', 'Spring', 'Summer', 'Winter']:
        raise ValueError("Not a semester designation: %s" % s)
    return S

@user_override
def sid(s):
    """Ensure s is a valid SID.

       By default, this function is just an alias for str(); provide
       your own in your validators.py.
    """
    return str(s)

@user_override
def course_number(s):
    """Ensure s is a valid course number.

       By default, this function is just an alias for str(); provide
       your own in your validators.py.
    """
    return str(s)

@user_override
def course_name(s):
    """Ensure s is a valid course name.

       By default, this function is just an alias for str(); provide
       your own in your validators.py.
    """
    return str(s)

@user_override
def assignment_name(s):
    """Ensure s is a valid assignment name.

       By default, this function is just an alias for str(); provide
       your own in your validators.py.
    """
    return str(s)

@user_override
def name(s):
    """Ensure s looks like a name.

       By default, this function strips whitespace and converts s to uppercase.
    """
    return s.strip().upper()

@user_override
def email(s):
    """Ensure s looks like an email address.

       By default, this function just checks that s contains '@', and converts
       the address to lower case.
    """
    e = s.lower()
    if '@' not in e:
        raise ValueError("%s does not appear to be an email address" % s)
    return e
