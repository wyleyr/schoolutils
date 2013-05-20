"""
calculator_helpers.py: helpers for user-defined calculation functions.
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

import math

# Useful constants:
POINTS = [
    # format: (letter grade, point_value, exclusive_max, inclusive_min)
    ('A+', 4.2, 5.0, 4.2), 
    ('A', 4.0, 4.2, 3.85),
    ('A-', 3.7, 3.85, 3.5),
    ('B+', 3.3, 3.5, 3.15),
    ('B', 3.0, 3.15, 2.85),
    ('B-', 2.7, 2.85, 2.5),
    ('C+', 2.3, 2.5, 2.15),
    ('C', 2.0, 2.15, 1.85),
    ('C-', 1.7, 1.85, 1.5),
    ('D+', 1.3, 1.5, 1.15),
    ('D', 1.0, 1.15, 0.85),
    ('D-', 0.7, 0.85, 0.3),
    ('F', 0.0, 0.3, -1.0),
    # dummy limits ensure nothing falls in this range:
    ('I', float("Nan"), float("-inf"), float("inf"))
]

PERCENTS = [
    # format: (letter grade, point_value, exclusive_max, inclusive_min)
    ('A+', 100, 200, 97), 
    ('A', 95, 97, 94),
    ('A-', 92, 94, 90),
    ('B+', 88, 90, 87),
    ('B', 85, 87, 84),
    ('B-', 82, 84, 80),
    ('C+', 78, 80, 77),
    ('C', 75, 77, 74),
    ('C-', 72, 74, 70),
    ('D+', 68, 70, 67),
    ('D', 65, 67, 64),
    ('D-', 62, 64, 60),
    ('F', 58, 60, 0),
    # dummy limits ensure nothing falls in this range:
    ('I', float("Nan"), float("-inf"), float("inf"))
]

# Grade type conversions:
def letter_to_points(letter_grade):
    "Convert a letter grade to 4.0-scale grade"
    return letter_to_number(letter_grade, POINTS)

def letter_to_percentage(letter_grade):
    "Convert a letter grade to a percentage"
    return letter_to_number(letter_grade, PERCENTS)

def points_to_letter(p):
    "Convert a 4.0-scale grade to a letter grade"
    return number_to_letter(p, POINTS)

def percentage_to_letter(p):
    "Convert a percentage to a letter grade"
    return number_to_letter(p, PERCENTS)

def letter_to_number(letter_grade, scale):
    """Convert a letter grade to a number using a given scale.
       Returns float('Nan') for grades not in the scale."""
    for grade, val, mx, mn in scale:
        if letter_grade == grade:
            return val
    else:
        return float('Nan')

def number_to_letter(n, scale):
    """Convert a number grade n to a letter using a given scale.
       Returns 'I' for float('Nan') grades."""
    # any missing grades should default to Incomplete:
    if math.isnan(n):
        return 'I'

    # otherwise find the appropriate grade given ranges in the scale:
    for grade, val, mx, mn in scale:
        if mn <= n < mx:
            return grade
    else:
        raise ValueError("Value %s not on scale with max=%s and min=%s" %
                         (n, scale[0][2], scale[-2][3])) 
     
# Aggregations and averages:   
def letter_grade_average(letter_grades, weights=None):
    """4.0-scale average of grades in letter_grades.
       If given, weights[i] should be a weight for the letter grade in
       letter_grades[i]."""
    point_grades = map(letter_to_points, letter_grades)

    if weights:
        return weighted_average(point_grades, weights)
    else:
        return unweighted_average(point_grades)
    
def unweighted_average(grades):
    "Calculate an unweighted average"
    return float(sum(grades)) / len(grades)

def weighted_average(grades, weights):
    """Calculate a weighted average.
       weights[i] should be the weight given to the grade in grades[i].
       This function does not check that weights sum to 1 or normalize
       the resulting grades."""
    return sum([n[0] * n[1] for n in zip(grades, weights)])

def points_to_weights(point_values):
    """Convert a list of point values to a list of fractional weights.
       The return value at index i is the fraction that point_values[i]
       represents of the sum of point_values."""
    s = sum(point_values)
    return [float(p)/s for p in point_values]

# Munging input data:
def unpack_entered_grades(rows):
    """Extract grade values, weights, types and assignment names from a sequence
       of grade rows produced by, e.g., select_grades_for_course_members.
       Each row must have fields: value, weight, grade_type, assignment_name
       Skips any row where the weight is 'CALC' (indicating a calculated grade).
       
       Returns four co-indexed lists, in the following order:
         values: grade values
         weights: assignment weights
         types: assignment grade types
         names: assignment names
    """
    values = []
    weights = []
    types = []
    assignment_names = []
    for r in rows:
        values.append(r['value'])
        weights.append(r['weight'])
        types.append(r['grade_type'])
        assignment_names.append(r['assignment_name'])

    return values, weights, types, assignment_names

def extract_and_zero_grades(fields, d):
    "Extract an array of grades from a dictionary; convert non-numeric values to 0.0"
    # convert strings to floats; non-numeric values get a zero
    grades = []
    for f in fields:
        try:
            g = float(d[f])
        except ValueError:
            #print "converting to zero: %s" % d[f]
            g = 0.0
        grades.append(g)

    return grades

