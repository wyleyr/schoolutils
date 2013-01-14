"""
config.py

Sample configuration file for schoolutils
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

#
# General options
#
name = 'Your Name'
email = 'your.email@whatever.edu'

# path to your grade database file 
gradedb_file = '/path/to/grades.db'

#
# Grading options
#

# If you specify current_semester, current_year, and current_courses
# (as a list of course numbers), courses matching these criteria will
# be selectable from a list when you change courses in the grader, so
# you won't have to search for a course in the database.  They will
# also be used to determine the grade calculation functions for the
# current courses.
current_semester = 'Spring' # string
current_year = 2013 # int, not string
current_courses = [
    '146',
    ]

# if you specify default_course as a (semester, year, course_number)
# tuple, it will be selected as the current course when you start grader
default_course = (current_semester, current_year, current_courses[0])

# if you specify default_assignment as a string in addition to
# default_course, it will be selected as the current assignment when
# you start grader
default_assignment = "Paper 1"


