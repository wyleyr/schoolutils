"""
ui.py

User interfaces for grading utilities.
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

# imports to support Python 3
from __future__ import print_function

try:
    input = raw_input
except NameError:
    pass

# imports compatible across Python versions
import os, sys, csv, datetime, tempfile

from schoolutils.config import user_config, user_calculators
from schoolutils.grading import db, validators
from schoolutils.reporting import reports

# TODO: abstract from specific institution
from schoolutils.institutions.ucberkeley import bspace

def require(attribute, callback, message):
    """Require that an object has an attribute before executing a method.
       attribute should be the attribute name.
       callback should be a method that will mutate the object to provide
         the attribute when it doesn't exist; it will be called with the object
         as an argument
       message should be a message to print to the user before callback is
         called""" 
    def method_factory(f):
        def method(self, *args, **kwargs):
            attr = getattr(self, attribute, None)
            while not attr:
                print("")
                print(message)
                callback(self)
                attr = getattr(self, attribute, None)
            return f(self, *args, **kwargs)
        method.__doc__ = f.__doc__  # preserve docstring for actions_menu  
        return method
    return method_factory

class BaseUI(object):
    def __init__(self, options=None):
        """Initialize grading program UI.
           options, if provided, should be an options structure produced by
             optparse
        """
        if options:
            self.cli_options = options
        else:
            self.cli_options = None
            
        
        self.semester = None
        self.year = None
        self.current_courses = []
        self.course_id = None
        self.assignment_id = None

        self.initial_database_setup()
        self.initial_course_setup()
        self.initial_assignment_setup()

        
    def get_config_option(self, option_name, validator, default=None):
        """Return the appropriate config value from CLI options or user config.
           option_name should be an attribute to look for on both the options
             object and the user_config module.  CLI options override user_config
             values.
           validator will be applied to the value.
           Returns the validated value, or default if option is not
           supplied by the user or the user-supplied value does not
           pass validation.
        """
        val = (getattr(self.cli_options, option_name, '') or
               getattr(user_config, option_name, ''))
        try:
            return validator(val)
        except ValueError:
            return default

    def initial_database_setup(self):
        "Set db_file and db_connection from user config and CLI options"
        self.db_file = self.get_config_option('gradedb_file', file_path)
        if self.db_file and os.path.exists(self.db_file):
            try:
                self.db_connection = db.connect(self.db_file, create=False)
            except db.ConnectionError:
                self.db_connection = None
        else:
            self.db_connection = None

            
    def initial_course_setup(self):
        """Set semester, year, current_courses, and course_id from user config
           and CLI options"""
        
        self.semester = self.get_config_option('current_semester',
                                               validators.semester)
        self.year = self.get_config_option('current_year', validators.year)
        self.current_courses = user_config.current_courses
        course_num = self.get_config_option('default_course',
                                            validators.course_number)
        
        if not (self.db_connection and self.semester and self.year):
            # don't bother looking for a course without a semester and year
            # (but try otherwise, because these might identify one uniquely)
            return
        
        try:
            self.course_id = db.ensure_unique(
                db.select_courses(self.db_connection,
                                  semester=self.semester,
                                  year=self.year,
                                  number=course_num))
        except (db.NoRecordsFound, db.MultipleRecordsFound):
            sys.stderr.write("Unable to locate a unique default course; "
                             "ignoring.\n")
            
            
    def initial_assignment_setup(self):
        "Set assignment_id using user config and CLI options"
        if not (self.db_connection and self.course_id):
            return

        if user_config.use_last_due_assignment:
            try:
                self.select_last_due_assignment()
            except AttributeError: # select_last_due_assignment is currently defined by SimpleUI
                sys.stderr.write("Ignoring use_last_due_assignment.\n")

       

class SimpleUI(BaseUI):
    """Manages a simple (command line) user interface.
    """
    # Helpers for printing data to stdout
    STUDENT_FORMAT = '{last_name}, {first_name} (SID: {sid})'
    COURSE_FORMAT = '{number} - {name} ({semester} {year})'
    ASSIGNMENT_FORMAT = '{name} (due {due_date})'
    GRADE_FORMAT = '' # TODO

    def course_formatter(self, course_row):
        "Format COURSE_FORMAT with course from db"
        return self.COURSE_FORMAT.format(year=course_row['year'],
                                         semester=course_row['semester'],
                                         number=course_row['number'],
                                         name=course_row['name'])

    def student_formatter(self, student_row):
        "Format STUDENT_FORMAT with student from db"
        return self.STUDENT_FORMAT.format(last_name=student_row['last_name'],
                                          first_name=student_row['first_name'],
                                          sid=student_row['sid'])

    def assignment_formatter(self, assignment_row):
        return self.ASSIGNMENT_FORMAT.format(name=assignment_row['name'],
                                             due_date=assignment_row['due_date'])

    def grade_formatter(self, grade_row):
        pass
   
    # BaseUI overrides
    def initial_database_setup(self):
        """Set db_file and db_connection from user config and CLI options.
           Query the user if automatic database connection fails."""
        super(SimpleUI, self).initial_database_setup()
        if self.db_connection:
            return
        if not self.db_file:
            return self.change_database()

        err_msg = ''
        if not os.path.exists(self.db_file):
            prompt = "No existing database at %s.\nCreate? (Y/N) " % self.db_file
            if typed_input(prompt, yn_bool):
                try:
                    self.db_connection = db.connect(self.db_file, create=True)
                except db.ConnectionError as e:
                    err_msg = ("FAILED to create database at {path}.\n"
                               "Error was: {err}".format(path=self.db_file, err=e))
        else:
            # retry automatic connection, mostly to get error message
            try:
                self.db_connection = db.connect(self.db_file, create=False)
            except db.ConnectionError as e:
                err_msg = ("FAILED to open file at {path} as a grade database.\n"
                           "Error was: {err}".format(path=self.db_file, err=e))
                    
        if not self.db_connection:
            if err_msg:
                print(err_msg)
            print("Could not open a grade database based on your settings "
                  "in config.py.\n"
                  "Check the value of your gradedb_file setting and "
                  "permissions of your database \nfile and enclosing directory.")
            if typed_input("Enter database path manually? (Y/N) ", yn_bool):
                return self.change_database()
            else:
                # setup attempts failed, but we can still let the user
                # go to the main menu
                self.db_connection = None
                
    # Actions which can be @require-d: 
    def close_database(self):
        """Close the current database connection."""
        if self.db_connection:
            print("Closing current database located at: %s" % self.db_file)
            self.db_connection.commit()
            self.db_connection.close()
            self.db_connection = None
            self.db_file = None
            # these fields will now be invalid, so erase them too:
            self.course_id = None
            self.assignment_id = None

            
    def change_database(self):
        """Open a new database.
           Closes the current database connection (if any) and opens another."""
        if self.db_connection:
            self.close_database()
        
        db_path = typed_input("Enter path to grade database: ", file_path)
        create = False
        if not os.path.exists(db_path):
            create = typed_input(
                "No existing database at %s.\nCreate (Y/N)? " % db_path,
                yn_bool)
        try:
            self.db_file = db_path
            self.db_connection = db.connect(db_path, create=create)
        except db.ConnectionError as e:
            print("Could not open {path} as a grade database.\n"
                  "Error was: {err}".format(path=db_path, err=e))
            
            if typed_input("Try again? (Y/N) ", yn_bool):
                return self.change_database()
            else:
                print("Database change aborted.")
            
            
    def get_student(self, create=False):
        """Lookup a student in the database, trying several methods.
           If create is True, allow (and offer) creating a new student using
             entered criteria if none exists.
           Returns student row. 
        """
        student = None
        first_name = ''
        last_name = ''
        sid = ''
        email = ''

        # Helpers
        class UniqueFound(Exception):
            # dummy class for flow control
            pass
        
        def quit_if_unique(students):
            "Stop searching if a unique student has been located"
            if len(students) == 1:
                raise UniqueFound
            else:
                print("%d students found." % len(students))
                
        def students_menu(students):
            "Select a student (or None) from a menu"
            return self.options_menu(
                "Select a student:",
                students, 
                self.student_formatter,
                allow_none=create)
               
        students = []
        try:
            print("Enter student data to lookup or create student. "
                  "Search uses fuzzy matching on name and email fields.\n"
                  "Use Ctrl-C to stop search and select from list.")
            sid = typed_input("Enter SID: ", validators.sid, default='')
            students = db.select_students(self.db_connection, sid=sid)
            quit_if_unique(students)

            last_name = typed_input("Enter last name: ", validators.name,
                                    default='')
            students = db.select_students(self.db_connection,
                                          sid=sid,
                                          last_name=last_name,
                                          fuzzy=True)
            quit_if_unique(students)
            
            first_name = typed_input("Enter first name: ", validators.name,
                                     default='')
            students = db.select_students(self.db_connection,
                                          sid=sid,
                                          last_name=last_name,
                                          first_name=first_name,
                                          fuzzy=True)
            quit_if_unique(students)

            email = typed_input("Enter email: ", validators.email, default='')
            students = db.select_students(self.db_connection,
                                          sid=sid,
                                          last_name=last_name,
                                          first_name=first_name,
                                          email=email,
                                          fuzzy=True)
            quit_if_unique(students)

        except UniqueFound:
            if create:
                # edge case: unique student found, but user may still
                # want to add a new one
                student = students_menu(students)
            else:
                student = students[0]
            
        except KeyboardInterrupt:
            # don't bother with a selection menu if no students met all
            # the search criteria at the time the user presses Ctrl-C
            if students:
                student = students_menu(students)
            elif not create:
                # if no students have been found and creation is not an option,
                # user wants to escape; so error should propagate 
                raise KeyboardInterrupt
            
        if student:
            pass
        elif create and typed_input("No student found; create? (Y/N) ", yn_bool):
            # give user a chance to update values they provided and provide values
            # they didn't enter
            vals = {'last_name': last_name, 'first_name': first_name,
                    'sid': sid, 'email': email}
            print("Please provide data for the student to be created:")
            vals = self.edit_student_dict(from_dict=vals)
            vals.pop('student_id') # we're creating a new record
            student_id = db.create_student(self.db_connection, **vals)
            student = db.select_students(self.db_connection,
                                         student_id=student_id)[0]
        else:
            print("Could not locate student with these criteria; please try again.")
            return self.get_student(create=create)

        print("Selected: %s" % self.student_formatter(student))
        return student

    # Top-level actions:       
    def main_loop(self):
        "Main menu"
        while True:
            self.print_db_info()
            self.print_course_info()
            self.print_assignment_info()
            self.actions_menu(
                "Main menu.",
                [self.change_database,
                 self.edit_courses,
                 self.edit_assignments,
                 self.import_students,
                 self.edit_student,
                 self.enter_grades,
                 self.edit_grades,
                 self.calculate_grades,
                 #self.import_grades,
                 self.export_grades,
                 self.grade_report,
                 self.exit])

            # commit after successful completion of any top-level action
            # to avoid data-loss
            if self.db_connection:
                self.db_connection.commit()

           
    @require('db_connection', change_database,
             "A database connection is required to edit courses.")
    def edit_courses(self):
        """Edit courses.
           Select, create, edit and delete courses."""
        def edit_course(c):
            make_default_clause = lambda v: (" (default: %s)" % str(v)
                                             if v else '')
            name_prompt = "Enter course name{default}: ".format(
                default=make_default_clause(c['name']))
            course_name = typed_input(name_prompt, validators.course_name,
                                      default=c['name'])
            year_prompt = "Enter year{default}: ".format(
                default=make_default_clause(c['year']))
            year = typed_input(year_prompt, validators.year, default=c['year'])
            sem_prompt = "Enter semester{default}: ".format(
                default=make_default_clause(c['semester']))
            semester = typed_input(sem_prompt, validators.semester,
                                   default=c['semester'])
            num_prompt = "Enter course number{default}: ".format(
                default=make_default_clause(c['number']))
            course_num = typed_input(num_prompt, validators.course_number,
                                     default=c['number'])
            
            course_id = db.create_or_update_course(
                self.db_connection,
                course_id=c['id'],
                year=year,
                semester=semester,
                name=course_name,
                number=course_num)

            return db.select_courses(self.db_connection, course_id=course_id)[0]
        
        create_course = lambda: edit_course({
                'id': None,
                'name': None,
                'year': None,
                'semester': None,
                'number': None,
                })
                
        def delete_course(c):
            existing_assignments = db.select_assignments(self.db_connection,
                                                         course_id=c['id'])
            existing_grades = [g for g in db.select_grades_for_course_members(
                                       self.db_connection,
                                       course_id=c['id'])
                               if g['value'] is not None]
            enrollees = db.select_students(self.db_connection, course_id=c['id'])
            if existing_assignments:
                print("WARNING: there are %d existing assignments for this course, "
                      "with %d associated grades.\n"
                      "Deleting this course will DELETE THESE ASSIGNMENTS AND GRADES, "
                      "and UNENROLL %d STUDENTS." %
                      (len(existing_assignments), len(existing_grades), len(enrollees)))
                if not typed_input("Delete anyway? (Y/N) ", yn_bool):
                    return False

            # deselect if this course was the currently selected course
            if self.course_id == c['id']:
                self.course_id = None
            if self.assignment_id in existing_assignments:
                self.assignment_id = None
                
            return db.delete_course_etc(self.db_connection,
                                        course_id=c['id'])

        def select_course(c):
            if self.course_id != c['id']:
                self.course_id = c['id']
                self.assignment_id = None
                print("Selected %s as current course."
                      % self.course_formatter(c))
            if user_config.use_last_due_assignment:
                self.select_last_due_assignment()
                if self.assignment_id:
                    assignment = db.select_assignments(
                        self.db_connection,
                        assignment_id=self.assignment_id)[0]
                    print("Selected %s as current assignment." %
                          self.assignment_formatter(assignment))

            print("")   
            return True
        
        formatter = self.course_formatter
        header = "Courses"
        courses = db.select_courses(self.db_connection)
        
        self.edit_table(courses, header, formatter,
                        entity_type='course',
                        editor=edit_course,
                        creator=create_course,
                        deleter=delete_course,
                        selector=select_course)
 

    @require('db_connection', change_database,
             "A database connection is required to edit assignments.")
    @require('course_id', edit_courses,
             "A selected course is required to edit assignments.")
    def edit_assignments(self):
        """Edit assignments.
           Select, create, edit and delete assignments for the current course."""
        def edit_assignment(a):
            make_default_clause = lambda v: (" (default: %s)" % str(v)
                                             if v else '')
            name_prompt = "Enter assignment name{default}: ".format(
                default=make_default_clause(a['name']))
            name = typed_input(name_prompt, validators.assignment_name,
                               default=a['name'])
            desc_prompt = "Enter description{default}: ".format(
                default=make_default_clause(a['description']))
            description = typed_input(desc_prompt, str,
                                      default=a['description'])
            due_date_prompt = "Enter due date (YYYY-MM-DD){default}: ".format(
                default=make_default_clause(a['due_date']))
            due_date = typed_input(due_date_prompt, validators.date,
                                   default=a['due_date'])
            grade_type_prompt = "Enter grade type{default}: ".format(
                default=make_default_clause(a['grade_type']))
            grade_type = typed_input(grade_type_prompt, validators.grade_type,
                                     default=a['grade_type'])
            gt_unchanged = (grade_type == a['grade_type'])
            if grade_type == "points":
                wt_prompt = "Enter number of possible points{default}: ".format(
                    default=make_default_clause(
                        # don't use default if grade type changed
                        a['weight'] if gt_unchanged else ''))
            else:
                wt_prompt = "Enter grade weight (as decimal fraction of 1){default}: ".format(
                    default=make_default_clause(
                        # don't use default if grade type changed
                        a['weight'] if gt_unchanged else ''))
            weight = typed_input(wt_prompt, validators.grade_weight,
                                 default=a['weight'])

            a_id = db.create_or_update_assignment(
                self.db_connection,
                assignment_id=a['id'],
                course_id=self.course_id,
                name=name, description=description, grade_type=grade_type,
                due_date=due_date, weight=weight)

            return db.select_assignments(self.db_connection, assignment_id=a_id)[0]

        create_assignment = lambda: edit_assignment({
                'id': None,
                'name': None,
                'description': '',
                'due_date': None,
                'grade_type': None,
                'weight': None
                })
                
        def delete_assignment(a):
            existing_grades = db.select_grades(self.db_connection,
                                               assignment_id=a['id'])
            if existing_grades:
                print("WARNING: there are %d existing grades for this assignment.\n"
                      "Deleting this assignment WILL ALSO DELETE THEM." %
                      len(existing_grades))
                if not typed_input("Delete anyway? (Y/N) ", yn_bool):
                    return False

            # deselect if this assignment was the currently selected assignment
            if self.assignment_id == a['id']:
                self.assignment_id = None
                
            return db.delete_assignment_and_grades(self.db_connection,
                                                   assignment_id=a['id'])

        def select_assignment(a):
            self.assignment_id = a['id']
            print("Selected %s as current assignment.\n"
                  % self.assignment_formatter(a))
            return True
        
        format_str = ("{name: <20s} {due_date: <10s} {grade_type: <7s} {weight: <6} "
                      "{description: <32s}")
        formatter = lambda r: format_str.format(**r)
        header = format_str.format(name="Name", due_date="Due date",
                                   grade_type="Type", weight="Weight",
                                   description="Description")
        assignments = db.select_assignments(self.db_connection,
                                            course_id=self.course_id)
        
        self.edit_table(assignments, header, formatter,
                        entity_type='assignment',
                        editor=edit_assignment,
                        creator=create_assignment,
                        deleter=delete_assignment,
                        selector=select_assignment)
        
    @require('db_connection', change_database,
             "A database connection is required to select last due assignment.")
    @require('course_id', edit_courses,
             "A selected course is required to select last due assignment.")
    def select_last_due_assignment(self):
        """Select last due assignment.
           Selects the most recently due assignment in the current course, if any.
        """
        assignments = db.select_assignments(self.db_connection,
                                            course_id=self.course_id)
        most_recent = None
        current_date = datetime.date.today()
        past_assignments = [a for a in assignments
                            if a['due_date'] and
                               validators.date(a['due_date']) <= current_date]

        if not past_assignments:
            print("No assignments for this course have a due date in "
                  "the past; no current assignment is set.\n")
            self.assignment_id = None
            return
   
        most_recent = past_assignments[0] 
        most_recent_date = validators.date(most_recent['due_date'])
        for a in past_assignments:
            due_date = validators.date(a['due_date'])
            if due_date > most_recent_date:
                most_recent = a
                most_recent_date = due_date

        self.assignment_id = most_recent['id']

           
    @require('db_connection', change_database,
             "A database connection is required to enter grades.")
    @require('course_id', edit_courses,
             "A selected course is required to enter grades.")
    @require('assignment_id', edit_assignments,
             "A selected assignment is required to enter grades.")
    def enter_grades(self):
        """Enter grades.
           Enter grades for the current assignment for individual students.
        """
        grade_type = db.select_assignments(self.db_connection,
                                           assignment_id=self.assignment_id)[0]['grade_type']
        grade_validator = validators.validator_for_grade_type(grade_type)
        
        print("")
        print("Use Control-C to finish entering grades.")
        while True:
            try:
                student = self.get_student()
                # avoid entering grades for non-member students:
                try:
                    membership = db.ensure_unique(db.select_course_memberships(
                            self.db_connection,
                            course_id=self.course_id,
                            student_id=student['id']))
                except db.NoRecordsFound:
                    course = db.select_courses(self.db_connection,
                                               course_id=self.course_id)[0]
                    print("{student} is not a member of {course}".format(
                            student=self.student_formatter(student),
                            course=self.course_formatter(course)))
                    # offer to add to course, but don't refuse to continue if not
                    if typed_input("Add this student to the course? (Y/N) ", yn_bool):
                        db.create_course_member(self.db_connection,
                                                student_id=student['id'],
                                                course_id=self.course_id)
                    else:
                        print("WARNING: grades for this student will not be "
                              "calculated or reported unless you add him or her "
                              "to the course later.")
                           
                grade_id = None
                grade_val = typed_input("Enter grade value: ", grade_validator)
                existing_grades = db.select_grades(self.db_connection,
                                                   student_id=student['id'],
                                                   course_id=self.course_id,
                                                   assignment_id=self.assignment_id)
                if existing_grades:
                    print("Student has existing grades for this assignment.")
                    print("Existing grades are: %s" % ", ".join(
                            str(g['value']) for g in existing_grades))
                    update = typed_input("Update/overwrite? (Y/N) ", yn_bool)
                    if update:
                        if len(existing_grades) == 1:
                            print("Will update existing grade.")
                            grade = existing_grades[0]
                        else:
                            grade = self.options_menu(
                                "Select a grade to update.",
                                existing_grades,
                                # TODO: show timestamp?
                                lambda g: "{0}: {1}".format(
                                    g['assignment_name'],
                                    g['value']))
                        grade_id = grade['id']

                db.create_or_update_grade(self.db_connection,
                                          grade_id=grade_id,
                                          assignment_id=self.assignment_id,
                                          student_id=student['id'],
                                          value=grade_val)
                                          
            except KeyboardInterrupt:
                print("")
                break
            # TODO: shortcut here for changing to another assignment?
            # enter_grades_for_student method? (for a single student across all course assignments)

    @require('db_connection', change_database,
             "A database connection is required to edit grades.")
    @require('course_id', edit_courses,
             "A selected course is required to edit grades.")
    def edit_grades(self):
        """Edit grades.
           Edit a table of grades for the current course.
        """
        # TODO: handle case where student has multiple grades for an
        # assignment. Presently these are silently dropped in the
        # display, but when editing, user is asked to enter new grades
        # multiple times.
        def formatter(tbl_row):
            return row_fmt.format(name=self.student_formatter(tbl_row['student']),
                                  **dict((g['assignment_name'], str(g['value']))
                                         for g in tbl_row['grades']))

        def editor(tbl_row):
            print("Editing grades for %s." % self.student_formatter(tbl_row['student']))
            
            prompt = "New grade value for %s (default: %s): "
            any_updates = False
            for g in tbl_row['grades']:
                grade_validator = validators.validator_for_grade_type(g['grade_type'])
                old_val = g['value']
                # TODO: user can get stuck in a loop here if there is no existing
                # grade value but user doesn't want to enter one, because typed_input
                # will requery when default is None.  WONTFIX for now, because this
                # is an edge case, because it is easily (and correctly) escaped via
                # Control-C, and because generally, user should just enter the grade.
                new_val = typed_input(prompt % (g['assignment_name'], old_val),
                                      grade_validator, default=old_val)
                if new_val == old_val:
                    continue
                elif new_val:
                    any_updates = True
                    new_grade_id = db.create_or_update_grade(
                        self.db_connection,
                        student_id=g['student_id'],
                        assignment_id=g['assignment_id'],
                        grade_id=g['grade_id'], # may be None if grade didn't exist
                        value=new_val)

            if any_updates:
                return {
                    'student': tbl_row['student'],
                    'grades': db.select_grades_for_course_members(
                        self.db_connection,
                        course_id=self.course_id,
                        student_id=tbl_row['student']['id'])
                    }
            else:
                return tbl_row

            
        students = db.select_students(self.db_connection,
                                      course_id=self.course_id)
        all_grades = db.select_grades_for_course_members(
            self.db_connection,
            course_id=self.course_id)
        rows = [
            {'student': s,
             'grades': [r for r in all_grades if r['student_id'] == s['id']]}
            for s in students]

        # we use select_assignments here because it orders the
        # assignments by due date
        assignments = db.select_assignments(self.db_connection,
                                            course_id=self.course_id)
        assignment_names = [a['name'] for a in assignments]
        row_fmt = "{name: <40s}  "
        for a in assignment_names:
            row_fmt += "{" + a + ": <10s}"
        
        header = row_fmt.format(name="Student",
                                **dict((a,a) for a in assignment_names))
    
        self.edit_table(rows, header, formatter, editor=editor,
                        entity_type='grades for student')
        print("Grades updated successfully.")

    @require('db_connection', change_database,
             "A database connection is required to import students.")
    @require('course_id', edit_courses,
             "A selected course is required to import students.")
    def import_students(self):
        """Import students.
           Import students from a CSV file as members of the current course.
        """
        csv_path = typed_input("Enter path to CSV file with student data to import: ", file_path)
        if not os.path.exists(csv_path):
            retry = typed_input("File %s does not exist; try again? (Y/N) " %
                                csv_path, yn_bool)
            if retry:
                return self.import_students()
            else:
                return None

        # assume, for now, that CSV files have been generated by bSpace:
        students = bspace.roster_csv_to_students(csv_path)
        formatter = lambda s: "{last_name: <15s} {first_name: <20s} {email: <30s} {sid: <8}".format(**s)
        editor = lambda s: self.edit_student_dict(from_dict=s)
        creator = self.edit_student_dict
        header = formatter({'last_name': "Last name", 'first_name': "First name",
                            'email': "Email", 'sid': "SID"})
        students = self.edit_table(students, header, formatter,
                                   editor=editor, creator=creator,
                                   deleter=lambda s: True)

        for s in students:
            try:
                s['student_id'] = db.get_student_id(self.db_connection,
                                                    sid=s['sid'],
                                                    first_name=s['first_name'],
                                                    last_name=s['last_name'])
            except db.NoRecordsFound:
                s['student_id'] = None

            student_id = db.create_or_update_student(
                self.db_connection,
                sid=s['sid'],
                first_name=s['first_name'],
                last_name=s['last_name'],
                email=s['email'])
            course_member_id = db.create_course_member(
                self.db_connection,
                student_id=student_id,
                course_id=self.course_id)

        print("%d students imported successfully." % len(students))

    @require('db_connection', change_database,
             "A database connection is required to edit students.")
    def edit_student(self):
        """Add or edit students.
           Lookup students and modify their contact data and course memberships.
        """
        self.actions_menu(
            "What do you want to do?",
            [self.edit_student_info,
             self.edit_student_courses,
             self.edit_course_members])
 
    @require('db_connection', change_database,
             "A database connection is required to edit student information.")
    def edit_student_info(self):
        """Edit student contact data.
           Change name, SID, email, etc. for a single student.
        """
        # ugly hack: check result of get_student against list of existing students
        # to avoid asking user to enter student data 3(!) times (to search, create, edit)
        all_student_ids = [s['id'] for s in db.select_students(self.db_connection)]
        student = self.get_student(create=True)
        if student['id'] in all_student_ids:
            # this was an existing student, so run the editor:
            d = self.edit_student_dict(from_row=student)
            student_id = db.create_or_update_student(self.db_connection, **d)
        else:
            # this student was just created, so skip the editor;
            # get_student already gave user a chance to confirm data
            pass
        
        print("Student information updated.")

    @require('db_connection', change_database,
             "A database connection is required to edit course memberships.")
    def edit_student_courses(self):
        """Edit student courses.
           Add or remove a single student from one or more courses.
        """
        student = self.get_student()
        def add_to_course():
            all_courses = db.select_courses(self.db_connection)
            current_courses = db.select_courses(self.db_connection,
                                                student_id=student['id'])
            options = [c for c in all_courses if c not in current_courses]
            if not options:
                print("\nThis student is already enrolled in every course.")
                return None
            course = self.options_menu(
                "Which course should the student be added to?",
                options,
                self.course_formatter,
                allow_none=True)
            if course:
                course_id = course['id']
                db.create_course_member(self.db_connection,
                                        student_id=student['id'],
                                        course_id=course_id)
                print("Student added to %s" % self.course_formatter(course))
            else:
                print("Student not added to course.")
                
            return course
                
        def remove_from_course(course):
            course_id = course['id']
            db.delete_course_member(self.db_connection,
                                    student_id=student['id'],
                                    course_id=course_id)
            print("Student deleted from %s" % self.course_formatter(course))
            return True

        current_courses = db.select_courses(self.db_connection,
                                            student_id=student['id'])
        self.edit_table(
            current_courses,
            "Current courses for %s" % self.student_formatter(student),
            self.course_formatter,
            creator=add_to_course,
            deleter=remove_from_course)

        print("Student course memberships updated.")
        
    @require('db_connection', change_database,
             "A database connection is required to edit students in course.")
    @require('course_id', edit_courses,
             "A selected course is required to edit students in course.")
    def edit_course_members(self):
        """Edit course enrollments.
           Add or remove one or more students in the current course.
        """
        def add_to_course():
            student = self.get_student(create=True)
            db.create_course_member(self.db_connection,
                                    student_id=student['id'],
                                    course_id=self.course_id)
            print("Added %s to course." %
                  self.student_formatter(student))
            return student
            
        def remove_from_course(student):
            student_id = student['id']
            db.delete_course_member(self.db_connection,
                                    student_id=student_id,
                                    course_id=self.course_id)
            print("Deleted student %s from course." %
                  self.student_formatter(student))
            return True

        current_students = db.select_students(self.db_connection,
                                              course_id=self.course_id)
        current_course = db.select_courses(self.db_connection,
                                           course_id=self.course_id)[0]
        self.edit_table(
            current_students,
            "Current students in %s" % self.course_formatter(current_course),
            self.student_formatter,
            creator=add_to_course,
            deleter=remove_from_course,
            entity_type="student's membership")
        print("Course enrollments updated.")
 
    def import_grades(self):
        pass

    @require('db_connection', change_database,
             "A database connection is required to export grades.")
    @require('course_id', edit_courses,
             "A selected course is required to export grades.")
    def export_grades(self):
        """Export grades.
           Export grades for the current course to a CSV file.
        """
        out_file_name = typed_input("Enter a path to CSV file to export grades: ", file_path)
        if os.path.exists(out_file_name):
            print("Warning: file %s exists." % out_file_name)
            overwrite = typed_input("Overwrite? (Y/N) ", yn_bool)
            if not overwrite:
                print("Abort.")
                return

        out_file = open(out_file_name, 'w')
        
        # format, for now:
        # last_name + first_name, sid, grade1, grade2, grade3...
        # we use select_assignments here because it orders the
        # assignments by due date
        assignments = db.select_assignments(self.db_connection,
                                            course_id=self.course_id)
        assignment_names = [a['name'] for a in assignments]
        header = ["Name", "SID"] + assignment_names
        writer = csv.DictWriter(out_file, header)
        
        students = db.select_students(self.db_connection,
                                      course_id=self.course_id)

        # writeheader() became available in Python 2.7:
        try:
            writer.writeheader()
        except AttributeError:
            writer.writerow(dict(zip(header,header)))

        all_grades = db.select_grades_for_course_members(
            self.db_connection,
            course_id=self.course_id)
        
        for s in students:
            row = {}
            row["Name"] = "%s, %s" % (s['last_name'], s['first_name'])
            row["SID"] = s['sid']
            grades = [r for r in all_grades if r['student_id'] == s['id']]
            for g in grades:
                assignment_name = g['assignment_name']
                if assignment_name not in row:
                    row[assignment_name] = g['value']
                else:
                    print("Warning: multiple grades found for student %s "
                          "for assignment %s; only exporting first result."
                          % (self.student_formatter(s), assignment_name))
                    continue
            
            try:
                writer.writerow(row)
            except IOError:
                print("Warning: could not write row to CSV: %r." % row)
                continue

        out_file.close()
        print("Grades exported successfully to: %s.\n" % out_file_name)
                
    @require('db_connection', change_database,
             "A database connection is required to calculate grades.")
    @require('course_id', edit_courses,
             "A selected course is required to calculate grades.")
    def calculate_grades(self):
        """Calculate grades.
           Run the (user-defined) grade calculation function for students in the
           current course.
        """
        def save_calculated_grade(student_id,
                                  name='', # required, unless grade_id or assignment_id given
                                  value='', # required
                                  # to update an existing grade:
                                  grade_id=None,
                                  # to add a grade for an existing assignment:
                                  assignment_id=None, 
                                  # to create a new assignment:
                                  description='(Assignment for calculated grade)',
                                  due_date=datetime.date.today(),
                                  grade_type=None,
                                  weight='CALC'):
            if not name and not (assignment_id or grade_id):
                raise ValueError("No assignment name given for calculated grade.")
            if value is None: # missing values not allowed, but 0/False/etc. OK
                raise ValueError("No value given for calculated grade %s." % name)

            if grade_id:
                db.update_grade(self.db_connection,
                                student_id=student_id,
                                grade_id=grade_id,
                                value=value)
                return grade_id

            if not assignment_id:
                try:
                    assignment_id = db.ensure_unique(db.select_assignments(
                        self.db_connection,
                        course_id=self.course_id,
                        name=name))
                except db.NoRecordsFound:
                    assignment_id = db.create_assignment(
                        self.db_connection,
                        course_id=self.course_id,
                        name=name,
                        description=description,
                        grade_type=grade_type,
                        due_date=due_date,
                        weight=weight)
                # MultipleRecordsFound should propagate
                
            # avoid storing calculated grades multiple times
            try:
                grade_id = db.ensure_unique(
                    db.select_grades(self.db_connection,
                                     student_id=student_id,
                                     assignment_id=assignment_id))
            except db.NoRecordsFound:
                grade_id = None
                                            
            row_id = db.create_or_update_grade(
                self.db_connection,
                student_id=student_id,
                assignment_id=assignment_id,
                grade_id=grade_id,
                value=value)

            return row_id
        
                                  
        course = db.select_courses(self.db_connection,
                                   course_id=self.course_id)[0]
        safe_num = course['number'].replace('-', '_').replace('.', '_')
        calc_name = ('calculate_grade_' + safe_num + '_' +
                     course['semester'].lower() + str(course['year']))
        calc_func = getattr(user_calculators, calc_name, None)

        if not calc_func:
            print("Could not locate grade calculation function %s. "
                  "Have you written it?" % calc_name)
            print("")
            return

        students = db.select_students(self.db_connection,
                                      course_id=self.course_id)
        all_grades = db.select_grades_for_course_members(
                self.db_connection,
                course_id=self.course_id)
        
        for s in students:
            grades = [r for r in all_grades
                      if (r['student_id'] == s['id'] and r['weight'] != 'CALC')]

            try:
                calculated_grades = calc_func(grades)
            except Exception as e:
                print("Failed to calculate grades for %s. "
                      "Error was: %s.  Skipping..." %
                      (self.student_formatter(s), e))
                continue
            if type(calculated_grades) is dict:
                # transpose to the list format to use save_calculated_grades
                calculated_grades = [
                    {'name': k, 'value': v}
                    for k, v in calculated_grades.items()]

            for cg in calculated_grades:
                save_calculated_grade(s['id'], **cg)

        print("Grade calculations ran successfully.\n")

    @require('db_connection', change_database,
             "A database connection is required to view a grade report.")
    @require('course_id', edit_courses,
             "A selected course is required to view a grade report.")
    def grade_report(self):
        """View grade report.
           See a report on grades in the current course."""
        r = reports.GradeReport(self.db_connection, course_id=self.course_id)
        r.run()
        print(r.as_text(compact=True))
        if typed_input("See and save the full report? (Y/N): ", yn_bool):
            # TODO: support for pager program?
            full_report = r.as_text(compact=False)
            print(full_report)
            
            course = db.select_courses(self.db_connection,
                                       course_id=self.course_id)[0]
            name = "grade_report_{number}_{semester}_{year}-".format(**course)
            with tempfile.NamedTemporaryFile(prefix=name, delete=False) as t:
                try:
                    # 3.x
                    report_bytes = full_report.encode("utf-8")
                except AttributeError:
                    # 2.x
                    report_bytes = full_report
                t.write(report_bytes)
                print("Full report saved at: %s\n" % t.name)

    def exit(self):
        """Quit grader.
           Closes database connection and exits."""
        self.close_database()
        exit(0)
        
    # Helper methods:
    def actions_menu(self, query, actions, default=None, escape=None):
        """Present a menu of actions to the user.
           query should be a string to print before the list of actions.
           actions should be a sequence callables.
             The docstring of each action is used to provide its menu entry.
           default, if provided, should be a callable to call if the user
             makes no selection
           escape, if provided, should be a callable that returns the user
             to a previous menu.
           Returns the return value of the selected action.
        """
        # TODO: add support for arguments to actions?
             
        if escape:
            actions = list(actions) + [escape]
        
        menu_format = "{0:>3d}: {1: <30} {2: <40}"
        short_descs = []
        long_descs = []
        for a in actions:
            lines = a.__doc__.splitlines()
            short_descs.append(lines[0])
            long_descs.append(' '.join([l.strip() for l in lines[1:]]))

        print("")
        print(query)
        print("Please select one of the following actions:")
        for i, a in enumerate(actions):
            print(menu_format.format(i, short_descs[i], long_descs[i]))

        if default is not None:
            prompt = "Which action? (default %d): " % actions.index(default)
        else:
            prompt = "Which action? (enter a number): "

        validator = lambda s: validators.int_in_range(s, 0, len(actions))
        i = typed_input(prompt, validator,
                        default=actions.index(default) if default in actions else None)
        print("") # visually separate menu and selection 
        
        return actions[i]()

    def options_menu(self, query, options, formatter,
                     escape=None, allow_none=False):
        """Present a menu of options to the user.
           query should be a string to print before the list of options
           options should be a list of values
           formatter should be a callable that returns a string
             representation of a given option.
           escape, if provided, should be a callable to run in lieu of returning
             a selected value
           allow_none, if true, will add an option for the user to make no selection.
           Returns the selected option or None.
        """
        print("")
        print(query)
        menu_format = "{0:>3d}: {1}"
        max_index = len(options) - 1
        escape_option = None
        none_option = None
        for i, o in enumerate(options):
            print(menu_format.format(i, formatter(o)))
        if escape:
            escape_option = max_index 
            max_index += 1
            print(menu_format.format(max_index, escape.__doc__.splitlines()[0]))
        if allow_none:
            # TODO: something wrong with logic here; escape doesn't work
            none_option = max_index
            max_index += 1
            print(menu_format.format(max_index, "None of the above"))

        validator = lambda s: validators.int_in_range(s, 0, max_index+1)
            
        idx = typed_input("Which option? (enter a number): ", validator)
        print("") # visually separate menu and selection input 
        
        if idx < len(options):
            return options[idx]
        elif idx == escape_option:
            return escape()
        elif idx == none_option:
            return None

    def edit_table(self, rows, header, formatter, editor=None,
                   creator=None, deleter=None, selector=None, entity_type='row'):
        """Present a simple interface for reviewing and editing tabular data.
           rows should be a sequence of values for the user to review and edit
           header should be a string to print above the table
           formatter should be a function which, given a row value, returns a
             string representing the row for display to the screen
           editor, if provided, should be a function which, given a row value,
             returns a new row value based on user input
           creator, if provided, should be a function with no arguments which
             returns a new row value based on user input  
           deleter, if provided, should be a function to call for its side
             effects with the row value when the user deletes a row.
             It should return False if deletion was aborted or unsuccessful,
             and a true value otherwise.
           selector, if provided, should be a function to call for its side
             effects with the row value when the user selects a row to be the
             currently-selected value (e.g., current assignment or course).
             It should return True if this function should exit after a selection
             is made, False otherwise.
           entity_type, if provided, will be used instead of the generic name 'row'
             when displaying the prompts for selecting, editing, creating, etc.
           Returns the edited rows.
        """
        editable_rows = [r for r in rows]
        header_underline = "-".ljust(80, "-")
        row_format = "{index: >5}: {frow: <73s}"
        def validator(s):
            s = s.strip().lower()
            if s.startswith('d'):
                action = 'd'
                idx = validators.int_in_range(s[1:], 0, len(editable_rows)+1)
            elif s.startswith('e'):
                action = 'e'
                idx = validators.int_in_range(s[1:], 0, len(editable_rows)+1)
            elif s.startswith('c'):
                action = 'c'
                idx = None
            else:
                action = 's'
                idx = validators.int_in_range(s, 0, len(editable_rows)+1)
            return action, idx
                
        while True:
            try:
                print("")
                print(row_format.format(index='Row #', frow=header))
                print(header_underline)
                if editable_rows:
                    for i, r in enumerate(editable_rows):
                        print(row_format.format(index=i, frow=formatter(r)))
                else:
                    print("(No %s data yet.)" % entity_type)

                print("")
                prompt = "Press Ctrl-C to end.\n"
                if creator:
                    prompt += "Enter 'c' to create a new %s. " % entity_type
                if editor:
                    prompt += "Prefix row # with 'e' to edit %s. " % entity_type
                if deleter:
                    prompt += "Prefix row # with 'd' to delete %s. " % entity_type
                if selector:
                    prompt += ("\nEnter row # to select as current %s. " %
                               entity_type)
                prompt += "\nWhat do you want to do? "
                    
                action, idx = typed_input(prompt, validator)
                if action == 'e' and editor:
                    new_row = editor(editable_rows[idx])
                    if new_row: # editor might return None
                        editable_rows[idx] = new_row
                elif action == 'd' and deleter:
                    success = deleter(editable_rows[idx])
                    if success:
                        editable_rows.pop(idx)
                    else:
                        print("Deletion unsuccessful.")
                elif action == 'c' and creator: 
                    new_row = creator()
                    if new_row: # creator might return None
                        editable_rows.append(new_row)
                elif action == 's' and selector:
                    should_exit = selector(editable_rows[idx])
                    if should_exit:
                        return editable_rows
                    
            except KeyboardInterrupt:
                print("")
                break

        return editable_rows

    def edit_dict(self, d, validators=None, skip=None):
        """Simple interface for editing the values in a dictionary.
           Queries the user for a new value for each key in d, then
             updates the dictionary with a new validated value.
           d should be a dictionary of values with strings as keys
             The keys will be pretty printed, split along '_', when
             querying the user for new values.
           validators, if given, should be a dictionary mapping keys
             of d to functions validating input; str() will be used
             as a default validator if none is provided for a given key
           skip, if given, should be a list of keys in d to skip
             querying the user for
           Returns the updated dictionary.
        """
        if not validators:
            validators = {}
        if not skip:
            skip = []

        for k, v in d.items():
            if k in skip:
                continue
            
            validator = validators.get(k, str)
            pretty_field = ' '.join([word.strip().lower()
                                     for word in k.split('_')])
            pretty_current = (" (default: %s): " % v) if v else ": "
            new_v = typed_input("Enter %s%s" % (pretty_field, pretty_current),
                                validator, default=v)
            if new_v:
                d[k] = new_v

        return d

    def edit_student_dict(self, from_dict=None, from_row=None):
        """Convenience wrapper for edit_dict for student data.
           from_row, if provided, should be a row from the students table,
             with at least the following columns: 
             id, last_name, first_name, sid, email
           from_dict, if provided, should have keys:
             last_name, first_name, sid, email
           You may not pass both from_row and from_dict; but you may pass
             neither.  In that case, the user will have to enter all fields.
           Returns a dictionary suitable to pass to *_student database
             functions as kwargs, with keys:
             student_id, last_name, first_name, sid, email
        """
        if from_dict and from_row:
            raise ValueError("You may not pass both from_dict and from_row")

        db_fields = ['student_id', 'last_name', 'first_name', 'sid', 'email']
        vlds = {'last_name': validators.name, 'first_name': validators.name,
                'sid': validators.sid, 'email': validators.email}
        d = {}
        for f in db_fields:
            if from_row:
                # student_id field comes from db as 'id' column
                d[f] = from_row[f if f != 'student_id' else 'id']
            elif from_dict:
                d[f] = from_dict.get(f, None)
            else:
                d[f] = None
                
        return self.edit_dict(d, validators=vlds, skip=['student_id'])
        
    def print_course_info(self):
        "Prints information about the currently selected course"
        if self.course_id:
            course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
            print("Current course is: %s" % self.course_formatter(course))
        else:
            print("No course selected")
           
    def print_assignment_info(self):
        "Prints information about the currently selected assignment"
        if self.assignment_id:
            assignment = db.select_assignments(self.db_connection,
                                               assignment_id=self.assignment_id)[0]
            print("Current assignment is: %s" % self.assignment_formatter(assignment))
        else:
            print("No assignment selected")

    def print_db_info(self):
         "Prints information about the database connection"
         if self.db_connection:
             print("Database open at %s" % self.db_file)
         else:
             print("No current database connection")

        
            
#
# Utilities
# 
def typed_input(prompt1, constructor, prompt2=None, default=None):
    """Get input and convert it to a given type.
       prompt1 should be an initial prompt for the user
       constructor should be a callable that converts a string
         to a value of the desired type or raises ValueError
       prompt2, if provided, should be a second prompt to use when
         the user provides an unacceptable value
       default, if provided, should be a default value to use when the
         user provides no input
    """
    if not prompt2:
        prompt2 = prompt1

    prompt = prompt1
    val = None
    while val is None:
        try:
            s = input(prompt)
            if not s and default is not None:
                val = default
            else:
                val = constructor(s)
        except ValueError:
            prompt = prompt2
            continue

    return val

#
# Constructors/validators
# 
def file_path(s):
    """Convert a string to a file path.
       The passed string may contain '~' and will be expanded to an absolute
       path."""
    fp = s.strip()
    if not fp:
        raise ValueError("File path may not be empty")
    return os.path.abspath(os.path.expanduser(fp))

def yn_bool(s):
    """Convert a yes/no string to a boolean.
       Strings beginning with 'Y' and 'y' return True, with 'N' and 'n' return False."""
    b = s and s.strip().upper()[0]
    if b == 'Y':
        return True
    elif b == 'N':
        return False
    else:
        raise ValueError("Expected 'Y' or 'N': %s" % s)

