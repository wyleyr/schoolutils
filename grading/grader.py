"""
grader.py

Enter students' grades individually on a command line, then calculate
weighted averages and write to CSV.
"""
# The beginning of a Python program usually involves importing modules
# from the standard library.  Here I import the csv module so I can
# write a csv file, below, and a couple of modules nearly every Python
# program imports: os and sys.
import csv, os, sys, math

# A couple of global variables needed by the functions below; you
# should customize these for the particular class you're grading.
INPUT_FIELDS = ["Name", "Paper 1 grade", "Paper 2 grade"]
CALCULATED_FIELDS = ["Final percentage", "Final letter grade"]

# You probably don't need to change this function:        
def main():
    "The program's entry point, when run interactively."

    print "AUSTIN'S GREAT GRADING PROGRAM!"
    print "Enter each student's name and grade."
    print "To stop entry, leave the name field blank.\n"

    all_grades = []
    while True:
        student_grade_or_stop = get_next_student_grades()
        if student_grade_or_stop:
            all_grades.push(student_grade_or_stop)
        else:
            break

    write_csv(INPUT_FIELDS + CALCULATED_FIELDS, all_grades)

    exit(0) 
    
def main_with_csv(in_name, out_name, sort_field=''):
    "Main entry point, when run against a CSV file"
    fieldnames, rows = read_csv(in_name)

    calculated_fields = ['Grade average', 'Final grade']
    
    for row in rows:
        for field in calculated_fields:
            row[field] = calculate_grade(field, row)

    # sort rows before output based on sort_field if requested:
    def cmp_overall(x,y):
        if x[sort_field] < y[sort_field] or math.isnan(x[sort_field]):
            return 1 # puts highest score at the top
        elif y[sort_field] < x[sort_field] or math.isnan(y[sort_field]):
            return -1
        else:
            return 0
        
    if sort_field:
        rows.sort(cmp=cmp_overall)

    # output to CSV:
    write_csv(out_name, fieldnames + calculated_fields, rows)
            
# You'll need to modify this function to suit your needs:
def get_next_student_grades():
    """Ask the user for each of a student's assignment grades, then
    calculate their final percentage and letter grade"""
    
    student_grades = {}
    for f in INPUT_FIELDS:
        # ask the user for the value to put in each field
        i = raw_input("Enter %s: " % f)
        if not i and f == "Name":
            # stop when a name field is left blank
            return False
        else:
            # no attempt made here to convert input strings to numbers
            # or other types of value; you'll have to do that at some
            # point!  (Hint: you'll probably need the float()
            # function.)
            student_grades[f] = i

    for f in CALCULATED_FIELDS:
        student_grades[f] = calculate_grade(f, student_grades)

    return student_grades

# The functions below all deal with calculating grades.  You need to
# fill in the implementation here.
def calculate_grade_spring2012(f, sgs):
    raise NotImplementedError("Implementation of calculate_grade_spring2012 is gone")

def calculate_grade_summer2012(f, sgs):
    raise NotImplementedError("Implementation of calculate_grade_summer2012 is gone")

def calculate_grade_fall2012(f, sgs):
    "Calculate a fall 2012 (25A) grade on the basis of entered grades."
    if f == "Grade average":
        return letter_grade_avg(sgs, ["Paper 1", "Paper 2", "Paper 3", "Exam grade"])
    elif f == "Final grade":
        return points_to_letter(sgs["Grade average"])
    else:
        raise NotImplementedError(
            "Man, I haven't even *heard* of a '%s' grade. " % f +\
            "Don't even try that shit with me.") 

# update this every semester
calculate_grade = calculate_grade_fall2012

# represents ranges for grades on a GPA scale
# format: (letter grade, point_value, exclusive_max, inclusive_min)
# values less than -1.0 or greater than 5.0 are assumed not to be on this scale    
POINTS = [
    ('A+', 4.2, 5.0, 4.0), 
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

def letter_to_points(lgrd):
    "Convert a letter grade to 4.0-scale points"
    points_dict = dict([(p[0], p[1]) for p in POINTS])
    try:
        return points_dict[lgrd]
    except KeyError:
        # assume something went missing
        return float('Nan')
    
def points_to_letter(pts):
    "Convert a 4.0-scale grade to a letter grade"
    # any missing grades should default to Incomplete:
    if math.isnan(pts):
        return 'I'

    # otherwise find the appropriate grade given ranges in the scale:
    for grade, val, mx, mn in POINTS:
        if mn <= pts < mx:
            return grade
    else:
        raise ValueError("Value not on 4-point scale: %s" % pts) 
    

def final_percentage(sgs):
    "Calculate a final percentage based on a student's grades"
    raise NotImplementedError()

def final_letter_grade(sgs):
    "Calculate a final letter grade based on a student's grades"
    raise NotImplementedError()

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
        

# These functions are utility functions that you'll probably want to
# use in defining final_percentage, final_letter_grade, etc.  You need
# to provide the implementations.
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
                      
def weighted_average(nums, weights):
    "Calculate a weighted average"
    raise NotImplementedError()

def percentage_to_letter_grade(p):
    "Convert a percentage to a letter grade"
    raise NotImplementedError()

def letter_grade_to_percentage(lg):
    "Convert a letter grade to a percentage"
    raise NotImplementedError()

# This function will output the final list of student grades to a CSV
# file, so that you can look at the results in a text editor or in a
# spreadsheet.  I've provided the implementation here.
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
