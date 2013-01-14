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

import os, sqlite3

from schoolutils.config import user_config, user_calculators
from schoolutils.grading import db

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
                print ""
                print message
                callback(self)
                attr = getattr(self, attribute, None)
            return f(self, *args, **kwargs)
        method.__doc__ = f.__doc__  # preserve docstring for actions_menu  
        return method
    return method_factory

class BaseUI(object):
    def __init__(self):
        self.db_file = file_path(user_config.gradedb_file)
        if self.db_file and os.path.exists(self.db_file):
            self.db_connection = sqlite3.connect(self.db_file)
        else:
            self.db_connection = None
        
        self.semester = user_config.current_semester 
        self.year = user_config.current_year 
        self.current_courses = user_config.current_courses

        self.course_id = None
        self.assignment_id = None
        self.student_id = None

        if user_config.default_course[0] and self.db_connection:
            self.set_default_course()
        if user_config.default_assignment and self.db_connection:
            self.set_default_assignment()
            
    def set_default_course(self):
        "Set course_id using user_config.default_course"
        # TODO: course_id should also be settable via command line option
        # TODO: fallback: if current_year and current_semester determine a unique
        # course, use that
        sem, yr, num = user_config.default_course
        try:
            self.course_id = db.ensure_unique(db.select_courses(self.db_connection,
                                                                semester=sem,
                                                                year=yr,
                                                                number=num))
        except (AttributeError, db.NoRecordsFound, db.MultipleRecordsFound):
            # AttributeError covers case where self.db_connection uninitialized
            sys.stderr.write("Unable to locate a unique default course;"
                             "ignoring.\n")
            
            
    def set_default_assignment(self):
        "Set assignment_id using user_config.default_assignment"
        # TODO: assignment_id should also be settable via command-line option
        try:
            self.assignment_id = db.ensure_unique(
                db.select_assignments(self.db_connection,
                                      course_id=self.course_id,
                                      name=user_config.default_assignment))
        except (AttributeError, db.NoRecordsFound, db.MultipleRecordsFound):
            # AttributeError covers case where self.db_connection uninitialized
            sys.stderr.write("Unable to locate a unique default assignment;"
                             "ignoring.\n")
        

