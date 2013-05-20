"""
calculators.py

Sample grade calculation function file
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

from schoolutils.grading import calculator_helpers as ch

# Every grade calculation function should be named like:
#   calculate_grade_<course number>_<semester><year>
# You should replace any characters in the course number which
# cannot appear in Python identifiers (e.g., '.' or '-') with '_'

# Every grade calculation function must consume a set of database rows
# representing the entered grades for one student and return a
# dictionary, or list of dictionaries, representing the calculated
# grades.

# Here's a simple example:
def calculate_grade_146_spring2013(rows):
    # Unpack the data from the database rows:
    # unpack_entered_grades returns co-indexed lists of
    # grade values, weights, types, and assignment names for entered grades
    vals, weights, types, assignment_names = ch.unpack_entered_grades(rows)

    # Do the actual calculations:
    # letter_grade_average converts each of the letter grade values to
    # a 4.0 scale, then takes a weighted average.
    # (Here we are assuming all the grades are letter grades.)
    avg = ch.letter_grade_average(vals, weights=weights)
    # points_to_letter converts the average back to a letter grade
    final = ch.points_to_letter(avg)

    # Return a representation of the calculated grades:
    # In this simple case, we just return a dictionary whose keys name
    # the calculated fields (i.e., the `assignments' these grade values are
    # associated with), and whose values are the calculated values
    # for this student.
    return {
        'Paper average': avg,
        'Final grade': final,
    }


# And here's a more complicated example:
def calculate_grade_146_spring2013(rows):
    # Instead of unpacking the data in rows, we can operate with it directly.
    # Each row has the following fields (see the documentation for
    # schoolutils.grading.db.select_grades_for_course_members), which can be
    # accessed like dictionary keys:
    # assignment_id, assignment_name, weight, grade_type, grade_id, student_id, value
    # For example:
    paper_grades = []
    exercise_grades = []
    for r in rows:
        if r['grade_type'] == 'letter':
            paper_grades.append(r['value'])
        elif r['grade_type'] == 'percentage':
            exercise_grades.append(r['value'])
        # etc. ...

    # do calculations here on different grade types...

    # When it's time to return the calculated grades, we can also
    # return a list of dictionaries.  In this case, each dictionary
    # specifies a number of fields describing each calculated grade.
    # It can include the following fields:
    #   name (required): a name for the (type of) calculated grade
    #   value (required): the grade value for this student
    #   description: a description of this type of grade
    #   grade_type: the grade type, e.g., 'letter'
    #   due_date: a datetime.date 'due date' for this type of grade
    #           (defaults to the current date; useful because due dates
    #            are used to order assignment columns when editing and
    #            exporting grades)
    #   weight: a weight for this type of grade
    #           (defaults to 'CALC', a special value that indicates
    #            this is a calculated grade type rather than an entered
    #            grade type)
    # You can also use this mechanism to update existing grades, or store
    # grades for which no value was entered for this student.  To do so,
    # include one of these keys:
    #   grade_id: this updates an existing grade (by its primary key)
    #   assignment_id: this creates a new grade for an existing assignment
    # In this case, the 'name' key is optional, but 'value' is still required.
    return [
        dict(name='Paper average',
             value=avg,
             description='Weighted average of paper grades',
             grade_type='4points'),
        dict(name='Final grade',
             value=final,
             description='Raw letter grade',
             grade_type='letter'),
        # update an existing grade:
        dict(grade_id=some_grade_id,
             value=new_value)
        # create grade for assignment, e.g., if no value was previously entered:
        dict(assignment_id=some_assignment_id,
             value='F')
        ]


