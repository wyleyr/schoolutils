"""
db.py

Database interface for grading utilities
"""

import sys, sqlite3, datetime

class GradeDBException(Exception):
    def __init__(self, error_str, query=None, params=None): 
        self.query = query
        self.params = params
        self.error_str = error_str

    def __str__(self):
        return self.error_str

    def print_query(self):
        "Print this exception's query and parameter to stderr"
        sys.stderr.write(self.query)
        sys.stderr.write(str(self.params) + '\n')
    
class NoRecordsFound(GradeDBException):
    pass

class MultipleRecordsFound(GradeDBException):
    pass

def gradedb_init(db_connection):
    """Create a new SQLite database for storing grades.
       Creates a database in file named by fname with tables:
         students (id, first_name, last_name, sid)
         courses (id, name, number, year, semester)
         course_memberships (id, student_id, course_id)
         assignments (id, course_id, name, description, due_date, grade_type, points, weight)
         grades (id, assignment_id, student_id, value, timestamp)
    """
    db_connection.executescript("""
    CREATE TABLE students (
      id INTEGER PRIMARY KEY,
      first_name TEXT,
      last_name TEXT,
      sid TEXT UNIQUE
    );
    CREATE TABLE courses (
      id INTEGER PRIMARY KEY,
      name TEXT,
      number TEXT,
      year INTEGER,
      semester TEXT
    );
    CREATE TABLE course_memberships (
      id INTEGER PRIMARY KEY,
      student_id INTEGER NOT NULL,
      course_id INTEGER NOT NULL,
      FOREIGN KEY(student_id) REFERENCES students(id),
      FOREIGN KEY(course_id) REFERENCES courses(id)
    );
    CREATE TABLE assignments (
      id INTEGER PRIMARY KEY,
      course_id INTEGER NOT NULL,
      name TEXT,
      description TEXT,
      due_date TEXT,
      grade_type TEXT,
      weight NUMERIC,
      FOREIGN KEY(course_id) REFERENCES courses(id)
    );
    CREATE TABLE grades (
      id INTEGER PRIMARY KEY,
      assignment_id INTEGER NOT NULL,
      student_id INTEGER NOT NULL,
      -- rely on SQLite's dynamic types to store letter grades as text:
      value NUMERIC,
      timestamp TEXT,
      FOREIGN KEY(assignment_id) REFERENCES assignments(id),
      FOREIGN KEY(student_id) REFERENCES students(id)
    );
    """)
    return db_connection.commit()
    
def insert_sample_data(db_connection):
    "Insert some sample data into a grade database"
    db_connection.executescript("""
    INSERT INTO students VALUES (1, 'Richard', 'Lawrence', '21593500');
    INSERT INTO students VALUES (2, 'Austin', 'Andrews', '12345678');
    INSERT INTO courses VALUES (1, 'Ancient philosophy', '25A', 2012, 'Fall');
    INSERT INTO courses VALUES (2, 'Introduction to logic', '12A', 2012, 'Spring');
    INSERT INTO course_memberships VALUES (1, 1, 1);
    INSERT INTO course_memberships VALUES (2, 2, 1);
    INSERT INTO course_memberships VALUES (3, 1, 2);
    INSERT INTO assignments VALUES (1, 1, 'Paper 1', 'Socrates paper', '2012-09-17', 'letter', 0.25);
    INSERT INTO assignments VALUES (2, 1, 'Paper 2', 'Plato paper', '2012-10-30', 'letter', 0.25);
    INSERT INTO assignments VALUES (3, 1, 'Paper 3', 'Aristotle paper', '2012-11-26', 'letter', 0.25);
    INSERT INTO assignments VALUES (4, 1, 'Exam grade', 'Final exam', '2012-12-14', 'letter', 0.25);
    INSERT INTO assignments VALUES (5, 2, 'HW1', 'problem set', '2012-01-29', 'points', 105);
    INSERT INTO assignments VALUES (6, 2, 'HW2', 'problem set', '2012-02-05', 'points', 96);
    INSERT INTO grades VALUES (1, 1, 1, 'C-', '1111111111');
    INSERT INTO grades VALUES (2, 2, 1, 'B-', '1111111111');
    INSERT INTO grades VALUES (3, 3, 1, 'A', '1111111111');
    INSERT INTO grades VALUES (4, 4, 1, 'B+', '1111111111');
    INSERT INTO grades VALUES (5, 1, 2, 'A', '1111111113');
    INSERT INTO grades VALUES (6, 2, 2, 'A', '1111111113');
    INSERT INTO grades VALUES (7, 3, 2, 'A', '1111111113');
    INSERT INTO grades VALUES (8, 4, 2, 'A', '1111111113');
    INSERT INTO grades VALUES (9, 5, 1, 104, '1111111113');
    INSERT INTO grades VALUES (10, 6, 1, 90, '1111111113');
    """)
    return db_connection.commit()

