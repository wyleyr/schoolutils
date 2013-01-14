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

setup(name='schoolutils',
      version='0.1.0',
      description=('Utilities to track and manage student data, including '
                   'a grade database, grade calculators, and more'),
      url='https://bitbucket.org/wyleyr/schoolutils',
      author='Richard Lawrence',
      author_email='richard.lawrence@berkeley.edu',
      license='LICENSE.txt',
      packages=['schoolutils',
                'schoolutils.config',
                'schoolutils.grading',
                'schoolutils.institutions',
                ],
      data_files=[('examples', ['examples/*.py'])],
      #scripts=['bin/grade',],
      )
