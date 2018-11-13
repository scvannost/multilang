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
<<<<<<< HEAD
`pip install multilang`  
Import as `import multilang`
=======
`pip install matrython`  
Import as rython
>>>>>>> 31bcc41a9502037efb39b217d177d5cb9a4a98af

### Development
Current build is 0.1.0  
Developed solely by me  
If you find any bugs, please place an Issue on [github](https://github.com/scvannost/multilang).

## Features
The 2 main use cases are:  
1. `python -m multilang path/to/file.mul`
2.
~~~python
#! multilang
ml = multilang.Master()
ml.r('...')
# or
multilang.as_multilang('/path/to/file.mul')
# or
multilang.as_multilang('''code here...''')
~~~

The first shows how the module can be used to run Multilang .mul scripts directly. It
calls `multilang.as_multilang()` on the given file.  
The second shows the interact form of Multilang, using its `Master` class. This allows
for an interactive experience writing in 2 to 4 languages.

Either way, you get full access to the Python, R, Matlab, and shell environments; can use
any library or built-in function; and can build on top of these frameworks to do
crazy things and bodge things quickly.

### Example code
Examples will be placed in the `examples` folder 

### Changelog
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