class SimpleUI(BaseUI):
    """Manages a simple (command line) user interface.
    """
    # Helpers for printing data to stdout
    STUDENT_FORMAT = '{last_name}, {first_name} (SID: {sid})'
    COURSE_FORMAT = '{number}: {name} ({semester} {year})'
    ASSIGNMENT_FORMAT = '{name} (due {due_date})'
    GRADE_FORMAT = '' # TODO

    def course_formatter(self, course_row):
        "Format COURSE_FORMAT with course from db"
        return self.COURSE_FORMAT.format(year=course_row[3], semester=course_row[4],
                                         number=course_row[2], name=course_row[1])

    def student_formatter(self, student_row):
        "Format STUDENT_FORMAT with student from db"
        return self.STUDENT_FORMAT.format(last_name=student_row[1],
                                          first_name=student_row[2],
                                          sid=student_row[3])

    def assignment_formatter(self, assignment_row):
        return self.ASSIGNMENT_FORMAT.format(name=assignment_row[2],
                                             due_date=assignment_row[3])

    def grade_formatter(self, grade_row):
        pass
   
    # Actions which can be @require-d: 
    def close_database(self):
        """Close the current database connection."""
        if self.db_connection:
            print "Closing current database located at: %s" % self.db_file
            self.db_connection.commit()
            self.db_connection.close()
            self.db_connection = None
            self.db_file = None
            # these fields will now be invalid, so erase them too:
            self.course_id = None
            self.assignment_id = None
            self.student_id = None

            
    def change_database(self):
        """Open a new database.
           Closes the current database connection (if any) and opens another."""
        if self.db_connection:
            self.close_database()
        
        db_path = typed_input("Enter path to grade database: ", file_path)
        if not os.path.exists(db_path):
            create = typed_input(
                "No existing database at %s.  Create (Y/N)? " % db_path,
                yn_bool)
            if create:
                self.db_file = db_path
                self.db_connection = sqlite3.connect(db_path)
                db.gradedb_init(self.db_connection)
            else:
                return None
        else:
            self.db_file = db_path
            self.db_connection = sqlite3.connect(db_path)

            
    def get_student(self, create=False):
        """Lookup a student in the database, trying several methods.
           If create is True, allow (and offer) creating a new student using
             entered criteria if none exists.
           Returns student row and sets self.student_id.
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
                print "%d students found." % len(students)
                
        def students_menu(students):
            "Select a student (or None) from a menu"
            return self.options_menu(
                "Select a student:",
                students, 
                self.student_formatter,
                allow_none=create)
               
        students = []
        try:
            print ("Enter student data to lookup or create student. "
                   "Search uses fuzzy matching on name and email fields.\n"
                   "Use Ctrl-C to stop search and select from list.")
            sid = typed_input("Enter SID: ", db.sid, default='')
            students = db.select_students(self.db_connection, sid=sid)
            quit_if_unique(students)

            last_name = typed_input("Enter last name: ", db.name, default='')
            students = db.select_students(self.db_connection,
                                          sid=sid,
                                          last_name=last_name,
                                          fuzzy=True)
            quit_if_unique(students)
            
            first_name = typed_input("Enter first name: ", db.name, default='')
            students = db.select_students(self.db_connection,
                                          sid=sid,
                                          last_name=last_name,
                                          first_name=first_name,
                                          fuzzy=True)
            quit_if_unique(students)

            email = typed_input("Enter email: ", db.email, default='')
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
            print "Please provide data for the student to be created:"
            vals = self.edit_student_dict(from_dict=vals)
            vals.pop('student_id') # we're creating a new record
            student_id = db.create_student(self.db_connection, **vals)
            student = db.select_students(self.db_connection,
                                         student_id=student_id)[0]
        else:
            print "Could not locate student with these criteria; please try again."
            return self.get_student(create=create)

        print "Selected: %s" % self.student_formatter(student)
        self.student_id = student[0]
        return student

    # Top-level actions:       
    @require('db_connection', change_database, "")
    def main_loop(self):
        "Main menu"
        while True:
            self.print_db_info()
            self.print_course_info()
            self.print_assignment_info()
            self.actions_menu(
                "Main menu.",
                [self.change_database,
                 self.change_course,
                 self.change_assignment,
                 self.import_students,
                 self.edit_student,
                 self.enter_grades,
                 self.calculate_grades,
                 #self.import_grades,
                 #self.export_grades,
                 self.exit])

           
    @require('db_connection', change_database,
             "A database connection is required to change the current course.")
    def change_course(self):
        """Change current course.
           Select an existing course from the database, or add a new one.
        """
        # TODO: add support for selecting from user_config.current_courses
        self.print_course_info()
        self.actions_menu("What do you want to do?",
                        [self.select_course,
                         self.create_course])

        
    @require('db_connection', change_database,
             "A database connection is required to select a course.")
    def select_course(self):
        """Select an existing course.
           Lookup an existing course in the database by semester, name, or number.
        """
        print "(Press Enter to skip a given search criterion)"
        year = typed_input("Enter year: ", db.year, default='') or None
        semester = typed_input("Enter semester: ", db.semester, default='') or None
        course_num = typed_input("Enter course number: ", str) or None
        course_name = typed_input("Enter course name: ", str) or None

        courses = db.select_courses(self.db_connection,
                                    year=year, semester=semester,
                                    name=course_name, number=course_num)
                                   
        if len(courses) == 1:
            course = courses[0]
            print "Found 1 course; selecting: %s" % self.course_formatter(course)
            self.course_id = course[0]
        elif len(courses) == 0:
            print "No courses found matching those criteria; please try again."
            return self.change_course()
        else:
            course = self.options_menu(
                "Multiple courses found; please select one:",
                courses, self.course_formatter, allow_none=True)
            if course:
                print "Selected: %s" % self.course_formatter(course)
                self.course_id = course[0]

                
    @require('db_connection', change_database,
             "A database connection is required to create a course")
    def create_course(self):
        """Create a new course.
           Add a new course to the database and select it as the current
           course.
        """
        year = typed_input("Enter year: ", db.year)
        semester = typed_input("Enter semester: ", db.semester)
        course_num = typed_input("Enter course number: ", str)
        course_name = typed_input("Enter course name: ", str)

        course_id = db.create_course(
            self.db_connection,
            year=year, semester=semester,
            name=course_name, number=course_num)

        self.course_id = course_id

        
    @require('db_connection', change_database,
             "A database connection is required to change the current assignment.")
    def change_assignment(self):
        """Change current assignment.
           Select an existing assignment from the database, or add a new one.
        """
        self.print_assignment_info()
        self.actions_menu("What do you want to do?",
            [self.select_assignment, self.create_assignment])

        
    @require('db_connection', change_database,
             "A database connection is required to select an assignment.")
    @require('course_id', change_course,
             "A selected course is required to select an assignment.")
    def select_assignment(self):
        """Select an assignment.
           Lookup an existing assignment in the database.
        """
        assignments = db.select_assignments(self.db_connection,
                                            course_id=self.course_id)
        if len(assignments) == 0:
            create = typed_input(
                "No assignments found for the current course.  Create? (Y/N) ",
                yn_bool)
            if create:
                return self.create_assignment()
            else:
                print "No assignment selected or created."
        else:
            assignment = self.options_menu(
                "Select an assignment for this course:",
                assignments, self.assignment_formatter,
                escape=self.create_assignment, allow_none=True)
            if assignment:
                self.assignment_id = assignment[0]
                
            
    @require('db_connection', change_database,
             "A database connection is required to create an assignment.")
    @require('course_id', change_course,
             "A selected course is required to create an assignment.")
    def create_assignment(self):
        """Create a new assignment.
           Add a new assignment to the database and select it as the current assignment.
        """
        name = typed_input("Enter assignment name: ", str)
        description = typed_input("Enter description: ", str, default='')
        due_date = typed_input("Enter due date (YYYY-MM-DD): ", db.date)
        grade_type = typed_input("Enter grade type: ", str)
        weight = typed_input("Enter weight (as decimal): ", float)

        self.assignment_id = db.create_assignment(
            self.db_connection,
            course_id=self.course_id,
            name=name, description=description, grade_type=grade_type,
            due_date=due_date, weight=weight)

        
    @require('db_connection', change_database,
             "A database connection is required to enter grades.")
    @require('course_id', change_course,
             "A selected course is required to enter grades.")
    @require('assignment_id', change_assignment,
             "A selected assignment is required to enter grades.")
    def enter_grades(self):
        """Enter grades.
           Enter grades for the current assignment for individual students.
        """
        print ""
        print "Use Control-C to finish entering grades."
        while True:
            try:
                student_id, last_name, first_name, sid, _ = self.get_student()
                grade_id = None
                grade_val = typed_input("Enter grade value: ", str)
                existing_grades = db.select_grades(self.db_connection,
                                                   student_id=student_id,
                                                   course_id=self.course_id,
                                                   assignment_id=self.assignment_id)
                if existing_grades:
                    print "Student has existing grades for this assignment."
                    update = typed_input("Update/overwrite? (Y/N) ", yn_bool)
                    if update:
                        if len(existing_grades) == 1:
                            print "Will update existing grade."
                            grade = existing_grades[0]
                        else:
                            grade = self.options_menu(
                                "Select a grade to update.",
                                existing_grades,
                                lambda g: "{4}: {5}".format(*g))
                        grade_id = grade[0]

                db.create_or_update_grade(self.db_connection,
                                          grade_id=grade_id,
                                          assignment_id=self.assignment_id,
                                          student_id=student_id,
                                          value=grade_val)
                                          
            except KeyboardInterrupt:
                print ""
                break
            # TODO: shortcut here for changing to another assignment?
            # enter_grades_for_student method? (for a single student across all course assignments)

    @require('db_connection', change_database,
             "A database connection is required to import students.")
    @require('course_id', change_course,
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
                                   deleter=lambda s: None)

        for s in students:
            s.pop('full_name') # name should now be properly split into last/first
            try:
                s['student_id'] = db.get_student_id(self.db_connection,
                                                    sid=s['sid'],
                                                    first_name=s['first_name'],
                                                    last_name=s['last_name'])
            except db.NoRecordsFound:
                s['student_id'] = None

            student_id = db.create_or_update_student(
                self.db_connection, **s)
            course_member_id = db.create_course_member(
                self.db_connection,
                student_id=student_id,
                course_id=self.course_id)

        print "%d students imported successfully." % len(students)

    @require('db_connection', change_database,
             "A database connection is required to edit students.")
    def edit_student(self):
        """Add or edit students.
           Lookup students and modify their contact data and course memberships.
        """
        student = self.get_student(create=True)
            
        self.actions_menu(
            "What do you want to do?",
            [self.edit_student_info, self.edit_student_courses])
            
 
    @require('db_connection', change_database,
             "A database connection is required to edit student information.")
    @require('student_id', get_student,
             "A selected student is required to edit student information.")
    def edit_student_info(self):
        """Edit student contact data.
           Change name, SID, email, etc. for current student.
        """
        student = db.select_students(self.db_connection,
                                     student_id=self.student_id)[0]
        d = self.edit_student_dict(from_row=student)
        
        self.student_id = db.create_or_update_student(self.db_connection, **d)
        print "Student information updated."

    @require('db_connection', change_database,
             "A database connection is required to edit course memberships.")
    @require('student_id', get_student,
             "A selected student is required to edit course memberships.")
    def edit_student_courses(self):
        """Edit student courses.
           Add or remove current student from courses.
        """
        student = db.select_students(self.db_connection,
                                     student_id=self.student_id)[0]
        
        def add_to_course():
            all_courses = db.select_courses(self.db_connection)
            current_courses = db.select_courses(self.db_connection,
                                                student_id=self.student_id)
            options = filter(lambda c: c not in current_courses, all_courses)
            course = self.options_menu(
                "Which course should the student be added to?",
                options,
                self.course_formatter,
                allow_none=True)
            if course:
                course_id = course[0]
                db.create_course_member(self.db_connection,
                                        student_id=self.student_id,
                                        course_id=course_id)
                print "Student added to %s" % self.course_formatter(course)
            else:
                print "Student not added to course."
                
            return course
                
        def remove_from_course(course):
            course_id = course[0]
            db.delete_course_member(self.db_connection,
                                    student_id=self.student_id,
                                    course_id=course_id)
            print "Student deleted from %s" % self.course_formatter(course)

        current_courses = db.select_courses(self.db_connection,
                                            student_id=self.student_id)
        self.edit_table(
            current_courses,
            "Current courses for %s" % self.student_formatter(student),
            self.course_formatter,
            creator=add_to_course,
            deleter=remove_from_course)

        print "Student course memberships updated."
        

    def import_grades(self):
        pass

    def export_grades(self):
        pass

    @require('course_id', change_course,
             "A selected course is required to calculate grades.")
    def calculate_grades(self):
        """Calculate grades.
           Run the (user-defined) grade calculation function for students in the
           current course.
        """
        _, name, num, yr, sem = db.select_courses(self.db_connection,
                                                  course_id=self.course_id)[0]
        safe_num = num.replace('-', '_').replace('.', '_')
        calc_name = 'calculate_grade_' + safe_num + '_' + sem.lower() + str(yr)
        calc_func = getattr(user_calculators, calc_name, None)

        if not calc_func:
            print ("Could not locate grade calculation function %s. "
                   "Have you written it?" % calc_name)
            print ""
            return

        students = db.select_students(self.db_connection,
                                      course_id=self.course_id)
        assignments = db.select_assignments(self.db_connection,
                                            course_id=self.course_id)
        
        for s in students:
            grades = db.select_grades(self.db_connection,
                                      student_id=s[0],
                                      course_id=self.course_id)

            if len(grades) != len(assignments):
                # TODO: something more sophisticated here
                # skip? pass to grade function anyway? user-configurable behavior?
                print ("Warning: %s does not have a grade for all assignments "
                       "in this course." % self.student_formatter(s))
                
            grade_dict = calc_func(db.GradeDict(grades))
            grade_dict.save(self.db_connection)
            

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

        print ""
        print query
        print "Please select one of the following actions:"
        for i, a in enumerate(actions):
            print menu_format.format(i, short_descs[i], long_descs[i])

        if default is not None:
            prompt = "Which action? (default %d): " % actions.index(default)
        else:
            prompt = "Which action? (enter a number): "

        validator = lambda s: db.int_in_range(s, 0, len(actions))
        i = typed_input(prompt, validator,
                        default=actions.index(default) if default in actions else None)
        print "" # visually separate menu and selection 
        
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
        print ""
        print query
        menu_format = "{0:>3d}: {1}"
        max_index = len(options) - 1
        escape_option = None
        none_option = None
        for i, o in enumerate(options):
            print menu_format.format(i, formatter(o))
        if escape:
            escape_option = max_index 
            max_index += 1
            print menu_format.format(max_index, escape.__doc__.splitlines()[0])
        if allow_none:
            # TODO: something wrong with logic here; escape doesn't work
            none_option = max_index
            max_index += 1
            print menu_format.format(max_index, "None of the above")

        validator = lambda s: db.int_in_range(s, 0, max_index+1)
            
        idx = typed_input("Which option? (enter a number): ", validator)
        print "" # visually separate menu and selection input 
        
        if idx < len(options):
            return options[idx]
        elif idx == escape_option:
            return escape()
        elif idx == none_option:
            return None

    def edit_table(self, rows, header, formatter, editor=None,
                   creator=None, deleter=None):
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
             effects with the row value when the user deletes a row
           Returns the edited rows.
        """
        editable_rows = [r for r in rows]
        header_underline = "-".ljust(80, "-")
        row_format = "{index: >3}: {frow: <75s}"
        def validator(s):
            s = s.strip().lower()
            if s.startswith('d'):
                action = 'd'
                idx = db.int_in_range(s[1:], 0, len(editable_rows)+1)
            elif s.startswith('i'):
                action = 'i'
                idx = None
            else:
                action = 'e'
                idx = db.int_in_range(s, 0, len(editable_rows)+1)
            return action, idx
                
        while True:
            try:
                print row_format.format(index="Row", frow=header)
                print header_underline
                for i, r in enumerate(editable_rows):
                    print row_format.format(index=i, frow=formatter(r))

                print ""
                prompt = "Press Ctrl-C to end.\n"
                if editor:
                    prompt += "Enter row # to edit. " 
                if creator:
                    prompt += "Enter 'i' to insert a new row. "
                if deleter:
                    prompt += "Prefix row # with 'd' to delete. "
                prompt += "\nWhat do you want to do? "
                    
                action, idx = typed_input(prompt, validator)
                if action == 'e' and editor:
                    new_row = editor(editable_rows[idx])
                    if new_row: # editor might return None
                        editable_rows[idx] = new_row
                elif action == 'd':
                    to_delete = editable_rows.pop(idx)
                    if deleter:
                        deleter(to_delete)
                elif action == 'i' and creator: 
                    new_row = creator()
                    if new_row: # creator might return None
                        editable_rows.append(new_row)

            except KeyboardInterrupt:
                print ""
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

        for k, v in d.iteritems():
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
             formatted like:
             (student_id, last_name, first_name, sid, email)
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
        validators = {'last_name': db.name, 'first_name': db.name,
                      'sid': db.sid, 'email': db.email}
        d = {}
        for i, f in enumerate(db_fields):
            if from_row:
                d[f] = from_row[i]
            elif from_dict:
                d[f] = from_dict.get(f, None)
            else:
                d[f] = None
                
        return self.edit_dict(d, validators=validators, skip=['student_id'])
        
    def print_course_info(self):
        "Prints information about the currently selected course"
        if self.course_id:
            course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
            print "Current course is: %s" % self.course_formatter(course) 
        else:
            print "No course selected"
           
    def print_assignment_info(self):
        "Prints information about the currently selected assignment"
        if self.assignment_id:
            assignment = db.select_assignments(self.db_connection,
                                               assignment_id=self.assignment_id)[0]
            print "Current assignment is: %s" % self.assignment_formatter(assignment)
        else:
            print "No assignment selected"

    def print_student_info(self):
        "Prints information about the currently select student"
        if self.student_id:
            student = db.select_students(self.db_connection,
                                         student_id=self.student_id)[0]
            print "Current student is: %s" % self.student_formatter(student)
        else:
            print "No student selected"

    def print_db_info(self):
         "Prints information about the database connection"
         if self.db_connection:
             print "Database open at %s" % self.db_file
         else:
             print "No current database connection"

        
            
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
            s = raw_input(prompt)
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
    return os.path.abspath(os.path.expanduser(s))

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

