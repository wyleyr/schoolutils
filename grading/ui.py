"""
ui.py

User interfaces for grading utilities.
"""
import os, sqlite3
import db, bspace

class BaseUI(object):
    pass

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

class SimpleUI(BaseUI):
    """Manages a simple (command line) user interface.
    """
    def __init__(self):
        self.db_file = None
        self.db_connection = None
        
        self.semester = None
        self.year = None
        self.course_id = None
        self.assignment_id = None

    # Top-level actions:
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
                 self.enter_grades,
                 #self.calculate_grades,
                 #self.import_grades,
                 #self.export_grades,
                 self.exit])

           
    @require('db_connection', change_database,
             "A database connection is required to change the current course.")
    def change_course(self):
        """Change current course.
           Select an existing course from the database, or add a new one.
        """
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

        course_to_str = lambda c: "{4} {3}: {2} {1}".format(*c)
        if len(courses) == 1:
            course = courses[0]
            print "Found 1 course; selecting: %s" % course_to_str(course)
            self.course_id = course[0]
        elif len(courses) == 0:
            print "No courses found matching those criteria; please try again."
            return self.change_course()
        else:
            course = self.options_menu(
                "Multiple courses found; please select one:",
                courses, course_to_str, allow_none=True)
            if course:
                print "Selected: %s" % course_to_str(course)
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
        assignment_to_str = lambda a: "{2} (due {3})".format(*a)
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
                assignments, assignment_to_str,
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
                print "Selected: {0}, {1} (sid: {2})".format(
                    last_name, first_name, sid)
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
        editor = lambda s: self.edit_dict(s, skip=['full_name'])
        creator = lambda: self.edit_dict({'last_name':'',
                                          'first_name':'',
                                          'sid':'',
                                          'email':''},
                                         validators={
                                          'last_name': db.name,
                                          'first_name': db.name,
                                          'sid': db.sid,
                                          'email': db.email,
                                         })
        header = formatter({'last_name': "Last name", 'first_name': "First name",
                            'email': "Email", 'sid': "SID"})
        students = self.edit_table(students, header, formatter, editor, creator)

        for s in students:
            try:
                student_id = db.get_student_id(self.db_connection,
                                               sid=s['sid'],
                                               first_name=s['first_name'],
                                               last_name=s['last_name'])
            except db.NoRecordsFound:
                student_id = None

            student_id = db.create_or_update_student(
                self.db_connection,
                student_id=student_id,
                last_name=s['last_name'],
                first_name=s['first_name'],
                sid=s['sid'],
                email=s['email'])
            course_member_id = db.create_course_member(
                self.db_connection,
                student_id=student_id,
                course_id=self.course_id)

        print "%d students imported successfully." % len(students)
            
    def import_grades(self):
        pass

    def export_grades(self):
        pass

    def calculate_grades(self):
        pass

    def exit(self):
        """Quit grader.
           Closes database connection and exits."""
        self.close_database()
        exit(0)
        
    # Helper methods:
    def actions_menu(self, query, options, default=None, escape=None):
        """Present a menu of actions to the user.
           query should be a string to print before the list of actions.
           actions should be a sequence callables.
           The docstring of each action is used to provide its menu entry.
           escape, if provided, should be a callable that returns the user
           to a previous menu.
        """
        # TODO: roll this into options_menu or vice versa?
        if escape:
            options = list(options) + [escape]
        
        menu_format = "{0:>3d}: {1: <30} {2: <40}" #"%d: %s\t\t%s"
        short_descs = []
        long_descs = []
        for o in options:
            lines = o.__doc__.splitlines()
            short_descs.append(lines[0])
            long_descs.append(' '.join([l.strip() for l in lines[1:]]))

        print ""
        print query
        print "Please select one of the following actions:"
        for i, o in enumerate(options):
            print menu_format.format(i, short_descs[i], long_descs[i])

        if default is not None:
            prompt = "Which action? (default %d): " % options.index(default)
        else:
            prompt = "Which action? (enter a number): "

        validator = lambda s: db.int_in_range(s, 0, len(options))
        i = typed_input(prompt, validator, default=default)
        print "" # visually separate menu and selection 
        
        return options[i]()

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

    def edit_table(self, rows, header, formatter, editor, creator=None):
        """Present a simple interface for reviewing and editing tabular data.
           rows should be a sequence of values for the user to review and edit
           header should be a string to print above the table
           formatter should be a function which, given a row value, returns a
             string representing the row for display to the screen
           editor should be a function which, given a row value, returns a
             new row value based on user input
           creator, if provided, should be a function with no arguments which
             returns a new row value based on user input  
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
                prompt = ("Enter number to edit row (or Ctrl-C to end).\n"
                          "Prefix row number with 'd' to delete")
                if creator:
                    prompt += "; enter 'i' to insert a new row: "
                else:
                    prompt += ": "
                    
                action, idx = typed_input(prompt, validator)
                if action == 'e':
                    editable_rows[idx] = editor(editable_rows[idx])
                elif action == 'd':
                    editable_rows.pop(idx)
                elif action == 'i' and creator: 
                    new_row = creator()
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
                                validator)
            if new_v:
                d[k] = new_v

        return d
            
        
    def print_course_info(self):
        "Prints information about the currently selected course"
        if self.course_id:
            course = db.select_courses(self.db_connection, course_id=self.course_id)[0]
            print "Current course is %(num)s: %(name)s (%(sem)s %(year)s)" % {
                'num': course[2],
                'name': course[1],
                'sem': course[4],
                'year': course[3]}
        else:
            print "No current course"
           
    def print_assignment_info(self):
        "Prints information about the currently selected assignment"
        if self.assignment_id:
            assignment = db.select_assignments(self.db_connection,
                                               assignment_id=self.assignment_id)[0]
            print "Current assignment is: %s" % assignment[2]
        else:
            print "No current assignment"

    def print_db_info(self):
         "Prints information about the database connection"
         if self.db_connection:
             print "Database open at %s" % self.db_file
         else:
             print "No current database connection"

    def get_student(self):
        """Lookup a student in the database, trying several methods.
           Create a new student if none exists; return student row"""
        student = None
        first_name = ''
        last_name = ''
        sid = ''
        
        try:
            sid = typed_input("Enter SID: ", db.sid, default='')
            student_id = db.get_student_id(self.db_connection, sid=sid)
        except db.GradeDBException: # either 0 or multiple records found
            last_name = typed_input("Enter last name: ", db.name, default='')
            first_name = typed_input("Enter first name: ", db.name, default='')

        try:
            # TODO? we can end up returning students who are not members of the
            # current course; offer to add them...
            student_id = db.get_student_id(self.db_connection,
                                           last_name=last_name,
                                           first_name=first_name,
                                           sid=sid)
        except db.NoRecordsFound:
            create = typed_input("No student found; create? (Y/N) ", yn_bool)
            if create:
                student_id = db.create_student(
                    first_name=first_name, last_name=last_name, sid=sid)
            else:
                print "Could not locate student with these criteria; try again."
                return self.get_student()
        except db.MultipleRecordsFound:
            students = db.select_students(self.db_connection,
                                          last_name=last_name,
                                          first_name=first_name,
                                          course_id=self.course_id,
                                          sid=sid)
            student = self.options_menu(
                "Which student did you mean?",
                students, 
                lambda s: "{1}, {2} ({3})".format(*s))
            student_id = student[0]

        if not student:
            student = db.select_students(self.db_connection, student_id=student_id)[0]
            
        return student
            
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