def gradedb_clear(db_connection):
    "Drop all tables in a grade database"
    db_connection.executescript("""
    DROP TABLE students;
    DROP TABLE courses;
    DROP TABLE course_memberships;
    DROP TABLE assignments;
    DROP TABLE grades;
    """)
    return db_connection.commit()
    
#
# basic CRUD operations and some convenience interfaces
#
def select_courses(db_connection, year=None, semester=None, name=None, number=None):
    """Return a result set of courses.
       Rows in the result set have the format:
       (id, name, number, year, semester)
    """
    base_query = """
    SELECT id, name, number, year, semester
    FROM courses
    %(where)s
    """
    constraints, params = \
        make_conjunction_clause(['courses.year', 'courses.semester', 'courses.name', 'courses.number'],
                                [year, semester, name, number])
    query = add_where_clause(base_query, constraints)
    
    return db_connection.execute(query, params).fetchall()

def create_course(db_connection, year=None, semester=None, name=None, number=None):
    """Create a new course in the database.
       Returns the id of the inserted row.
    """
    base_query = """
    INSERT INTO courses (%(fields)s) VALUES (%(places)s);
    """
    fields, places, params = make_values_clause(['year', 'semester', 'name', 'number'],
                                                   [year, semester, name, number])
    query = base_query % {'fields': fields, 'places': places}
    db_connection.execute(query, params)

    return last_insert_rowid(db_connection)
    
def select_assignments(db_connection, course_id=None, year=None, semester=None, name=None):
    """Return a result set of assignments.
       The rows in the result set have the format:
       (assignment_id, course_id, assignment_name)
    """
    base_query = """
    SELECT assignments.id, courses.id, assignments.name
    FROM assignments, courses
    ON assignments.course_id=courses.id
    %(where)s
    """
    constraints, params = make_conjunction_clause(
        ['courses.year', 'courses.semester', 'courses.id', 'assignments.name'],
        [year, semester, course_id, name])
    query = add_where_clause(base_query, constraints)
    
    return db_connection.execute(query, params).fetchall()

def create_assignment(db_connection, course_id=None, name=None, description=None,
                      due_date=None, grade_type=None, weight=None):
    """Create a new assignment in the database.
       Returns the id of the inserted row.
    """
    base_query = """
    INSERT INTO assignments (%(fields)s) VALUES (%(places)s);
    """
    fields, places, params = make_values_clause(
        ['course_id', 'name', 'description', 'due_date', 'grade_type', 'weight'],
        [course_id, name, description, due_date, grade_type, weight])
    query = base_query % {'fields': fields, 'places': places}
    db_connection.execute(query, params)

    return last_insert_rowid(db_connection)
  
def select_students(db_connection, year=None, semester=None, course_id=None,
                    course_name=None, last_name=None, first_name=None, sid=None):
    """Return a result set of students.
       The rows in the result set have the format:
       (student_id, last_name, first_name, sid)
    """
    base_query = """
    SELECT students.id, students.last_name, students.first_name, students.sid
    FROM students, course_memberships, courses
    ON course_memberships.student_id=students.id AND
       course_memberships.course_id=courses.id
    %(where)s
    """
    fields = ['courses.year', 'courses.semester', 'courses.id', 'courses.name',
              'students.last_name', 'students.first_name', 'students.sid']
    vals = [year, semester, course_id, course_name, last_name, first_name, sid]
    constraints, params = make_conjunction_clause(fields, vals)
    query = add_where_clause(base_query, constraints)
    
    return db_connection.execute(query, params).fetchall()

