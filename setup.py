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
from distutils.core import setup

try:
    readme = open('README.rst', 'r')
    long_desc = readme.read()
except:
    long_desc = ''
finally:
    readme.close()
    
setup(name='schoolutils',
      version='0.1.3',
      description=('Utilities to track and manage student data, including '
                   'a grade database, grade calculators, and more'),
      long_description=long_desc,
      url='https://bitbucket.org/wyleyr/schoolutils',
      author='Richard Lawrence',
      author_email='richard.lawrence@berkeley.edu',
      classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: Python',
        'Topic :: Education',
        'Intended Audience :: Education',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Development Status :: 2 - Pre-Alpha',
        ],
      packages=[
        'schoolutils',
        'schoolutils.config',
        'schoolutils.grading',
        'schoolutils.institutions',
        'schoolutils.institutions.ucberkeley',
        ],
      scripts=['bin/grade',],
      data_files=[('share/schoolutils/examples', ['examples/config.py',
                                                  'examples/calculators.py'])],
      )
