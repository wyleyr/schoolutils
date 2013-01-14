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

from schoolutils.grading import grader as g

# Every grade calculation function consumes a dictionary containing
# entered grades for one student and returns a dictionary containing
# both the entered grades and the calculated grades.
def calculate_grade_25A_fall2012(student_grades):
    """Calculates the unweighted average of letter grades for Papers
       1--3 and the exam grade.
       Calculated grades are:
         Grade average (4.0 scale)
         Final grade (letter grade)
    """
    entered_grades = ["Paper 1", "Paper 2", "Paper 3", "Exam grade"]

    avg = g.letter_grade_average(student_grades, entered_grades)
    student_grades["Grade average"] = avg
    student_grades["Final grade"] = g.points_to_letter(avg)

    return student_grades