def get_student_id(db_connection, first_name='', last_name='', sid=''):
    """Find a student in the grade database.
       Searches by (last_name, first_name) OR sid.
       Return the student's id if found uniquely.
    """
    base_query = """
    SELECT id
    FROM students
    %(where)s
    """
    name_constraints, name_params = make_conjunction_clause(
        ['first_name', 'last_name'],
        [first_name, last_name])
    constraints, params = make_disjunction_clause(
        ['sid'],
        [sid],
        extra=name_constraints, extra_params=name_params)

    query = add_where_clause(base_query, constraints)
    
    rows = db_connection.execute(query, params).fetchall()

    return ensure_unique(rows, err_msg="get_student_id expects to find exactly 1 student",
                         query=query, params=params)
    
def create_student(db_connection, first_name=None, last_name=None, sid=None):
    """Create a new student in the database.
       Returns the id of the inserted row.
    """
    base_query = """
    INSERT INTO students (%(fields)s) VALUES (%(places)s);
    """
    fields, places, params = make_values_clause(
        ['first_name', 'last_name', 'sid']
        [first_name, last_name, sid])
    query = base_query % {'fields': fields, 'places': places}
    db_connection.execute(query, params)

    return last_insert_rowid(db_connection)

def update_student(db_connection, student_id=None, last_name=None, first_name=None, sid=None):
    """Update a record of an existing student.
    
       If student_id is not provided, this function attempts to find a
       unique existing student using get_student_id with the given
       criteria, and then updates the database with whatever
       information has been provided, by overlaying the given criteria
       with the existing data.  (That is, it will not replace existing
       data with a NULL value.)  Returns the id of the updated row.
    """
    if not student_id:
        student_id = get_student_id(db_connection,
                                    last_name=last_name, first_name=first_name, sid=sid)

    fields = ['last_name', 'first_name', 'sid']
    old_values = db_connection.execute(
        "SELECT %s FROM students WHERE id=?" % ', '.join(fields),
        (student_id,)
    ).fetchone()
    new_values = [last_name, first_name, sid]
    update_values = overlay(old_values, new_values)
    
    base_query = """
    UPDATE students
    SET %(updates)s
    WHERE %(where)s;
    """
    update_clause, params = make_constraint_clause(", ", fields, update_values)
    query = base_query % {'updates': update_clause,
                          'where': "id=?"}
    db_connection.execute(query, params + (student_id,))
    
    return student_id

def create_or_update_student():
    raise NotImplementedError

def create_course_member(db_connection, course_id=None, student_id=None):
    """Create a new course_membership record in the database.
       Returns the id of the inserted row.
    """
    base_query = """
    INSERT INTO course_memberships (%(fields)s) VALUES (%(places)s);
    """
    fields, places, params = make_values_clause(
        ['course_id', 'student_id'],
        [course_id, student_id])
    query = base_query % {'fields': fields, 'places': places}
    db_connection.execute(query, params)

    return last_insert_rowid(db_connection)

def select_grades(db_connection, student_id=None, course_id=None, assignment_id=None):
    """Get a result set of grades for a given student or course.
       The rows in the result set have the format:
       (grade_id, student_id, course_id, assignment_id, assignment_name, grade_value)
       course_id may be supplied to limit results to one course.
    """
    base_query = """
    SELECT grades.id, students.id, assignments.course_id, assignments.id, assignments.name, grades.value
    FROM grades, assignments, students
    ON grades.assignment_id=assignments.id AND grades.student_id=students.id
    %(where)s
    """
     
    constraints, params = \
        make_conjunction_clause(['students.id', 'assignments.course_id', 'assignments.id'],
                                [student_id, course_id, assignment_id])
    query = add_where_clause(base_query, constraints)
   
    return db_connection.execute(query, params).fetchall()

