"""
bspace.py

Functions for dealing with bSpace data
"""

import csv

def roster_csv_to_students(fname):
    """Convert a CSV file from a bSpace roster to dictionaries
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
        field_names = ['full_name', 'sid', 'email', 'role']
        reader = csv.DictReader(f, fieldnames=field_names)
        for r in reader:
            if r['role'].lower() != 'student':
                # this implicitly skips the header line, as well as any
                # GSI/instructor records
                continue

            full_name = r['full_name']
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

            r['last_name'] = last_name
            r['first_name'] = first_name
            r.pop('role')

            yield r
        
def gradebook_csv_to_grades(fname, field_map=None):
    """Convert a CSV file from a bSpace gradebook to dictionaries
       representing student grades.
    """
    raise NotImplementedError

def assignment_csv_to_grades(fname):
    """Convert a CSV file from a bSpace assignment to dictionaries
       representing student grades.
    """
    raise NotImplementedError

def grades_to_gradebook_csv(fname, grades, field_map):
    raise NotImplementedError
