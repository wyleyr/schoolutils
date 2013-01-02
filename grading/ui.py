"""
ui.py

User interfaces for grading utilities.
"""
import os, sqlite3
import db

class BaseUI(object):
    pass

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

    # Top-level screens:
    def main_loop(self):
        "Main menu"
        if not self.db_connection:
            self.change_database()

        while True:
            self.print_db_info()
            self.print_course_info()
            self.print_assignment_info()
            self.actions_menu(
                "Main menu.",
                [self.change_database,
                 self.change_course,
                 #self.import_students,
                 self.change_assignment,
                 #self.enter_grades,
                 #self.calculate_grades,
                 #self.import_grades,
                 #self.export_grades,
                 self.exit])

    def close_database(self):
        """Close the current database connection."""
        if self.db_connection:
            print "Closing current database located at: %s" % self.db_file
            self.db_connection.commit()
            self.db_connection.close()
            self.db_connection = None
            self.db_file = None

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
            
    def enter_grades(self):
        pass

    def change_course(self):
        """Change current course.
           Select an existing course from the database, or add a new one."""
        self.print_course_info()
        self.actions_menu("What do you want to do?",
                        [self.select_course,
                         self.create_course])
                        
    def select_course(self):
        """Select an existing course.
           Lookup an existing course in the database by semester, name, or number."""
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

        self.print_course_info()
        
    def create_course(self):
        """Create a new course.
           Add a new course to the database and select it as the current
           course."""
        year = typed_input("Enter year: ", db.year)
        semester = typed_input("Enter semester: ", db.semester)
        course_num = typed_input("Enter course number: ", str)
        course_name = typed_input("Enter course name: ", str)

        course_id = db.create_course(
            self.db_connection,
            year=year, semester=semester,
            name=course_name, number=course_num)

        self.course_id = course_id
        self.print_course_info()

    def change_assignment(self):
        """Change current assignment.
           Select an existing assignment from the databse, or add a new one"""
        self.print_assignment_info()
        self.actions_menu("What do you want to do?",
            [self.select_assignment, self.create_assignment])

    def select_assignment(self):
        """Select an assignment.
           Lookup an existing assignment in the database.
        """
        if not self.course_id:
            print "You must select a course before selecting an assignment"
            self.change_course()
            
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
                
        self.print_assignment_info() 
    
    def create_assignment(self):
        """Create a new assignment.
           Add a new assignment to the database and select it as the current assignment.
        """
        if not self.course_id:
            print "You must select a course before creating an assignment"
            self.change_course()

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

        self.print_assignment_info()
            
    def import_students(self):
        pass

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
