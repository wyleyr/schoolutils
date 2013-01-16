===========
schoolutils
===========

schoolutils provides a simple, efficient way to track and manage
student data.  It includes:

* a database for storing information about students, courses,
  assignments, and grades
* a command-line interface for interacting with the database 
* tools for calculating grades  
* tools for importing and exporting student data in useful formats

Other planned features include:

* tools for reporting grade statistics
* tools for receiving student assignments via email, and returning
  graded assignments and comments via email

Installation
============
The easiest way to install schoolutils is via `pip
<http://www.pip-installer.org/en/latest/installing.html>`_::

  $ pip install schoolutils

You can also `download
<http://pypi.python.org/pypi/schoolutils#downloads>`_ the package from
PyPI, unpack it, and run::

  $ python setup.py install

from the package directory.

Finally, you can get the development version with ``git``::

  $ git clone https://bitbucket.org/wyleyr/schoolutils.git

schoolutils has no dependencies (besides the Python standard library),
so the installation should go smoothly; if you have any problems, please
`report a bug <https://bitbucket.org/wyleyr/schoolutils/issues>`_.

Configuration
=============
It isn't necessary to configure schoolutils, but it will be faster to
use if you do.  The command-line UI expects to find configuration
files in the ``.schoolutils`` directory of your home directory.  You
should create three Python modules there: ``config.py``,
``calculators.py``, and ``validators.py``.  Sample configuration files
are included in the ``examples`` directory of the source package::

  $ mkdir ~/.schoolutils
  $ cp path/to/schoolutils_source/examples/*.py ~/.schoolutils

The comments in the sample files explain the values you should provide
there.  The most important one in ``config.py`` is ``gradedb_file``,
which should contain the path to your grade database file.  If you
don't provide this value, you will have to type it in every time you
start the grading program.

First run
=========
Once you've installed the package, you can run the grading program as
follows::

  $ grade

This will start the grading program's interactive user interface with
the configuration you specified in your ``config.py`` module.
From there, you can:

1) Add a course
2) Add or import students into the course
3) Add assignments
4) Start entering grades


After that
==========

A few concepts
--------------
The grading program has a few important concepts you should be aware
of:

Currently selected course and assignment
  The grading program has a notion of the 'current course' and
  'current assignment'.  Most of the actions you take in the grading
  program depend on your having previously selected a course or
  assignment.  For example, when you add or import students, the
  grading program will add them as members of the current course.
  When you enter grades, you will be entering grades for the current
  assignment.  You can specify the current course and assignment in
  your ``config.py`` module, or select them interactively. 

Entered vs. calculated grades
  'Entered' grades are grades you have entered into the database
  through the interactive interface.  These are the sort of grades you
  produce by hand: for example, letter grades for a batch of papers
  that you've graded.

  'Calculated' grades are grades you use the grading program to
  calculate.  Grades are calculated by a Python function that you must
  provide, in your ``calculators.py`` module (see below).  These will
  also be saved in the database, when you run the grade calculation
  command.

  You can use the grading program without ever calculating grades, but
  it will (hopefully!) save you some work if you do.
  
Grade calculation function
  A grade calculation function is a function you define in your
  ``calculators.py`` module.  This function should calculate the
  calculated grades for a single student on the basis of entered
  grades.  You should define one grade calculation function per
  course.

  Grade calculation functions use a special naming convention so the
  grading program knows which function to use when calculating
  grades.  The name should be::
  
    calculate_grade_<course number>_<semester><year>

  For example, if you are teaching a course numbered '12A' in the fall
  semester of 2013, you'd write a grade calculation function named::

    calculate_grade_12A_fall2013

  Each grade calculation function will receive a dictionary as input,
  representing a single student's (entered) grades in the current
  course.  The keys of the input dictionary are assignment names; the
  values are grade values.  The function should return a dictionary
  with the same keys and values for the entered grades, as well as a
  new key and value for each calculated grade.  For more information,
  see the example ``calculators.py`` module.

Validator function
   A validator function is a function you define in your
   ``validators.py`` module.  It prepares data that you type into the
   user interface to be saved to the database.  This function should
   accept a string and either return an appropriate value or raise a
   Python ``ValueError``.  If a validator raises a ``ValueError``, the
   user interface asks you to re-enter the value until you type one
   that validates. For example, the ``letter_grade`` validator ensures
   that any string passed to it is a letter grade, so that you can't
   save a letter grade of 'W' by mistake.

   See the sample ``validators.py`` module for more information and a
   list of the validators you can define.

Command-line options
--------------------
To see command-line options available for the grading program, use::

  $ grade --help






