from distutils.core import setup

setup(name='schoolutils',
      version='0.1.0',
      description=('Utilities to track and manage student data, including '
                   'a grade database, grade calculators, and more'),
      url='',
      author='Richard Lawrence',
      author_email='richard.lawrence@berkeley.edu',
      license='GPLv2+',
      packages=['schoolutils',
                'schoolutils.grading'],
      #scripts=['bin/grade',],
      )
