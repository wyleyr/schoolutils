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

# Your name and email address.
name = 'Your Name'
email = 'your.email@whatever.edu'

# Path to the file containing your grade database.
# The grade database is stored as a single file; you can locate it
# wherever you want, such as with your other teaching-related files, or
# in a directory where it will be automatically backed up.  If the file
# you specify here does not already exist, the grading program will offer 
# to create it at startup.
gradedb_file = '~/.schoolutils/grades.db'

#
# Grading options
#

# If you specify current_semester, current_year, and current_courses
# (as a list of strings representing course numbers), courses matching
# these criteria will be selectable from a list when you change
# courses in the grading program, so you won't have to search for a
# course in the database.
current_semester = 'Spring' # string
current_year = 2013         # int, not string
current_courses = ['146',]  # list of strings

# If you specify a string for default_course, it will be used in
# conjunction with current_semester and current_year to select a
# current course when you start the grading program
default_course = current_courses[0]

# If you specify default_assignment as a string in addition to
# default_course, it will be selected as the current assignment when
# you start the grading program
#default_assignment = "Paper 1"
