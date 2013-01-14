"""
grader.py

Utilities for calculating and reporting grades
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

import csv, os, sys, math, optparse

from schoolutils.config import user_calculators

#
# Top-level interfaces
#
# Each interface accepts an input file handle, an output file
# handle, and an options structure
def csv_to_csv(in_file, out_file, options):
    "Interface for reading and writing CSV files"        
    fieldnames, rows = read_csv(in_file)

    # TODO: user_calculators need not provide a single
    # calculate_grade...
    calculated_rows = [user_calculators.calculate_grade(row) for row in rows]
    
    if options.sort_field:
        calculated_rows = sort_grade_list(calculated_rows, options.sort_field)
        
    write_csv(out_file, calculated_rows[0].keys(), calculated_rows)

#
# Grade-list operations and reporting functions
#
def sort_grade_list(rows, sort_field):
    "Sort a list of grade dicionaries by sort_field"
    def cmp_overall(x,y):
        if x[sort_field] < y[sort_field] or math.isnan(x[sort_field]):
            return 1 # puts highest score at the top
        elif y[sort_field] < x[sort_field] or math.isnan(y[sort_field]):
            return -1
        else:
            return 0
        
    rows.sort(cmp=cmp_overall)
    return rows

#
# Utility functions for grade calculations
#
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

# Aggregations and averages:   
def letter_grade_average(sgs, fieldnames, weights=None):
    """4.0-scale average of the letter grades found in sgs.
       If given, weights[i] should be a weight for the letter grade in
       sgs[fieldnames[i]]."""
    lgrades = [sgs[field] for field in fieldnames]
    pgrades = map(letter_to_points, lgrades)

    if weights:
        return weighted_average(pgrades, weights)
    else:
        return unweighted_average(pgrades)
    
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

#
# I/O
#
def write_csv(f, fields, all_sgs):
    "Write a list of student grade dictionaries to rows in a CSV file"
    # simple sanity check: don't try to write an empty list of grades
    if not all_sgs:
        sys.stderr.write("Grade table empty; skipping csv write.\n")
        return all_sgs

    writer = csv.DictWriter(f, fields)

    # writeheader() became available in Python 2.7:
    try:
        writer.writeheader()
    except AttributeError:
        writer.writerow(dict(zip(fields,fields)))

    for row in all_sgs:
        writer.writerow(row)

    return all_sgs

def read_csv(f, *args, **kwargs):
    "Read a list of student grades as dictionaries from a CSV file"
    reader = csv.DictReader(f, *args, **kwargs)
    rows = [row for row in reader]

    return reader.fieldnames, rows

#
# Main function when used as a script from CLI
#
def main():
    parser = optparse.OptionParser()
    parser.add_option("-i", "--csv-in", dest="in_file",
                      metavar="FILE",
                      help="Input data as CSV from FILE")
    parser.add_option("-o", "--csv-out", dest="out_file",
                      metavar="FILE",
                      help="Output data as CSV to FILE")
    parser.add_option("-s", "--sort", dest="sort_field",
                      metavar="FIELD_NAME",
                      help="Sort data on FIELD_NAME before output")
    options, args = parser.parse_args()

    if options.in_file:
        in_file = open(options.in_file, 'r')
    else:
        in_file = sys.stdin
        
    if options.out_file:
        out_file = open(options.out_file, 'w')
    else:
        out_file = sys.stdout

    try:
        csv_to_csv(in_file, out_file, options)
        exit(0)
    finally:
        in_file.close()
        out_file.close()

if __name__ == '__main__':
    main()
