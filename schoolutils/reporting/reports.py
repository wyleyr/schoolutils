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

import math, cStringIO

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
            grades = filter(lambda g: g['assignment_id'] == a['id'],
                            all_grades)
            missing = [g['student_id'] for g in grades if g['grade_id'] is None]
            try:
                mn, mx, avg = self.calculate_stats(grades)
                stats.append({
                        'assignment_id': a['id'],
                        'assignment_name': a['name'],
                        'grade_type': a['grade_type'],
                        'weight': a['weight'],
                        'min': mn,
                        'max': mx,
                        'mean': avg,
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
        "Calculate summary statistics for the grades for a particular assignment"
        values, weights, types, _ = ch.unpack_entered_grades(grades)
        grade_type = types[0] # values are for single assignment and grade type
        mn = ch.min_for_type(values, grade_type)
        mx = ch.max_for_type(values, grade_type)
        avg = ch.mean_for_type(values, grade_type, filter_nan=True)
        if math.isnan(avg):
            avg = None
        if avg and grade_type == 'letter':
            # letter grade is more useful here
            avg = ch.points_to_letter(avg)
       
        return mn, mx, avg

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
        row_template = ("{assignment_name: <15} {weight: <10} {mean: <10} {min: <10}"
                        "{max: <10} {num_missing: <15}\n")
        header = row_template.format(assignment_name="Assignment", weight="Weight",
                                     mean="Average",
                                     min="Minimum", max="Maximum",
                                     num_missing="Missing grades")
        underline = "".join('-' for i in range(len(header))) + "\n"
        
        output = cStringIO.StringIO()

        course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
        output.write(title_template.format(**course))
        output.write(header)
        output.write(underline)

        for s in self.stats:
            num_missing = len(s['missing_students'])
            if 'unavailable' in s:
                output.write(row_template.format(
                        assignment_name=s['assignment_name'],
                        weight=s['weight'],
                        min=None, max=None, mean=None,
                        num_missing=num_missing))
                continue
            
            output.write(row_template.format(num_missing=num_missing, **s))
            
        return output.getvalue()
       
    def as_full_text(self):
        """Return a full representation of this report.
           Includes names of students missing a grade for each assignment."""
        title_template = "GRADE REPORT: {number}: {name}, {semester} {year}\n"
        stats_template = ("{assignment_name: <25s}\n"
                          "Grade type: {grade_type: <8s} Weight: {weight: <8}\n"
                          "Average: {mean: <8} Minimum: {min: <8} "
                          "Maximum: {max: <8}\n")
        no_stats_msg = ("{assignment_name: <25s}\n  No statistics available for "
                        "this assignment, because:\n  {unavailable}\n")
        missing_template = ("{num_missing} students do not have a grade for this "
                            "assignment:\n{student_names}\n")
        name_template = "{last_name}, {first_name} (SID: {sid})"
        
        output = cStringIO.StringIO()

        course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
        output.write(title_template.format(**course))

        for s in self.stats:
            if 'unavailable' in s:
                output.write(no_stats_msg.format(**s))
                continue
                        
            output.write(stats_template.format(**s))
            if s['missing_students']:
                students = db.select_students(self.db_connection,
                                              course_id=self.course_id)
                names = "\n".join(name_template.format(**stu)
                                  for stu in students
                                  if stu['id'] in s['missing_students'])
                output.write(missing_template.format(
                        num_missing=len(s['missing_students']),
                        student_names=names))

            output.write('\n') # empty line between assignments

        return output.getvalue()
    