def create_grade(db_connection, assignment_id=None, student_id=None, value=None,
                 timestamp=None):
    """Create a new grade in the database.
       The timestamp field is automatically generated if not provided.
       Returns the id of the inserted row.
    """
    if not timestamp:
        timestamp = datetime.datetime.now()

    base_query = """
    INSERT INTO grades (%(fields)s) VALUES (%(places)s);
    """
    fields, places, params = make_values_clause(
        ['assignment_id', 'student_id', 'value', 'timestamp'],
        [course_id, student_id, value, timestamp])
    query = base_query % {'fields': fields, 'places': places}
    db_connection.execute(query, params)

    return last_insert_rowid(db_connection)

def create_or_update_grade(db_connection, grade_id=None, assignment_id=None, student_id=None,
                           value=None, timestamp=None):
    """Create a new grade or update a record of an existing grade.
       Returns the id of the created or updated row.
       WARNING: This function uses SQLite's INSERT OR REPLACE
       statement rather than an UPDATE statement.  If you pass
       grade_id, it *will* erase data in an existing row of the grades
       table; you must provide all values to replace the existing data. 
    """
    base_query = """
    INSERT OR REPLACE INTO grades (%(fields)s) VALUES (%(places)s);
    """
    if not timestamp:
        timestamp = datetime.datetime.now()
        
    fields, places, params = make_values_clause(
        ['id', 'assignment_id', 'student_id', 'value', 'timestamp'],
        [grade_id, assignment_id, student_id, value, timestamp])    
    
    query = base_query % {'fields': fields, 'places': places}
    db_connection.execute(query, params)
    
    return last_insert_rowid(db_connection)

    
#
# for interfacing with grading functions:
# 
class GradeDict(dict):
    """Represents a set of a single student's grades in a single course.

       This class acts like a dictionary, but internally keeps track
       of database values (e.g. primary keys) so that grade values can
       be saved in the database with ease.  Assignment names are used
       as keys; these map to grade values.
    """
    def __init__(self, rows):
        """Initialize with a set of database rows.
           Each row should be formatted like:
           (student_id, course_id, assignment_id, assignment_name, grade_id, grade_value)
           as e.g. produced by select_grades_for_student. 
        """
        extra_student_ids = filter(lambda r: r[0] != rows[0][0], rows)
        if extra_student_ids:
            raise ValueError("student_id must be same in rows: %s" % rows)
        else:
            self.student_id = rows[0][0]

        # a single, unique course_id is necessary so that we can
        # correctly enter new assignments into the db  
        extra_course_ids = filter(lambda r: r[1] != rows[0][1], rows)
        if extra_course_ids:
            raise ValueError("course_id must be same in rows: %s" % rows)
        else:
            self.course_id = rows[0][1]
        
        # ensure assignment names are unique in rows
        assignment_names = [row[3] for row in rows]
        for i in range(len(assignment_names)):
            if assignment_names[i] in assignment_names[i+1:]:
                raise ValueError("Assignment names must be unique in rows: %s" %
                                 rows)
        
        # internally, the grades are maintained as a dictionary
        # mapping assignment names to a tuple of the values needed to
        # store these grades back in the database
        self._grades = dict([(r[3], r) for r in rows])

    def __getitem__(self, key):
        return self._grades[key][4]

    def __setitem__(self, key, val):
        if key in self._grades:
            self._grades[key][4] = val
        else:
            # grade_id and assignment_id not available;
            # they must be supplied at save time
            self._grades[key] = (None, None, self.student_id, key, val)

    def __iter__(self):
        return self.keys()
    
    def keys(self):
        return self._grades.keys()

    def values(self):
        return [v[4] for v in self._grades.values()]

    def items(self):
        return list(self.iteritems())

    def iteritems(self):
        return (t for t in zip(self.keys(), self.values()))
    
    def save(self, db_connection):
        "Update or insert grades into grade database"
        for grade_id, assignment_id, student_id, assignment_name, grade_val, course_id \
                in self._grades.values():
            if assignment_id is None:
                # 1) is there an assignment by this name?
                query = """
                SELECT assignments.id
                FROM assignments, courses
                ON assignments.course_id=courses.id
                WHERE assignments.name=? AND courses.id=?;
                """
                params = (assignment_name, course_id)
                ids = db_connection.execute(query, params)
                if len(ids) == 1:
                    assignment_id = ids[0][0]
                elif len(ids) == 0:
                    query = "INSERT INTO assignments (course_id, name) VALUES (?, ?)"
                    params = (course_id, assignment_name)
                    db_connection.exceute(query, params)
                    # ...
                else:
                    raise ValueError("More than one assignment with name %s for course_id %s" %
                                     assignment_name, course_id)

                
            if grade_id is not None:
                query = """
                UPDATE grades SET value=?
                WHERE id=?;
                """
                params = (grade_id, grade_val)
            else:
                pass

