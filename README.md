# Multilang
A way to write code in Python, R, Matlab, and/or bash in the same file

### Why
In computational biology, there are many tools that exist in either only Python
or only R. Even within the same project, I was having to switch from Python
(my workhorse) to R for some steps and then back to Python where I'm more
comfortable. I decided that I wanted to be able to interact with an R environment
from within Python, and that being able to write a file that could execute in
both languages was really appealing.

## Install
`pip install multilang`
Import as `import multilang`  

### Requirements
1. Termainal command `$ R` that launches the R CLI
2. Terminal command `$ matlab -nojvm -nodisplay -nosplash` that launches the Matlab CLI

### Development
Current build is 0.1.3  
Developed solely by me in pursuit of my graduate studies at MIT  
If you find any bugs, please place an Issue on [github](https://github.com/scvannost/multilang).

## Features
The 2 main use cases are:  
1. `python -m multilang path/to/file.mul`
2.
~~~python
ml = multilang.Master()
ml.r('...')
# or
multilang.as_multilang('path/to/file.mul')
# or
multilang.as_multilang(open('path/to/file.mul', 'r')) # or 'rb'
# or
multilang.as_multilang('''#! multilang
	code here...''')
~~~

The first shows how the module can be used to run Multilang .mul scripts directly. It
calls `multilang.as_multilang()` on the given file.  
The second shows the interact form of Multilang, using its `Master` class. This allows
for an interactive experience writing in 2 to 4 languages.

Either way, you get full access to the Python, R, Matlab, and shell environments; can use
any library or built-in function; and can build on top of these frameworks to do
crazy things and bodge things quickly.

### Command Line
usage: `python -m multilang [-h] [-v [{0,1,2,3}]] [-s] [-t [TIMEOUT]] file`

##### positional arguments:  
1. `file`  
   the file name to run

##### optional arguments:  
1. `-h`, `--help`  
   show this help message and exit  

2. `-v [{0,1,2,3}]`, `--verbosity [{0,1,2,3}]`  
   the level of things to print  
   0 is silent,  
   *1 is default*,  
   2 also prints switching environments,  
   3 is max  

3. `-s`, `--silent`  
   same as `--verbosity 0`

4. `-t [TIMEOUT]`, `--timeout [TIMEOUT]`  
   the number of seconds to wait for R or matlab to respond  
   default *600*


## Syntax Highlighting
By putting the `.tmPreferences` and `.sublime-syntax` in the `.config/sublime-text-3/Packages/User`
folder, Sublime will automatically highlight the syntax correctly for each language in a `.mul` file
and understand how to properly comment in Multilang.  
You may need to do `View > Syntax > Open all with current extension as... > User > Multilang`

## Example code
Examples will be placed in the `examples` folder 

## Changelog
v0.1.3:
  - added options to command line
  - added `_verbosity` to `as_multilang`
  - capture output for R and Matlab
  - `timeout` parameter added across the board

v0.1.2:
  - expanded documentation
  - better handling of errors from pexpect
  - Windows handling in `__init__` instead of `__main__`

v0.1.1:
  - name change
  - Suggested extension changed from `.ry` to `.mul` 
  - added bash support
  - calling `python -m multilang` on Windows calls `as_multilang_windows`

matrython==0.1.0:
  - name change to upload to PyPI
  - bug fixes

rython==0:
  - Python/R/Matlab support
  - Unit tests 

## MIT License
Copyright (C) 2018 SC van Nostrand

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
