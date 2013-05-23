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

import cStringIO

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
            mn, mx, avg = self.calculate_stats(grades)
            stats.append({
                    'assignment_id': a['id'],
                    'assignment_name': a['name'],
                    'min': mn,
                    'max': mx,
                    'mean': avg,
                    'missing_students': missing,
                    })

        self.stats = stats
        return stats

    def calculate_stats(self, grades): 
        values, weights, types, _ = ch.unpack_entered_grades(grades)
        grade_type = types[0]
        mn = ch.min_for_type(values, grade_type)
        mx = ch.max_for_type(values, grade_type)
        avg = ch.mean_for_type(values, grade_type)
        if grade_type == 'letter':
            avg = ch.points_to_letter(avg) # letter grade is more useful here
       
        return mn, mx, avg

    def as_text(self):
        title_template = "GRADE REPORT: {number}: {name}, {semester} {year}\n"
        stats_template = "{assignment_name: <25s} Average: {mean: <8} Minimum: {min: <8}  Maximum: {max: <8}\n"
        missing_template = "{num_missing} students do not have a grade for this assignment:\n{student_names}"
        name_template = "{last_name}, {first_name} (SID: {sid})"
        
        output = cStringIO.StringIO()

        course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
        output.write(title_template.format(**course))

        for s in self.stats:
            output.write(stats_template.format(**s))
            if s['missing_students']:
                students = db.select_students(self.db_connection,
                                              course_id=self.course_id)
                names = "\n".join(name_template.format(**stu)
                                  for stu in students
                                  if stu['id'] in s['missing_students'])
                output.write(missing_template.format(num_missing=len(s['missing_students']),
                                                     student_names=names))

        return output.getvalue()
    
