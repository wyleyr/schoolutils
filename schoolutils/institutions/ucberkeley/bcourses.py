"""
bcourses.py

Functions for dealing with bcourses data
"""
# This file is part of the schoolutils package.
# Copyright (C) 2015 Richard Lawrence <richard.lawrence@berkeley.edu>
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

import csv

def gradebook_csv_to_students(fname):
    """Convert a CSV file from a bCourses gradebook to dictionaries
       representing students.

       Returns a generator which yields dictionaries with the following keys:
         full_name: original name data (as written in CSV file)
         last_name: last name, as split from full name (or '')
         first_name: first name, as split from full name (or '')
         sid: Berkeley student ID number
         email: email address

       The header row of the CSV file is ignored, and any record
       where the role is not "Student" is ignored.
    """
    with open(fname) as f:
        reader = csv.reader(f)

        # skip first TWO rows, which both contain header info
        next(reader)
        next(reader)

        for r in reader:
            # all other fields are grade-related or bcourses-related; ignore
            full_name = r[0]
            sid = r[2]
            
            try:
                last_name, first_name = full_name.split(',')
                last_name = last_name.strip().upper()
                first_name = first_name.strip().upper()
                # TODO: remove middle name? separate it into separate column?
                # need to do something...storing it in first_name column makes search more
                # difficult
            except ValueError:
                last_name = ''
                first_name = ''

            yield {'last_name': last_name,
                   'first_name': first_name,
                   'email': '',
                   'sid': sid}
        
def gradebook_csv_to_grades(fname, field_map=None):
    """Convert a CSV file from a bcourses gradebook to dictionaries
       representing student grades.
    """
    raise NotImplementedError

def assignment_csv_to_grades(fname):
    """Convert a CSV file from a bcourses assignment to dictionaries
       representing student grades.
    """
    raise NotImplementedError

def grades_to_gradebook_csv(fname, grades, field_map):
    raise NotImplementedError