#            
# utilities
#
def ensure_unique(rows, err_msg='', query='', params=None):
    "Ensure a set of rows contains a single value and returns it"
    if len(rows) == 0:
        raise NoRecordsFound(err_msg, query=query, params=params)
    elif len(rows) > 1:
        raise MultipleRecordsFound(err_msg, query=query, params=params)
    else:
        return rows[0][0]

def overlay(old_values, new_values):
    """Overlay a new set of values on an old set.
       If old_values[i] != new_values[i], uses new_values[i],
       except if new_values[i] evaluates to False.
    """
    overlaid_vals = []
    for ov, nv in zip(old_values, new_values):
        if not nv or ov == nv:
            overlaid_vals.append(ov)
        else:
            overlaid_vals.append(nv)

    return overlaid_vals

def make_constraint_clause(connective, fields, values,
                           extra='', extra_params=tuple()):
    """Construct a constraint clause and a set of parameters for it.
       Returns a tuple of the constaint clause as a string and the
       parameter values as a tuple.

       If provided, extra should be a string to prepend in parentheses
       to the generated constraint clause, and extra_params should be
       a tuple of parameters to prepend to the generated parameters.
       Using these arguments, one can incrementally construct complex
       constraints, e.g. "(field1=? AND field2=?) OR field3=?"
    """
    constraints = []
    params = []
    for f, v in zip(fields, values):
        if v:
            constraints.append(f + "=?")
            params.append(v)

    if extra:
        constraints.insert(0, "(" + extra +")")
        
    clause = connective.join(constraints)
    
    return clause, tuple(extra_params) + tuple(params)

def make_conjunction_clause(fields, values,
                            extra='', extra_params=tuple()):
    "Construct a conjunctive constraint clause with make_constraint_clause"
    return make_constraint_clause(" AND ", fields, values,
                                  extra=extra, extra_params=extra_params)

def make_disjunction_clause(fields, values,
                            extra='', extra_params=tuple()):
    "Construct a disjunctive constraint clause with make_constraint_clause"
    return make_constraint_clause(" OR ", fields, values,
                                  extra=extra, extra_params=extra_params)

def add_where_clause(base_query, constraints):
    """Add a WHERE clause to a query if there are any constraints.
       base_query should be a dictionary-style format string
       containing the format specifier %(where)s and constraints
       should be a string of field constraints.
    """
    if constraints:
        where_clause = "WHERE " + constraints
        query = base_query % {'where': where_clause}
    else:
        query = base_query % {'where': ''}

    return query

def make_values_clause(fields, values):
    "Construct strings of field names and query parameter places, and a tuple of parameters"
    used_fields = []
    params = []
    places = []
    
    for i, v in enumerate(values):
        if v:
            used_fields.append(fields[i])
            params.append(values[i])
            places.append('?')
    
    return ', '.join(used_fields), ', '.join(places), tuple(params)

def last_insert_rowid(db_connection):
    "Returns the id of the last inserted row"
    return ensure_unique(db_connection.execute("SELECT last_insert_rowid()").fetchall())
