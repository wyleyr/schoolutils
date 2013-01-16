"""
validators.py

Sample validators file for schoolutils
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

# A validator is a function that accepts a string and either returns a
# value or raises a ValueError.  Validators are used by the UI to
# prepare user-entered data to be saved to the database.  By defining
# your own validators, you'll ensure that the data in your grade
# database stays consistent with your expectations.
#
# For example, by defining the course_number validator, you can make
# sure that any course number saved in the database follows a
# particular format, and that if you accidentally type in a course
# number that doesn't follow this format, the UI will ask you to type
# it again.
#
# Any function you define here will override the function in
# schoolutils.grading.validators with the same name (provided that
# function has been marked as overrideable).  
# 
# Here is an example validator function:
def sid(s):
    """Ensure s is a valid UC Berkeley SID"""
    sid = s.strip()
    if len(sid) != 8:
        raise ValueError("SID must be 8 digits long")
    for digit in sid:
        if digit not in '0123456789':
            raise ValueError("Non-numeric digit in SID: %s" % digit)
    else:
        return sid


# The complete list of validators you can override is as follows:
# grade_type
# grade_weight
# percentage_grade
# four_point_grade
# letter_grade
# semester
# sid
# course_number
# course_name
# assignment_name
# name
# email
