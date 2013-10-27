"""
reports.py

Basic report definitions.
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

import math, io

# support io.StringIO.write requiring unicode in Python 3
def u(s):
    try:
        return unicode(s)
    except NameError:
        return s

from schoolutils.grading import db, calculator_helpers as ch

class Report(object):
    """
    Base class for reports.
    """
    def __init__(self):
        pass

    def run(self):
        pass
    
    def as_text(self):
        pass


class GradeReport(Report):
    """
    Basic report on the grades in a course.
    """
    def __init__(self, db_connection, course_id=None):
        self.course_id = course_id
        self.db_connection = db_connection

    def run(self):
        "Run the calculations for this report"
        assignments = db.select_assignments(
            self.db_connection,
            course_id=self.course_id)
        
        all_grades = db.select_grades_for_course_members(
            self.db_connection,
            course_id=self.course_id)

        stats = []
        for a in assignments:
            grades = [g for g in all_grades if g['assignment_id'] == a['id']]
            missing = [g['student_id'] for g in grades if g['grade_id'] is None]
            try:
                mn, mx, avg, lavg = self.calculate_stats(grades)
                hist = self.histogram(grades)
                stats.append({
                        'assignment_id': a['id'],
                        'assignment_name': a['name'],
                        'grade_type': a['grade_type'],
                        'weight': a['weight'],
                        'min': mn,
                        'max': mx,
                        'mean': avg,
                        'mean_as_letter': lavg,
                        'hist': hist,
                        'missing_students': missing,
                        })
            except (ValueError, TypeError) as e:
                # no stats available here, e.g., because no grade_type
                stats.append({
                        'assignment_id': a['id'],
                        'assignment_name': a['name'],
                        'unavailable': str(e),
                        'weight': a['weight'],
                        'missing_students': missing,
                        })

        self.stats = stats
        return stats

    def calculate_stats(self, grades):
        """Calculate summary statistics for the grades for a particular assignment.
           Returns minimum, maximum, mean, and mean converted to a letter grade
           for a set of grades.
        """
        values, weights, types, _ = ch.unpack_entered_grades(grades)
        grade_type = types[0] # values are for single assignment and grade type
        mn = ch.min_for_type(values, grade_type)
        mx = ch.max_for_type(values, grade_type)
        avg = ch.mean_for_type(values, grade_type, filter_nan=True)
        letter_avg = None
        if math.isnan(avg):
            avg = None
        if avg:
            if grade_type == '4points' or grade_type == 'letter':
                letter_avg = ch.points_to_letter(avg)
            elif grade_type == 'percentage':
                letter_avg = ch.percentage_to_letter(avg)
       
        return mn, mx, avg, letter_avg

    def histogram(self, grades):
        "Produce a simple text histogram indicating an assignment's distribution of grades."
        values, weights, types, _ = ch.unpack_entered_grades(grades)

        if types[0] == 'letter': # values are for single assignment and grade type
            bins = [p[0] for p in ch.POINTS] # grade values in descending order
            freqs = ch.freqs_for_letters(values)
        else:
            if types[0] == '4points':
                scale = ch.POINTS
            elif types[0] == 'percent':
                scale = ch.PERCENTS
            else:
                raise ValueError("Can't calculate histogram bins for assignment type %s" %
                                 types[0])
            bins = [(p[2], p[3]) for p in scale]
            bins.pop(-1) # remove "dummy" limits bin with inf/-inf bounds 
            freqs = ch.freqs_for_numbers(values, bins)

        def bin_str(b):
            if isinstance(b, tuple):
                return "{1:<.2f} to {0:<.2f}".format(*b)
            else:
                return b # letter grade "bins" are already strings
            
        line_template = "{bin: >10}: {freq: <5} {bars}\n"
        lines = [line_template.format(bin=bin_str(b),
                                      bars="".join("|" for i in range(freqs[b])),
                                      freq=("({0})".format(freqs[b]) if freqs[b] else ""))
                 for b in bins] # ensure grade values are printed in order

        return "".join(lines)
    
    def as_text(self, compact=False):
        """Return a textual representation of this report as a string.
           If compact is True, returns a compact, tabular representation.
           If compact is False, returns a full report, including names
           of students who are missing grades for each assignment."""
        if compact:
            return self.as_compact_text()
        else:
            return self.as_full_text()

    def as_compact_text(self):
        "Return a compact, tabular representation of this report."
        title_template = "GRADE REPORT: {number}: {name}, {semester} {year}\n"
        row_template = ("{assignment_name: <25} {weight: <10} {mean: <5.4} {mean_as_letter: <5}"
                        "{min: <10} {max: <10} {num_missing: <15}\n")
        header = row_template.format(assignment_name="Assignment", weight="Weight",
                                     mean="Mean", mean_as_letter="",
                                     min="Minimum", max="Maximum",
                                     num_missing="Missing grades")
        underline = "".join('-' for i in range(len(header))) + "\n"
        
        output = io.StringIO()

        course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
        output.write(u(title_template.format(**course)))
        output.write(u(header))
        output.write(u(underline))

        for s in self.stats:
            num_missing = len(s['missing_students'])
            row = "\n"
            if 'unavailable' in s:
                row = u(row_template.format(
                        assignment_name=s['assignment_name'],
                        weight=s['weight'],
                        min=None, max=None, mean=None, mean_as_letter=None,
                        num_missing=num_missing))
            else:
                row = u(row_template.format(
                        assignment_name=s['assignment_name'],
                        weight=s['weight'],
                        min=s['min'], max=s['max'], mean=s['mean'],
                        mean_as_letter=("({0})".format(s['mean_as_letter'])
                                        if s['mean_as_letter'] else ""),
                        num_missing=num_missing))
            output.write(row)
            
        return output.getvalue()
       
    def as_full_text(self):
        """Return a full representation of this report.
           Includes names of students missing a grade for each assignment."""
        title_template = "GRADE REPORT: {number}: {name}, {semester} {year}\n"
        stats_template = ("{assignment_name: <25s}\n"
                          "Grade type: {grade_type: <8s} Weight: {weight: <8}\n"
                          "Average: {mean: <8} Minimum: {min: <8} "
                          "Maximum: {max: <8}\n"
                          "Distribution:\n{hist}\n")
        no_stats_msg = ("{assignment_name: <25s}\n  No statistics available for "
                        "this assignment, because:\n  {unavailable}\n")
        missing_template = ("{num_missing} students do not have a grade for this "
                            "assignment:\n{student_names}\n")
        name_template = "{last_name}, {first_name} (SID: {sid})"
        
        output = io.StringIO()

        course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
        output.write(u(title_template.format(**course)))

        for s in self.stats:
            if 'unavailable' in s:
                output.write(u(no_stats_msg.format(**s)))
                continue
                        
            output.write(u(stats_template.format(**s)))
            if s['missing_students']:
                students = db.select_students(self.db_connection,
                                              course_id=self.course_id)
                names = "\n".join(name_template.format(**stu)
                                  for stu in students
                                  if stu['id'] in s['missing_students'])
                output.write(u(missing_template.format(
                        num_missing=len(s['missing_students']),
                        student_names=names)))

            output.write(u('\n')) # empty line between assignments

        return output.getvalue()
    
