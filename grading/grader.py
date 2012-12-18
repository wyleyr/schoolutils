"""
grader.py

Utilities for calculating grades
"""
import csv, os, sys, math

#
# Interfaces
#
def main_with_csv(in_name, out_name, sort_field=''):
    "Main entry point, when run against a CSV file"
    fieldnames, rows = read_csv(in_name)

    calculated_rows = [calculate_grade(row) for row in rows]
    
    # sort rows before output based on sort_field if requested:
    def cmp_overall(x,y):
        if x[sort_field] < y[sort_field] or math.isnan(x[sort_field]):
            return 1 # puts highest score at the top
        elif y[sort_field] < x[sort_field] or math.isnan(y[sort_field]):
            return -1
        else:
            return 0
        
    if sort_field:
        calculated_rows.sort(cmp=cmp_overall)

    write_csv(out_name, calculated_rows[0].keys(), calculated_rows)
            
#
# Grade calculation functions for specific courses
#

# Every grade calculation function consumes a dictionary containing
# entered grades for one student and returns a dictionary containing
# both the entered grades and the calculated grades.
def calculate_grade_spring2012(sgs):
    raise NotImplementedError("Implementation of calculate_grade_spring2012 is gone")

def calculate_grade_summer2012(sgs):
    raise NotImplementedError("Implementation of calculate_grade_summer2012 is gone")

def calculate_grade_fall2012(sgs):
    entered_grades = ["Paper 1", "Paper 2", "Paper 3", "Exam grade"]

    gavg = letter_grade_avg(sgs, entered_grades)
    sgs["Grade average"] = gavg
    sgs["Final grade"] = points_to_letter(gavg)

    return sgs

# update this every semester
calculate_grade = calculate_grade_fall2012

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
       Returns 'I' for float('Nan') grades"""
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
# (needs significant generalization/refactoring)
def homework_avg(sgs):
    # mean of homework 1-9 scores, except the lowest is dropped
    hw_fields = [k for k in sgs.keys() if k[0:2] == 'EX']
    hw_fields.sort()

    # convert strings to floats; non-numeric values get a zero
    grades = extract_and_zero_grades(hw_fields, sgs)

    # drop the lowest score:
    grades.sort()
    grades = grades[1:]

    return sum(grades) / len(grades)

def quiz_avg(sgs):
    # mean of quizzes 1 through 3, times 10
    quiz_fields = [k for k in sgs.keys() if k[0:4] == 'Quiz' and len(k) < 12]

    grades = extract_and_zero_grades(quiz_fields, sgs)

    # drop the lowest score:
    grades.sort()
    grades = grades[1:]

    # multiply the average by 10, since quizzes were out of 10:
    return 10.0 * sum(grades) / len(grades)

def letter_grade_avg(sgs, fieldnames):
    "4.0-scale average (unweighted) of letter grades found in fieldnames"
    lgrades = [sgs[field] for field in fieldnames]
    pgrades = map(letter_to_points, lgrades)
    
    return sum(pgrades) / len(pgrades)
    
def overall_avg(sgs):
    # final percentage is:
    # 40% final exam
    # 20% midterm exam
    # 25% homework average
    # 15% quiz average
    final, midterm = extract_and_zero_grades(
        ['Final Exam [100]', 'Midterm Exam [100]'], sgs)
    homework = sgs['Homework average'] # error if not calculated yet!
    quiz = sgs['Quiz average'] # error if not calculated yet!
    
    avg = 0.40 * final + 0.20 * midterm + 0.25 * homework + 0.15 * quiz
    return avg
                      
def weighted_average(nums, weights):
    "Calculate a weighted average"
    raise NotImplementedError()

# I/O:
def write_csv(fname, fields, all_sgs):
    "Write a list of dictionaries representing student grades to rows in a CSV file"
    # don't try to write an empty list of grades:
    if not all_sgs:
        return "Grade table empty; skipping csv write."

    if os.path.exists(fname):
        sys.stderr.write("Warning! %s already exists; overwriting!\n" % fname)

    try:
        f = open(fname, 'w')
        writer = csv.DictWriter(f, fields)

        # writeheader() became available in Python 2.7:
        try:
            writer.writeheader()
        except AttributeError:
            writer.writerow(dict(zip(fields,fields)))

        # the actual data:    
        for row in all_sgs:
            writer.writerow(row)
    finally:
        f.close()

    return "Success!"

def read_csv(fname, *args, **kwargs):
    "Read a list of student grades as dictionaries from a CSV file"
    f = open(fname)
    reader = csv.DictReader(f, *args, **kwargs)
    rows = [row for row in reader]
    f.close()

    return reader.fieldnames, rows
    
# This is just a (somewhat strange-looking) Python idiom. It tells the
# interpreter to run the main() function when you type "python
# grader.py" at the command line.
if __name__ == '__main__':
   PREFIX = '/home/rwl/Documents/philosophy/teaching/25A/grades'
   main_with_csv(PREFIX + '/fall2012_grades.csv',
                 PREFIX + '/fall2012_grades_calculated.csv',
                 sort_field='Grade average')
