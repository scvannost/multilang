# Rython
A way to write code in Python, R, and/or Matlab in the same file

### Why
In computational biology, there are many tools that exist in either only Python
or only R. Even within the same project, I was having to switch from Python
(my workhorse) to R for some steps and then back to Python where I'm more
comfortable. I decided that I wanted to be able to interact with an R environment
from within Python, and that being able to write a file that could execute in
both languages was really appealing.

### Development
Current build is 0.1.0  
Developed solely by me  
If you find any bugs, please place an Issue on the github.

## Features
The 2 main use cases are:  
1.```bash
python -m rython path/to/file.ry
```  
2. ```python
import rython
ry = rython.Master()
ry.r('...')
# or
rython.as_rython('/path/to/file.ry')
```

The first shows how the module can be used to run Rython .ry scripts directly. It
calls `rython.as_rython()` on the given file.  
The second shows the interact form of Rython, using its `Master` class. This allows
for an interactive experience writing in 2 (or 3) languages.

Either way, you get full access to the Python, R, and Matlab environments; can use
any library or built-in function; and can build on top of these frameworks to do
crazy things and bodge things quickly.

### Example code
Examples will be placed in the `examples` folder  

## MIT License
Copyright (C) 2018 SC van Nostrand

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so.  
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.  
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.