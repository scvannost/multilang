"""Run Python, R, Matlab, and bash in the same file.

Expected uses
-------------
1.	Natively in Python:
		>>> import multilang

	This allows for both script and interactive use
		>>>	# run a script
		>>>	fname = 'path/to/file.mul'
		>>>	ml = multilang.as_multilang(fname)
		>>>	ml = multilang.as_multilang('''#! multilang
		...	<code>
		...		''')

		>>>	# use interactively
		>>>	ml = multilang.Master()
		>>>	ml.r('# code here')

2.	Running scripts from Terminal:
		$ python -m multilang path/to/file.mul


Warning
-------
	The underlying connection relies on `pexpect`, which does not
	support a Windows environment.
	Some future release will be Windows-compatible.

Scripts
-------
Scripts contain source code in Python, R, Matlab, and/or bash.
These files are marked by the first line of code:
	#! multilang [<lang>]
Switching between environments is done using:
	#! <lang> -> [<vars>]
See the docs for as_multilang to learn more.

Interactive
-----------
Using the `mutlilang.Master()` class, you can interact with multiple
environments without having to write a script.
The Python environment here is only a dictionary to load/store variables.
All Python code is expected to be run directly by the user.
See the docs for Master to learn more.

How It Works
------------
Passing variables between most environments uses temporary .mat files.
Python's file interactions use scipy.io.
R's file interactions use R.matlab.
Matlab's file interactions use the `load` and `save` commands.
Bash's interactions are done using a dict, starting with `os.environ`.

Bash commands are run using:
	subprocess.run(<code>, shell=True, executable='/bin/bash')
Matlab is running as a script, so function definitions are not allowed.

Subpackages
-----------
All imported directly into the main module for convenience.
objects
	Underlying classes for R and Matlab environments

Attributes
----------
DEFAULT_DUMP : func
	The function called by `multilang.dump`
	Default: `multlilang.dump_dict`

DEFAULT_DUMPS : func
	The function called by `multilang.dumps`
	Default: `multlilang.dumps_json`

_VERSION : str
	The current version of multilang

_SUPPORTED : list[str]
	The currently supported languages

_VARIABLES : dict[str, object]
	The storage of variables in the Python environment

_IMPORTED : dict[name: object]
	Things imported by multilang which are available without
	import in Scripts.

Major Functions
---------------
as_multilang
	Either as_multilang_unix or as_multilang_windows as detected
	by platform.system
as_multilang_unix
	Run multilang code on a Unix-based system; eg. Ubuntu, Mac
as_multilang_windows
	Not implemented
	Run multilang code on Windows

Classes
-------
Master
	An interactive object for multilang coding
RObject
	An interactive R environment
MatlabObject
	An interactive Matlab environment

Builtin Functions for Scripting
-------------------------------
as_array
	For passing Python variables as arrays
mod
	Replaces Python's modulo operator %

Minor Functions
---------------
py_to_bash
py_to_r
py_to_mat
	Move variables from the Python variable dict to the given environment

r_to_bash
r_to_py
r_to_mat
	Move variables from R to the given environment

mat_to_bash
mat_to_py
mat_to_r
	Move variables from Matlab to the given environment

bash_to_py
bash_to_mat
bash_to_r
	Move variables from the bash env dict to the given environment
"""



# ------------------------------- Imports ------------------------------- #
import json
import numpy as np
import os
import pandas as pd
from platform import system
from random import choices
import re
import scipy.io as sio
import sys
import subprocess
from tempfile import NamedTemporaryFile

from .objects import RObject, MatlabObject



# ------------------------------ Constants ------------------------------ #
global _VARIABLES
_VARIABLES = {}

_IMPORTED = {
		'json'	: json,
		'np'	: np,
		'os'	: os,
		'pd'	: pd,
		'system': system,
		'choices': choices,
		're'	: re,
		'sio'	: sio,
		'subprocess': subprocess,
		'NamedTemporaryFile': NamedTemporaryFile,
		'RObject': RObject,
		'MatlabObject': MatlabObject
	}

_SUPPORTED = ['python3', 'matlab', 'r', 'bash']
_VERSION = '0.1.3a1'

# Defaults at bottom



# --------------------------- Helper Functions --------------------------- #
def py_to_bash(_line, _environ : dict = None):
	"""Move variables from Python to bash.

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! b[ash] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of Python variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a Python variable

		All variables must be str, int, float.

	_environ : optional[dict]
		The dict to which the variables are added
		Default: os.environ

	Returns
	-------
	dict[str: object]
		The requested variables and their corresponding values
		Meant to be used as @env in `subprocess.run`

	Raises
	------
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the Python environment
	TypeError
		If a requested variable is not str, int, float
	"""
	## input validation
	if not _environ: _environ = os.environ.copy() # default
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted _line: ' + _line)
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line: ' + str(_line))

	if _to_load[0] == '':
		# null case
		return _environ

	## get the variables
	_out = {}
	for _i in _to_load:
		if _i not in _VARIABLES:
			raise NameError(_i+' not in Python environment')
		elif type(_VARIABLES[_i]) not in [str, int, float]:
			raise TypeError('Only str, int, float can be passed to bash')
		else:
			_out[_i] = _VARIABLES[_i]

	# move the variables
	_environ.update(_out)
	return _environ

def bash_to_py(_line, _environ : dict, _load : bool = True):
	"""Move variables from bash to Python

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! p[y[thon]] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of bash variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a bash variable

		All variables must be str, int, float.

	_environ : dict
		The dictionary where the variables are stored
		Generally, comes from `multilang.bash`

	_load : optional[bool]
		If True, loads in `multilang._VARIABLES`

	Returns
	-------
	dict[str, object]
		The requested variables and their corresponding values

	Raises
	------
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the given @_environ
	"""
	## input validation
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	# null case
	if _to_load[0] == '':
		return {}

	# get the variables
	_out = {}
	for _i in _to_load:
		if _i not in _environ:
			raise NameError(str(_i) + ' not in bash environment.')
		else:
			_out[_i] = _environ[_i]

	if _load:
		# move the variables to python
		_VARIABLES.updat(_out)
	return _out

def bash_to_r(_line, _environ : dict, _r_object : RObject = RObject()):
	"""Move variables from bash to R

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! r[lang] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of bash variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a bash variable

		All variables must be str, int, float.

	_environ : dict
		The dictionary where the variables are stored
		Generally, comes from `multilang.bash`

	_r_object : optional[RObject]
		The R environment to load the variables into
		Default: new RObject()
		

	Returns
	-------
	RObject
		An R environment with the given variables loaded

	Raises
	------
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the given @_environ
	"""
	## input validation
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>,...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')
	
	if not _r_object.isalive:
		# make it if we need it
		_r_object = RObject()
	if _to_load[0] == '':
		# null case
		return _r_object

	# get the variables
	_out = {}
	for _i in _to_load:
		if _i not in _environ:
			raise NameError(str(_i) + ' not in bash environment.')
		else:
			_out[_i] = _environ[_i]
	
	# send to R
	_r_object.sendlines([
			_k + ' <- ' + ('"' + _v + '"' if type(_v) is str else str(_v))
				for _k, _v in _out.items()
		]
	)
	return _r_object

def bash_to_mat(_line, _environ : dict, _mat_object : MatlabObject = MatlabObject()):
	"""Move variables from bash to Matlab

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! m[at[lab]] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of bash variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a bash variable

		All variables must be str, int, float.

	_environ : dict
		The dictionary where the variables are stored
		Generally, comes from `multilang.bash`

	_mat_object : optional[MatlabObject]
		The Matlab environment to load the variables into
		Default: new MatlabObject()
		

	Returns
	-------
	MatlabObject
		A Matlab environment with the given variables loaded

	Raises
	------
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the given @_environ
	"""
	## input validation
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	if not _mat_object.isalive:
		# make it if we need it
		_mat_object = MatlabObject()
	if _to_load[0] == '':
		# null case
		return _mat_object

	# get the variables
	_out = {}
	for _i in _to_load:
		if _i not in _environ:
			raise NameError(str(_i) + ' not in bash environment.')
		else:
			_out[_i] = _environ[_i]
	
	# bundle them
	_temp_file = NamedTemporaryFile(suffix='.mat')
	sio.savemat(_temp_file, _out)
	_temp_file.seek(0)

	# load them
	_mat_object.sendline('load \'' + _temp_file.name + '\';')

	return _mat_object

def r_to_bash(_line, _r_object : MatlabObject, _environ : dict = None):
	"""Move variables from R to bash.

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! b[ash] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of R variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of an R variable

		All variables must be str, int, float.

	_r_object : RObject
		The R environment to pull the variables from

	_environ : optional[dict]
		The dictionary to which the variables are added
		Default: os.environ

	Returns
	-------
	dict[str, object]
		The requested variables and their corresponding values
		Meant to be used as @env in `multilang.bash`

	Raises
	------
	RuntimeError
		If _r_object is not alive.
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the R environment
	TypeError
		If a requested variable is not str, int, float
	"""
	## input validation
	if not _r_object.isalive:
		# can't do anythin
		raise RuntimeError('R connection was killed before things could be brought back to Python.')
	if not _environ: _environ = os.environ.copy() # default

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	# null case
	if _to_load[0] == '':
		return _environ

	# get the variables
	_dump = r_to_py(_line, _r_object, _load=False)
	_out = {}
	for _i in _to_load:
		if _i not in _dump:
			raise NameError(str(_i) + ' not in R environment.')
		elif type(_dump[_i]) not in [str, int, float]:
			raise TypeError('Only str, int, float can be passed to bash')
		else:
			_out[_i] = _dump[_i]

	# load them
	_environ.update(_out)
	return _environ

def mat_to_bash(_line, _mat_object : MatlabObject, _environ : dict = None):
	"""Move variables from Matlab to bash.

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! b[ash] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of Matlab variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of an Matlab variable

		All variables must be str, int, float.

	_mat_object : MatlabObject
		The Matlab environment to pull the variables from

	_environ : optional[dict]
		The dictionary to which the variables are added
		Default: os.environ

	Returns
	-------
	dict[str, object]
		The requested variables and their corresponding values
		Meant to be used as @env in `multilang.bash`

	Raises
	------
	RuntimeError
		If _mat_object is not alive.
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the Matlab environment
	TypeError
		If a requested variable is not str, int, float
	"""
	## input validation
	if not _mat_object.isalive:
		# can't do anything
		raise RuntimeError('Matlab connection was killed before things could be brought back to Python.')
	if not _environ: _environ = os.environ.copy() # default

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	# null case
	if _to_load[0] == '':
		return

	# get the variables
	_dump = mat_to_py(_line, _mat_object, _load=False)
	_out = {}
	for _i in _to_load:
		if _i not in _dump:
			raise NameError(str(i) + ' not in Matlab environment')
		elif type(_dump[_i]) not in [str, int, float]:
			raise TypeError('Only str, int, float can be passed to bash')
		else:
			_out[_i] = _dump[_i]

	# load them
	_environ.update(_out)
	return _environ



def py_to_r(_line, _r_object : RObject = RObject()):
	"""Move variables from Python to R

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! r[lang] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of Python variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a Python variable

		All variables must be str, int, float.

	_r_object : optional[RObject]
		The R environment to load the variables into
		Default: new RObject()
		

	Returns
	-------
	RObject
		An R environment with the given variables loaded

	Raises
	------
	ValueError
		If _line is not the right format
	RuntimeError
		If _r_object is not alive
	NameError
		If a requested variable is not in the Python environment
	"""
	## input validation
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')
	
	if not _r_object.isalive:
		# can't do anything
		raise RuntimeError('Matlab connection was killed before things could be send to it.')
	if _to_load[0] == '':
		# null case
		return _r_object

	# check the variables
	_temp = []
	_counter = 0
	while _counter < len(_to_load):
		_item = _to_load[_counter]

		# ignore if func(*args[str]), just look at func
		if '(' in _item and _item[-1] != ')':
			while _item[-1] != ')':
				_counter += 1
				_item += ',' + _to_load[_counter]

		# look for them
		if _item not in _VARIABLES: # hard case
			# look for it
			try:
				# make sure it's a valid function call
				if len(_item.split('(')) > 1: eval(_item.split('(')[0])
				else: raise Exception()
			except: raise NameError(_item.split('(')[0] + ' not in Python environment.')
			else: # if it's there
				# _item is func(a[, b])
				# look for the parameters
				for _i in _item[:-1].split('(')[1].split(','):
					if _i not in _VARIABLES:
						# if it exists, that's fine
						try: eval(_i)
						except: raise NameError(_i + ' not in Python environment.')
				_temp.append(_item)
		else: _temp.append(_item) # easy case

		_counter += 1
	_to_load = _temp

	# get them
	_out = {}
	for _i in _to_load:
		if '(' in _i and ')' in _i:
			# _i = 'func(a[, b])'
			_items = _i.split('(')[1].split(')')[0].split(',')

			_func = eval(_i.split('(')[0]) # get the func
			_out.update(_func(*_items)) # evaluate it

		else: _out[_i] = _VARIABLES[_i]

	# bundle the variables
	_temp_file = NamedTemporaryFile()
	sio.savemat(_temp_file, _out)
	_temp_file.seek(0)
	
	# send them
	_random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
	_r_object.sendlines(
		[
			'library("R.matlab")',
			_random_name + ' <- readMat("' + _temp_file.name + '")'
		] + [
			_current + ' <- ' + _random_name + '$' + _current
				for _current in _out
		] + [
			'rm(' + _random_name + ')'
		]
	)

	return _r_object

def py_to_mat(_line, _mat_object : MatlabObject = MatlabObject()):
	"""Move variables from Python to Matlab

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! m[at[lab]] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of Python variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a Python variable

		All variables must be str, int, float.

	_mat_object : optional[MatlabObject]
		The Matlab environment to load the variables into
		Default: new MatlabObject()
		

	Returns
	-------
	MatlabObject
		A Matlab environment with the given variables loaded

	Raises
	------
	ValueError
		If _line is not the right format
	RuntimeError
		If _mat_object is not alive
	NameError
		If a requested variable is not in the Python environment
	"""
	## input validation
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	if not _mat_object.isalive:
		# can't do anything
		raise RuntimeError('Matlab connection was killed before things could be send to it.')
	if _to_load[0] == '':
		# null case
		return _mat_object

	# check the variables
	_temp = []
	_counter = 0
	while _counter < len(_to_load):
		_item = _to_load[_counter]

		# ignore if func(*args[str]), just look at func
		if '(' in _item and _item[-1] != ')':
			while _item[-1] != ')':
				_counter += 1
				_item += ',' + _to_load[_counter]

		if _item not in _VARIABLES: # hard case
			try: # make sure it's a valid function call
				if len(_item.split('(')) > 1: eval(_item.split('(')[0])
				else: raise Exception()
			except: raise NameError(_item.split('(')[0] + ' not in Python environment.')
			else: # if it exists
				# check the parameters
				# _item = func(a[, b])
				for _i in _item[:-1].split('(')[1].split(','):
					if _i not in _VARIABLES: # if it's there, that's cool
						try: eval(_i)
						except: raise NameError(_i + ' not in Python environment.')
				_temp.append(_item)
		else: # easy case
			_temp.append(_item)
		_counter += 1
	_to_load = _temp

	# get the variables
	_out = {}
	for _i in _to_load:
		if '(' in _i and ')' in _i: # function call
			_items = _i.split('(')[1].split(')')[0].split(',')

			_func = eval(_i.split('(')[0]) # get the func
			_out.update(_func(*_items)) # evaluate it

		else: _out[_i] = _VARIABLES[_i] # easy case

	# bundle them
	_temp_file = NamedTemporaryFile(suffix='.mat')
	sio.savemat(_temp_file, _out)
	_temp_file.seek(0)

	# load them
	_mat_object.sendline('load \'' + _temp_file.name + '\';')
	return _mat_object

def r_to_py(_line, _r_object : RObject, _load : bool = True):
	"""Move variables from R to Python

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! p[y[thon]] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of R variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a R variable

		All variables must be str, int, float.

	_r_object : RObject
		The R environment where the variables are stored

	_load : optional[bool]
		If True, loads in `multilang._VARIABLES`

	Returns
	-------
	dict[str, object]
		The requested variables and their corresponding values

	Raises
	------
	RuntimeError:
		If _r_object is not alive
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the given R environment
	"""
	## input validation
	if not _r_object.isalive:
		# can't do anything
		raise RuntimeError('R connection was killed before things could be brought back to Python.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	# null case
	if _to_load[0] == '':
		return

	# check the variables
	_who = _r_object.who
	for i in _to_load:
		if i not in _who:
			raise NameError(str(i) + ' not in R environment.')

	# bundle them
	_random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
	_r_object.sendline(_random_name + '<- tempfile(); ' + _random_name)
	_temp_file = str(_r_object.before).split('"')[1]

	# get them
	_r_object.sendlines([
			'writeMat(paste(' + _random_name + ',".mat",sep=""), ' + ', '.join([i + '=' + i for i in _to_load]) + ')',
			'rm(' + _random_name + ')'
		])

	# load them
	_loaded = sio.loadmat(_temp_file, squeeze_me=True)
	del _loaded['__globals__'], _loaded['__header__'], _loaded['__version__']
	if _load:
		_VARIABLES.update(_loaded)
	return _loaded

def r_to_mat(_line, _r_object : RObject, _mat_object : MatlabObject = MatlabObject()):
	"""Move variables from R to Matlab

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! m[at[lab]] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of R variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a R variable

		All variables must be str, int, float.

	_r_object : Robject
		The R environment where the variables are stored

	_mat_object : optional[MatlabObject]
		The Matlab environment to load the variables into
		Default: new MatlabObject()
		

	Returns
	-------
	MatlabObject
		A Matlab environment with the given variables loaded

	Raises
	------
	RuntimeError:
		If _r_object or _mat_object is not alive
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the given R environment
	"""
	## input validation
	if not _r_object.isalive:
		# can't do anything
		raise RuntimeError('R connection was killed before things could be brought to Matlab.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	if not _mat_object.isalive:
		# can't do anything
		raise RuntimeError('Matlab connection was killed before things could be send to it.')
	if _to_load[0] == '':
		# null case
		return _mat_object

	# check the variables
	_who = _r_object.who
	for i in _to_load:
		if i not in _who:
			print(_who)
			raise NameError(str(i) + ' not in R environment.')

	# bundle them
	_random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
	_r_object.sendline(_random_name + '<- tempfile(); ' + _random_name)
	_temp_file = str(_r_object.before).split('"')[1]

	# get them
	_r_object.sendlines([
			'writeMat(paste(' + _random_name + ',".mat", sep=""), ' + ', '.join([ i + '=' + i for i in _to_load]) + ')',
			'rm(' + _random_name + ')'
		])

	# load them
	_mat_object.sendline('load \'' + _temp_file + '\';')
	return _mat_object

def mat_to_py(_line, _mat_object : MatlabObject, _load : bool = True):
	"""Move variables from Matlab to Python

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! p[y[thon]] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of Matlab variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a Matlab variable

		All variables must be str, int, float.

	_mat_object : MatlabObject
		The Matlab environment where the variables are stored

	_load : optional[bool]
		If True, loads in `multilang._VARIABLES`

	Returns
	-------
	dict[str, object]
		The requested variables and their corresponding values

	Raises
	------
	RuntimeError:
		If _mat_object is not alive
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the given Matlab environment
	"""
	## input validation
	if not _mat_object.isalive:
		# can't do anything
		raise RuntimeError('Matlab connection was killed before things could be brought back to Python.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__'):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	# null case
	if _to_load[0] == '':
		return

	# check the variables
	_who = _mat_object.who
	if any([i not in _who for i in _to_load]):
		raise NameError(str(i) + ' not in Matlab environment')

	# bundle them
	_random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
	_mat_object.sendline(_random_name + ' = tempname')
	_temp_file = _mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]

	# get them
	_mat_object.sendlines([
			'save ' + _temp_file + ' ' + ' '.join(_to_load),
			'clear ' + _random_name
		])

	# load them
	_loaded = sio.loadmat(_temp_file, squeeze_me=True)
	del _loaded['__globals__'], _loaded['__header__'], _loaded['__version__']
	if _load:
		_VARIABLES.update(_loaded)
	return _loaded

def mat_to_r(_line, _mat_object : MatlabObject, _r_object : RObject = RObject()):
	"""Move variables from Matlab to R

	Parameters
	----------
	_line : str, Iterable[str]
		If str, one of the following:
			1. '#! m[at[lab]] -> <vars>'
			2. '<vars>'
		where <vars> is a comma separated list of Matlab variable names

		If Iterable[str]: [<var1>, <var2>, ...]
		where <varX> is the name of a Matlab variable

		All variables must be str, int, float.

	_mat_object : Matlabobject
		The Matlab environment where the variables are stored

	_r_object : optional[RObject]
		The R environment to load the variables into
		Default: new RObject()
		

	Returns
	-------
	MatlabObject
		A Matlab environment with the given variables loaded

	Raises
	------
	RuntimeError:
		If _mat_object or _r_object is not alive
	ValueError
		If _line is not the right format
	NameError
		If a requested variable is not in the given Matlab environment
	"""
	## input validation
	if not _mat_object.isalive:
		# can't do anything
		raise RuntimeError('Matlab connection was killed before things could be brought back to Python.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		# _line = '#! <lang> -> <vars>'
		if not '->' in _line:
			raise ValueError('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		# _line = '<vars>'
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		# _line = [<var i>, ...]
		_to_load = list(_line)
	else:
		raise ValueError('Unrecognized _line')

	if not _r_object.isalive:
		# can't do anything
		raise RuntimeError('R connection was killed before things could be send to it.')
	if _to_load[0] == '':
		# null case
		return _r_object

	# check the variables
	_who = _mat_object.who
	for i in _to_load:
		if i not in _who:
			raise NameError(str(i) + ' not in Matlab environment')

	# bundle them
	_random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
	_mat_object.sendline(_random_name + ' = tempname')
	_temp_file = _mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]

	# get them
	_mat_object.sendlines([
			'save ' + _temp_file + '.mat ' + ' '.join(_to_load),
			'clear ' + _random_name
		])
	
	# load them
	_r_object.sendlines(
		[
			'library("R.matlab")',
			_random_name + ' <- readMat("' + _temp_file + '.mat")'
		] + [
			_current + ' <- ' + _random_name + '$' + _current
				for _current in _to_load
		] + [
			'rm(' + _random_name + ')'
		]
	)
	return _r_object


def dump(_file = '', **kwargs):
	"""Return the local Python variables
	Change `multilang.DEFAULT_DUMP` to change this action
	"""
	return DEFAULT_DUMP(_file=_file, **kwargs)

def dumps(**kwargs):
	"""Returns a str version of the local Python variables.
	Change `multilang.DEFAULT_DUMPS` to change this action
	"""
	return DEFAULT_DUMPS(_file='', **kwargs)


def dump_dict(**kwargs):
	"""Return the local Python variables

	Use `globals().update(dump())` to bring variables into the global scope,
		or `locals().update(dump())` for the local scope.

	Parameters
	----------
	**kwargs : Ignored

	Returns
	-------
	dict[str: object]
		One entry for each local Python variable
	"""
	return {k:v for k,v in _VARIABLES.items() if not k[0] is '_'}

def dump_mat(_file, **kwargs):
	"""Dumps the local Python variables to a .mat file

	Parameters
	----------
	_file : str, filelike
		The file name to dump into
		If filelike, has a `write` method
	**kwargs : Passed to `scipy.io.savemat`.
	"""
	if hasattr(_file, 'write'): # if filelike
		sio.savemat(_file, *[k for k,v in _VARIABLES.items() if not k[0] is '_'], **kwargs)
	else: # file name
		sio.savemat(open(_file, 'w'), *[k for k,v in _VARIABLES.items() if not k[0] is '_'], **kwargs)

def dump_json(_file, **kwargs):
	"""Dumps the local Python variables to a .json file

	Parameters
	----------
	_file : str, filelike
		The file name to dump into
		If filelike, has a `write` method
	**kwargs : Passed to `json.dump`.
	"""
	if hasattr(_file,'write'): # if filelike
		json.dump({k:v for k,v in _VARIABLES.items() if not k[0] is '_'}, _file, **kwargs)
	else: # file name
		json.dump({k:v for k,v in _VARIABLES.items() if not k[0] is '_'}, open(_file, 'w'), **kwargs)

def dumps_json(**kwargs):
	"""Returns a JSON-formatted str of local Python variables.

	Parameters
	----------
	**kwargs : Passed to `json.dump`.
	"""
	json.dumps({k:v for k,v in _VARIABLES.items() if not k[0] is '_'}, **kwargs)

def mod(a,b):
	"""Replaces Python's modulo operator due to its use in comments"""
	return a%b

def as_array(var: str, extras: str = 'True'):
	"""Built-in function to pass a variable as an np.array

	Parameters
	----------
	var : str
		Name of the Python variable
	extras : str
		If 'True', also pass additional information if avaialbe
		Default: 'True'

	Returns
	-------
	dict : [str: object]
		The resulting {@var: value} to be loaded into the next environment

	Extras
	-----
	If extras == 'True', adds more information about the variable.
	If var is a pd.DataFrame:
		<var>_index and <var>_columns are also passed as lists.
	"""
	# get it
	obj = _VARIABLES[var]

	if extras != 'True':
		# if nothing special
		return {var: np.array(obj)}
	elif type(obj) is pd.core.frame.DataFrame:
		# handle DataFrames
		return {var: np.array(obj),
				var+'_index': obj.index.values.tolist(),
				var+'_columns': obj.columns.values.tolist()}
	else: # everything else is simple
		return {var: np.array(obj)}

# ---------------------------- Main Functions ---------------------------- #
def as_multilang_windows(*args, **kwargs):
	"""A simple interface for multilang coding on Windows.
	Not yet implemented, but will recapitulate `as_multilang_Unix`.
	"""
	raise NotImplementedError('To be used in a Windows environment')


def as_multilang_unix(_lines, _load_r : bool = False, _r_object : RObject = None,
			_mat_object : MatlabObject = None, _environ : dict = None,
			_timeout : int = 600, _verbosity : int = 1, **kwargs):
	"""Run a multilang script (implementation for Unix)

	Parameters
	----------
	_lines : filelike, str, bytes, Iterable[str], Iterable[bytes]
		The script to be run
		If filelike: must have a `readlines` or `read` method
		If str, bytes: lines separated by line breaks; eg. \\r\\n, \\r, \\n
		if Iterable: each entry is a line; no line breaks

	_load_r : bool
		Whether to load the existing R environment
		Only checked if a new R environment is created
		Default: False

	_r_object : Optional[RObject]
		An R environment to use
		Default: new RObject

	_mat_object : Optional[MatlabObject]
		A Matlab environment to use
		Default: new MatlabObject

	_environ : dict[str: str,int,float]
		Variables to be used in bash
		Default: os.environ

	_timeout : int
		Number of seconds until time out
		Only used if a new R or Matlab environment is being created
		Default: 600

	_verbosity : int
		How much to print while this function runs
		0 <= _verbosity <= 3
		If 0: silent
		If 1: output from each environment
		If 2: plus when switching between environments
		If 3: plus additional information

	**kwargs : dict[str:object]
		Add as variables to the Python environment by calling `load`

	Returns
	--------
	Master
		A Master object with the resulting environments loaded

	Raises
	------
	ValueError
		If any multilang statement is improperly formatted
	NameError
		If any variable being passed doesn't exist
	TypeError
		If any variable passed to bash is not str,int,float

	Scripts
	=======
	"Shebangs" (i.e. #! or %!) are used as the statements to both identify
	multilang code and to switch between the different environments.
	_lines should read as so:
		[1] #! multilang [R, Python, Matlab, bash]
		[2] # code here`
		[3] #! R/Python/Matlab/bash -> [<vars>]
		[4] # code here
		[.] # ...
		[n] #! Python -> [<vars>]

	All multilang scripts start with `#! multilang` then an optional language.
	If no initial language is given, Python is assumed.
	Scripts should end with a Python switch line to retrieve any variables back
		into the Python environment.
	The suggested extension for a multilang file is .mul.

	To switch languages, `#! <lang> -> [<vars>]` is used to switched to <lang>.
	<vars> is an optional comma-separated list of variables to bring.
	Language names are NOT case-sensitive and depend only on the existence
	of 'r', 'p', 'm', or 'b'.

	`print` only works in the Python and bash environments.
	Outputs in R and Matlab are not currently captured.

	Comments
	--------
	Line comments can be marked with either '#' or '%'
	Block comments are surrounded by '%{'/'#{' and '%}'/'#}' on their own lines.

	In Python, the modulo operator uses a bare %, which is overridden by
		the multilang comment feature.
	Use multilang's builtin `mod(a,b)` instead of a%b.
	Use ''.format() instead of '' % ().
	
	Python's `%=`is not affected.
	R's `%...%` operators are not affected either.

	Builtins
	--------
	All of multilang is available as builtins in the Python environment.
	These can be extended by a Python function with the @multilang wrapper.

	This is particularly useful when passing objects between environments.
	As multilang's function are only available in Python, these functions are
	only available when switching out of Python.

	All inputs should be str, with the first being the name of the variable.
	Local variables can be accessed by _VARIABLES[name], see example.
	It should return a dict of {name: value} of things to pass through
		`sio.savemat` into the next environment.

	The definition of `mutlilang.as_array` follows as an example:
		[1]	#! multilang
		[2]	@multilang
		[3]	def as_array(var: str, extras: str = 'True'):
		[4]		obj = _VARIABLES[var]
		[5]		if extras != 'True':
		[6]			return {var: np.array(obj)}
		[7]		elif type(obj) is pd.core.frame.DataFrame:
		[8]			return {var: np.array(obj),
		[9]				var+'_index': obj.index.values.tolist(),
		[10]			var+'_columns': obj.columns.values.tolist()}
		[11]	else:
		[12]		return {var: np.array(obj)}
	"""

	# load the code
	if hasattr(_lines, 'readlines'): # preferred utility
		_file = _lines
		_lines = __file.readlines()
	elif hasattr(_lines, 'read'): # acceptable file usage
		_file = _lines
		_lines = _file.readlines()
	elif type(_lines) is str and _lines[:2] not in ['#!','%!']: # file name
		_fname = _lines
		with open(_fname, 'r') as _file:
			_lines = _file.readlines()
	
	# make sure is Iterable[str] without line breaks
	if type(_lines) in [bytes, str]: # handle not lists
		_lines = str(_lines).replace('\r\n','\n').replace('\r','\n').split('\n')
	elif type(_lines[0]) is bytes: # if List[bytes]
		_lines = [str(i) for i in _lines]
	if type(_lines[0] is str): # if List[str]
		_lines = [i.strip('\n') for i in _lines]

	# format validation
	while _lines[0][:2] not in ['#!','%!'] or 'multilang' not in _lines[0].lower():
		# find the multilang call
		_lines = _lines[1:]		
	for _n, _i in enumerate(_lines[1:]):
		if len(_i) > 2 and _i[:2] in ['#!', '%!']:
			# check statements
			_l = _i[2:].strip().replace(' ','').split('->')
			if not any([i in _l[0].lower() for i in 'rpmb']) or len(_l) != 2:
				raise ValueError('Improperly formatted call in line ' + str(_n+2))

	# get the starting environment
	_temp = _lines[0].split(' ')[-1].lower()
	if 'multilang' in _temp or 'p' in _temp:
		_lang = 'p'
	elif 'r' in _temp:
			_lang = 'r'
	elif 'm' in _temp:
		_lang = 'm'
	elif 'b' in _temp and not 'matlab' in _temp:
		# avoid b from matlab
		_lang = 'b'
	else:
		raise ValueError('Unknown language was specified')

	# deal with loading kwargs
	if kwargs: _VARIABLES.update(kwargs)

	# defaults
	if not _environ: _environ = os.environ.copy()
	if not _r_object: _r_object = RObject(load=_load_r, timeout=_timeout)
	if not _mat_object: _mat_object = MatlabObject(timeout=_timeout)

	# check in range
	if _verbosity < 0: _verbosity = 0
	elif _verbosity > 3: _verbosity = 3

	# loop through code
	# each endpoint increments counter and continues
	if _verbosity >= 2: print('Starting in ' + ('Python' if _lang == 'p' else 'R' if _lang == 'r' else 'Matlab' if _lang == 'm' else 'bash'))
	_counter = 1 # skip multilang declaration
	while _counter < len(_lines):
		_current_line = _lines[_counter].strip()
		if _current_line in ['%{','#{']:
			# block comment
			_i = _counter+1
			while _i < len(_lines) and _lines[_i].strip() not in ['%}','#}']:
				_i += 1
			_counter = _i+1
			continue
		elif not _current_line or (_current_line[0] in '#%' and _current_line[1] != '!'):
			# line comment
			_counter += 1
			continue

		# if currently in python
		elif _lang == 'p':
			if _current_line[:2] in ['#!','%!']: # if switching
				if 'r' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to R')
					_lang = 'r'
					_r_object = py_to_r(_current_line, _r_object)
				elif 'm' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to Matlab')
					_lang = 'm'
					_mat_object = py_to_mat(_current_line, _mat_object)
				elif 'b' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to bash')
					_lang = 'b'
					_environ = py_to_bash(_current_line, _environ)
				_counter += 1
				continue
			elif '@multilang' in _current_line and re.search(r'^def\s*[a-zA-Z_]+\s*\(.*?\)\s*:$', _lines[_counter+1].strip()):
				# declaring function in the local space

				# get the next line
				_end = _counter + 1
				_l = _lines[_end].strip(' ')
				
				# look for comments
				_i = 0
				_ignore = False
				while _i < len(_l):
					if _l[_i] in '\'"':
						_ignore = not _ignore
					elif not _ignore and (_l[_i] == '#' or (_l[_i] == '%' and _l[_i+1] != '=')):
						break
					_i += 1
				_l = _l[:_i]

				# get the function name
				_name = _l.split('def ')[1].split('(')[0].strip()

				# find the indent so we know when to stop
				_search = re.search(r'\t+(?:.)', _l)
				_tabs = _search.end() if _search and _search.end() > 0 else 0

				# get the code
				_to_exec = [_l[_tabs:]]
				while _l and _l[:2] not in ['#!', '%!'] and _end < len(_lines)-1:
					# get the line
					_end += 1
					_l = _lines[_end]

					# get indentation
					_search = re.search(r'[\t(?: {4})]+(?:.)', _l)
					_curr_tabs = _search.end() if _search and _search.end() > 0 else 0

					if _curr_tabs <= _tabs: # done!
						break
					elif _l and _l[0] not in '%#':
						# ignore comments
						_i = 0
						_ignore = False
						while _i < len(_l):
							if _l[_i] in '\'"':
								_ignore = not _ignore
							elif not _ignore and (_l[_i] == '#' or (_l[_i] == '%' and _l[_i+1] != '=')):
								break
							_i += 1

						# push it!
						_to_exec.append(_l[:_i])

				# define it and add it
				if _verbosity == 0:
					_old = sys.stdout
					sys.stdout = None
					try:
						exec('\n'.join(_to_exec))
					except Exception as e:
						sys.stdout = _old
						raise e
					else:
						sys.stdout = _old
					del _old
				else:
					exec('\n'.join(_to_exec))

				globals().update({_name: locals()[_name]})
				_counter = _end
				continue

			elif '@multilang' in _current_line:
				# skip if the next line isn't a `def`
				_counter += 1
				continue

			else: # otherwise, do the thing
				# make sure we're up to date
				globals().update(_VARIABLES)
				_end = _counter
				_l = _lines[_end].strip(' ')

				# remove comments
				_i = 0
				_ignore = False
				while _i < len(_l):
					if _l[_i] in '\'"':
						# ignore comment markers in strings
						_ignore = not _ignore
					elif not _ignore and (_l[_i] == '#' or (_l[_i] == '%' and _l[_i+1] != '=')):
						# if we're not in a string and it's a comment but not %=
						break # stop before here
					_i += 1
				_l = _l[:_i]

				# get the code to run
				# have to build it up for exec
				_to_exec = [_l] if _l and _l[0] not in '%#' else []
				while _l and _l[:2] not in ['#!','%!'] and '@multilang' not in _l and _end < len(_lines)-1:
					# stop at statements or local function declaration
					_end += 1
					_l = _lines[_end]
					if _l and _l[0] not in '%#':
						# ignore comments
						_i = 0
						_ignore = False
						while _i < len(_l):
							if _l[_i] in '\'"':
								# ignore if in string
								_ignore = not _ignore
							elif not _ignore and (_l[_i] == '#' or (_l[_i] == '%' and _l[_i+1] != '=')):
								break # stop before here
							_i += 1

						_to_exec.append(_l[:_i])

				# define it and add it
				if _verbosity == 0:
					_old = sys.stdout
					sys.stdout = None
					try:
						exec('\n'.join(_to_exec))
					except Exception as e:
						sys.stdout = _old
						raise e
					else:
						sys.stdout = _old
					del _old
				else:
					exec('\n'.join(_to_exec))

				_VARIABLES.update({k:v for k,v in locals().items() if not k[0] is '_'})
				_counter = _end+1 if _end == len(_lines)-1 else _end
				continue

		# if currently in bash
		elif _lang == 'b':
			if _current_line[:2] in ['#!', '%!']: # switching environments
				if 'p' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to Python')
					_lang = 'p'
					mat_to_py(_current_line, _mat_object)
				elif 'r' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to R')
					_lang = 'r'
					_r_object = mat_to_r(_current_line, _mat_object, _r_object)
				elif 'm' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to Matlab')
					_lang = 'm'
					_mat_object = py_to_mat(_current_line, _mat_object)
				_counter += 1
				continue
			else: # otherwise do the thing
				# get the line
				_end = _counter
				_l = _lines[_end].strip(' ')

				# remove comments
				_i = 0
				_ignore = False
				while _i < len(_l):
					if _l[_i] in '\'"':
						# ignore comment markers in strings
						_ignore = not _ignore
					elif not _ignore and _l[_i] in '#%':
						# if we're not in a string and it's a comment
						break # stop before here
					_i += 1
				_l = _l[:_i]


				# get the code to run
				# have to bundle for subprocess.run
				_to_exec = [_l] if _l and _l[0] not in '%#' else []
				while _l and _l[:2] not in ['#!','%!'] and _end < len(_lines)-1:
					_end += 1
					_l = _lines[_end]
					if _l and  _l[0] not in '%#':
						# ignore comments
						_i = 0
						_ignore = False
						while _i < len(_l):
							if _l[_i] in '\'"':
								_ignore = not _ignore
							elif not _ignore and (_l[_i] in '#%'):
								break
							_i += 1

						_to_exec.append(_l[:_i])

				# run in terminal
				# raises error if return code not 0
				if _verbosity == 0: subprocess.run('\n'.join(_to_exec), shell=True, env={k:str(v) for k,v in _environ.items()}, executable='/bin/bash', stdout=open('/dev/null', 'w')).check_returncode()
				else: subprocess.run('\n'.join(_to_exec), shell=True, env={k:str(v) for k,v in _environ.items()}, executable='/bin/bash').check_returncode()

				# update and move on
				_environ = os.environ.copy()
				_counter = _end+1 if _end == len(_lines)-1 else _end
				continue

		# if currently in R
		elif _lang == 'r':
			if _current_line[:2] in ['#!','%!']: # switching environments
				if 'p' in _current_line.lower().split('->')[0]: # if switching to Python
					if _verbosity >= 2: print('Switching to Python')
					_lang = 'p'
					r_to_py(_current_line, _r_object)
				elif 'm' in _current_line.lower().split('->')[0]: # if switching to Matlab
					if _verbosity >= 2: print('Switching to Matlab')
					_lang = 'm'
					_mat_object = r_to_mat(_current_line, _r_object, _mat_object)
				elif 'b' in _current_line.lower().split('->')[0]: # if switching to bash
					if _verbosity >= 2: print('Switching to bash')
					_lang = 'b'
					_environ = r_to_bash(_line, _environ)
				_counter += 1
				continue
			else: # otherwise do the thing
				# go through the code
				_end = _counter
				while _end < len(_lines) and _lines[_end].strip()[:2] not in ['#!', '%!']:
					_l = _lines[_end].strip()
					if _l and _l[0] not in '#%':
						# remove comments
						_i = 0
						_ignore = False
						while _i < len(_l):
							if _l[_i] in '\'"':
								_ignore = not _ignore
							elif not _ignore and (
									_l[_i] == '#' or (
										_l[_i] == '%' and 
										# have to ignore all the %...% operators
										not any([('%' + j + '%') in _l[_i:_i+10] for j in
											['in','between', 'chin', '+', '+replace',':','do','dopar',
											 '>','<>','T>','/', '*','o','x','*']
										])
									)
								):
								break
							_i += 1

						# do the thing
						_r_object.sendline(_l[:_i])
						if _verbosity > 0 and len(_r_object.before.split(_l[:_i])) > 1:
							_temp = _r_object.before.split(_l[:_i])[1].strip()
							if _temp: print(_temp)
					_end += 1

				# move on
				_counter = _end
				continue

		# if currently in Matlab
		elif _lang == 'm':
			if _current_line[:2] == '#!': # switching environments
				if 'p' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to Python')
					_lang = 'p'
					mat_to_py(_current_line, _mat_object)
				elif 'r' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to R')
					_lang = 'r'
					_r_object = mat_to_r(_current_line, _mat_object, _r_object)
				elif 'b' in _current_line.lower().split('->')[0]:
					if _verbosity >= 2: print('Switching to bash')
					_lang = 'b'
					_environ = mat_to_bash(_line, _environ)
				_counter += 1
				continue
			else: # otherwise do the thing
				# go through the code
				_end = _counter
				_done = ''
				while _end < len(_lines) and _lines[_end].strip()[:2] not in ['#!', '%!']:
					_l = _lines[_end].strip()
					if _l and  _l[0] not in '%#':
						# skip comments
						_i = 0
						_ignore = False
						while _i < len(_l):
							if _l[_i] in '\'"':
								_ignore = not _ignore
							elif not _ignore and (_l[_i] in '#%'):
								break
							_i += 1

						# do the thing
						# if command doesn't finish, matlab doesn't send anything in return
						_mat_object.send(_l[:_i] + '\n')
						_mat_object.expect('\r\n')

						if _l[-3:] == '...':
							# if end with line continuation, nothing
							continue

						# look for balancing things to see if done
						for i in _l:
							if i in '([{':
								_done += i
							elif i in ')]}':
								try:
									if i == ')' and _done[-1] == '(':
										_done = _done[:-1]
									elif i == ']' and _done[-1] == '[':
										_done = _done[:-1]
									elif i == '}' and _done[-1] == '}':
										_done = _done[-1]
								except Exception:
									pass

						if len(_done) == 0:
							# if everything matches up, start over
							_mat_object.expect('>>')
							if _verbosity >= 1 and _mat_object.before != '':
								# print if we're printing
								print(_mat_object.before)

					_end += 1

				# move on
				_counter = _end
				continue

		else: # shouldn't get here ever
			raise ValueError('Invalid definition of _lang, contact scvannost@gmail.com.')

	# return
	ret = Master(r_object = _r_object, mat_object = _mat_object, environ = _environ)
	ret.load_from_dict(_VARIABLES)
	return ret



# -------------------------------- Main Classes -------------------------------- #
class Master:
	"""An interactive Multilang environment

	Allows for interfacing with R, Matlab, and bash environments.
	Relies on RObject and MatlabObject classes, and `subprocess.run`.

	Unlike in scripts, do not pass misformatted comments.
		R/bash - # only
		Matlab - % or '%{...%}' only

	The Python environment here is only a dictionary to load/store variables.
	All Python code is expected to be run directly by the user.

	Properties
	----------
	who
		Returns {'X': who_X} for all X
	who_X
		Returns a list of the names of all variables in the X environment
	r_object
		The underlying R environment
	isalive_r
		If the underlying R environment is alive
	mat_object, m_object, matlab_object
		The underlying Matlab environment
	isalive_mat, isalive_m, isalive_matlab
		If the underlying Matlab environment is alive
	bash_object
		The dict of variables underlying the bash environment

	Functions
	---------
	connect
		Connect to the underlying environments
	reconnect
		Reconnect to the underlying environments
	dump_all
		Return all variables from all environments

	load, load_to_py, to_py
		Add variable to the Python variable dictionary
	load_from_dict
		Add variables to the Python variable dictionary
	drop
		Drop variable(s) from the Python variable dictionary
	dump_py
		Return the Python variable dictionary

	For X in [r, bash, mat/m/matlab]:
	connect_X
		Connect to the underlying R environment
	X
		Run X code
	X_to_mat, X_to_m, X_to_matlab
		Move variable(s) from X to Matlab
	X_to_r
		Move variable(s) from X to R
	dump_X
		Get all variables from X
		Or move all variables from X to the Python variable dictionary
	X_to_py
		Move variable(s) from X to the Python variable dictionary
		Or get variable(s) from X
	X_to_bash
		Move variable(s) from R to bash
	py_to_X
		Move variable(s) from the Python variable dictionary to X
	dump_to_X
		Move all variables from the Python variable dictionary to X
	"""
	def __init__(self, r : bool = True, mat : bool = True, load_r : bool = False,
			r_object : RObject = None, mat_object : MatlabObject = None, environ : dict = None,
			timeout : int = 600, m : bool = True, matlab : bool = True):
		"""Setup a Master object

		Parameters
		----------
		r : bool
			Whether to connect to an R environment on startup
		r_object : RObject
			An existing R environment to use
			Default: new MatlabObject()
		load_r : bool
			Whether to load the existing workspace in R
			Default: False
			Default: new RObject()
			Default: True
		mat : bool
			Or @m or @matlab
			Whether to connect to a Matlab environment on startup
			Default: True
		mat_object: MatlabObject
			An existing Matlab environment to use
		environ : dict[str: str,int,float]
			A dictionary to use for the bash environment
			Default: os.environ
		timeout : int
			Number of seconds until time out
			Only used if new R or Matlab environments are being generated
			Default: 600

		Returns
		-------
		Master
			Initialized object
		"""
		if system() == 'Windows':
			raise NotImplementedError('Not implemented for Windows')

		## Setup environments
		# R
		if not r_object: self._r_object = RObject(r, load_r, timeout)
		else: self._r_object = r_object

		# Matlab
		mat = mat and m and matlab
		if not mat_object: self._mat_object = MatlabObject(mat, timeout)
		else: self._mat_object = mat_object

		# bash
		if not environ: self. _environ = os.environ.copy()
		else: self._environ = environ
		self._orig_env = os.environ.copy()

		# Python
		self._variables = {}

	@property
	def who(self):
		"""Returns {'mat': `who_m`, 'r': `who_r`, 'py':`who_py`}"""
		return {'mat': self.who_m, 'r': self.who_r, 'py': self.who_py, 'bash': self.who_bash}

	def connect(self, r : bool = True, mat : bool = True, load_r : bool = False):
		"""Connect to the underlying environments.
		Does nothing if target environment already connected

		Parameters
		----------
		r : bool
			Whether to connect to the R environment
			Default: True
		load_r : bool
			Whether to load the existing workspace in R
		mat : bool
			Whether to connect to the Matlab environment
			Default: True
		"""
		if r: self.connect_r(load_r)
		if mat: self.connect_mat()

	def reconnect(self, r : bool = True, mat : bool = True, force : bool = True, load_r : bool = False):
		"""Reconnect to the underlying enviroments

		Parameters
		----------
		r : bool
			Whether to connect to the R environment
			Default: True
		load_r : bool
			Whether to load the existing workspace in R
		mat : bool
			Whether to connect to the Matlab environment
			Default: True
		force : bool
			Whether to force reconnection
			Default: True
		"""
		if r: self.r_object.reconnect(force, load_r)
		if mat: self.mat_object.reconnect(force)


	def to_py(self, name : str, value):
		"""See `load`"""
		self.load(name, value)
	def load_to_py(self, name : str, value):
		"""See `load`"""
		self.load(name, value)
	def load(self, name : str, value):
		"""Loads the given Python variable as {name: value}"""
		self._variables[name] = value

	def drop(self, name):
		"""Drop the given variable(s) from the Python environment"""
		if  hasattr(name, '__iter__') and not type(name) is str:
			[self.drop(i) for i in name]
		del self._variables[name]

	def load_from_dict(self, d : dict):
		"""Add the given Python variables as {name: value}
		Use `load_from_dict(globals())` to load all variables
		"""
		self._variables.update(d)

	@property
	def who_py(self):
		"""Returns a list of Python variables."""
		return list(self._variables.keys())

	def dump_py(self):
		"""Returns the Python variables as a dict of {name:value}"""
		return self._variables.copy()


	def dump_all(self, precedence : str = 'all', load : bool = False):
		"""Get/Load all variables from R and Matlab

		Parameters
		----------
		precedence : None, str in ['all', 'r', 'mat']
			If str: sets which environment gets precedence
				If 'all': set conflicting variable names as R_name and mat_name
			If None: error on conflict
			Default: 'all'

		load : bool
			Whether to load the result into the Python variable dict
			Default: False

		Returns
		-------
		dict
			{name:value} for all variables in R and Matlab

		Raises
		------
		RuntimeError
			If either the R or Matlab environment is not alive
		NameError
			If @precendence is None and there is a conflicting name
		ValueError
			If @precendence not in [None, 'r', 'mat', 'all']
		"""
		# can't do anything
		if not self.isalive_r: raise RuntimeError('r_object not alive')
		elif not self.isalive_mat: raise RuntimeError('mat_object not alive')

		# get all the variables from R
		names = self.who_r
		random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.r_object.sendline(random_name + '<- tempfile(); ' + random_name)
		temp_file = str(self.r_object.before).split('"')[1]
		self.r_object.sendlines([
				'writeMat(paste(' + random_name + ',".mat", sep=""), ' + ', '.join([i + '=' + i for i in names]) + ')',
				'rm(' + random_name + ')'
			])
		r = sio.loadmat(temp_file, squeeze_me=True)
		del r['__globals__'], r['__header__'], r['__version__']

		# get all the variables from Matlab
		names = self.who_mat
		random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.mat_object.sendline(random_name + ' = tempname')
		temp_file = self.mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]
		self.mat_object.sendlines([
				'save ' + temp_file + ' ' + ' '.join(names),
				'clear ' + random_name
			])
		mat = sio.loadmat(temp_file, squeeze_me=True)
		del mat['__globals__'], mat['__header__'], mat['__version__']

		if not precedence: # no repeats allowed
			for i in r:
				if i in mat:
					raise NameError('Repeated variable name: ' + i)
			# if it makes it here, no repeats
			mat.update(r)
			ret = mat
		
		elif 'r' in precedence: # R > Matlab
			mat.update(r)
			ret = mat
		elif 'm' in precedence: # Matlab > R
			r.update(mat)
			ret = r

		elif precedence == 'all': # both
			# find the ones we have to fix
			fix = []
			for i in r:
				if i in mat:
					fix.append(i)

			# fix them
			for i in fix:
				r['r_'+i] = r[i]
				del r[i]
				mat['mat_'+i] = mat[i]
				del mat[i]

			# no more overlaps
			mat.update(r)
			ret = mat
		else: # validation
			raise ValueError('@precedence must be \'r\', \'mat\', \'all\', or None')

		# load to Python and return
		if load: self._variables.update(ret)
		return ret

	def connect_r(self, load_r : bool = False):
		"""Connect to an R environment
		Does nothing if already connected

		Parameters
		----------
		load_r : bool
			Whether to load the existing R workspace
			Default: False
		"""
		self._r_object.connect(load_r)

	@property
	def r_object(self):
		"""Returns the underlying RObject"""
		return self._r_object
	@property
	def isalive_r(self):
		"""Returns if the R environment is alive"""
		return self._r_object.isalive
	@property
	def who_r(self):
		"""Returns a list of the variable names in R"""
		if not self.isalive_r: return []
		return self.r_object.who

	def r(self, code):
		"""Run R code"""
		if not self.isalive_r: raise RuntimeError('r_object not alive')
		code = code.replace('\r\n','\n').replace('\r','\n').split('\n')

		end = 0
		while end < len(code) and code[end].strip()[:2] not in ['#!', '%!']:
			l = code[end].strip()
			if l and l[0] not in '#%':
				# remove comments
				i = 0
				ignore = False
				while i < len(l):
					if l[i] in '\'"':
						ignore = not ignore
					elif not ignore and (
							l[i] == '#' or (
								l[i] == '%' and 
								# have to ignore all the %...% operators
								any([('%' + j + '%') in _l[i:i+10] for j in
									['in','between', 'chin', '+', '+replace',':','do','dopar',
									 '>','<>','T>','/', '*','o','x','*']
								])
							)
						):
						break
					i += 1

				# do the thing
				self.r_object.sendline(l[:i])
				temp = self.r_object.before.split(l[:i])[1].strip()
				if temp: print(temp)
			_end += 1

	def r_to_m(self, names):
		"""See `r_to_mat`"""
		self.r_to_mat(names)
	def r_to_matlab(self, names):
		"""See `r_to_mat`"""
		self.r_to_mat(names)
	def r_to_mat(self, names):
		"""Move variables from R to Matlab

		Parameters
		----------
		names: str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names

		Raises
		------
		RuntimeError
			If either the R or Matlab environments are not alive
		ValueError
			If unrecognized @names
		NameError
			If a variable not in the R environment
		"""
		## input validation
		if not self.isalive_r: raise RuntimeError('r_object not alive')
		elif not self.isalive_mat: raise RuntimeError('mat_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check the variables
		who = self.who_r
		for i in names:
			if i not in who:
				raise NameError(str(i) + ' not in R environment')

		# bundle them
		random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.r_object.sendline(random_name + '<- tempfile(); ' + random_name)
		temp_file = str(self.r_object.before).split('"')[1]

		# get them
		self.r_object.sendlines([
				'writeMat(paste(' + random_name + ',".mat", sep=""), ' + ', '.join([i + '=' + i for i in names]) + ')',
				'rm(' + random_name + ')'
			])

		# load them
		self.mat_object.sendline('load \'' + temp_file + '\';')

	def r_to_py(self, names, load : bool = True):
		"""Move variables from R to Python
		Use `globals().update(r_to_py(@names))` to add directly to local session

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names
		load : bool
			Whether to add to Python variable dict
			Default: True

		Returns
		-------
		dict[str: object]
			The requested variables

		Raises
		------
		RuntimeError
			If the R environment is not alive
		ValueError
			If unrecognized names
		NameError
			If a variable not in the R environment
		"""
		## input validation
		if not self.isalive_r: raise RuntimeError('r_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check the variables
		who = self.who_r
		for i in names:
			if i not in who:
				raise NameError(str(i) + ' not in R environment')

		# bundle them
		random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.r_object.sendline(random_name + '<- tempfile(); ' + random_name)
		temp_file = str(self.r_object.before).split('"')[1]

		# get them
		self.r_object.sendlines([
				'writeMat(' + random_name + ', ' + ', '.join([i + '=' + i for i in names]) + ')',
				'rm(' + random_name + ')'
			])

		# load them and return
		ret = sio.loadmat(temp_file, appendmat=False, squeeze_me=True)
		del ret['__globals__'], ret['__header__'], ret['__version__']
		if load: self._variables.update(ret)
		return ret

	def r_to_bash(self, names):
		"""Move variables from R to bash
		Variables must be str,int,float

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names

		Raises
		------
		RuntimeError
			If the R environment is not alive
		ValueError
			If unrecognized names
		NameError
			If a variable not in the R environment
		TypeError
			If a variable is not str,int,float
		"""
		## input validation
		if not self.isalive_r: raise RuntimeError('r_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check and get the variables
		dump = self.dump_r(load=False)
		ret = {}
		for i in names:
			if i not in dump:
				raise NameError(str(i) + ' not in R environment.')
			elif type(dump[i]) not in [str, int, float]:
				raise TypeError('Only str, int, float can be passed to bash')
			else:
				ret[i] = _dump[i]

		# load
		self._environ.update(ret)

	def py_to_r(self, names, **kwargs):
		"""Move variables from Python to R
		Make sure you have loaded the variables first with `load` or `load_from_dict`
		Use @as_array = True to pass pd.DataFrame as np.ndarray

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names
		**kwargs

		Raises
		------
		RuntimeError
			If the R environment is not alive
		ValueError
			If unrecognized names
		NameError
			If a variable not in the Python environment
		"""
		## input validation
		if not self.isalive_r: raise RuntimeError('r_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized name')

		# check the variables
		for i in names:
			if i not in self._variables:
				raise NameError(i + ' not in Python environment.')

		# get them
		to_load = {i: self._variables[i] for i in names}
		if 'as_array' in kwargs and kwargs['as_array']:
			# do as_array and replace
			temp = list(to_load.keys())
			if 'extras' in kwargs:
				extras = kwargs['extras']
				temp = [as_array(i, extras) for i in temp]
			else:
				temp = [as_array(i) for i in temp]
			to_load = {k:v for d in temp for k,v in d.items()}

		# bundle them
		temp_file = NamedTemporaryFile(suffix='.mat')
		sio.savemat(temp_file, to_load)
		temp_file.seek(0)

		# load them
		random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.r_object.sendlines(
			[
				'library("R.matlab")',
				random_name + ' <- readMat("' + temp_file.name + '")'
			] + [
				i.replace('_','.') + ' <- ' + random_name + '$' + i.replace('_','.')
					for i in to_load.keys()
			] + [
				'rm(' + random_name + ')'
			]
		)

	def dump_r(self, load : bool = False):
		"""Returns all the variables from the R environment

		Parameters
		----------
		load : bool
			Whether to also add the variables to the Python variable dict
			Default: False

		Returns
		-------
		dict[str, object]
			The variables loaded from the R environment
		"""
		return self.r_to_py(self.who_r, load)

	def dump_to_r(self):
		"""Move all variables from Python variable dict to the R environment"""
		self.py_to_r(self.who_py)



	def connect_m(self):
		"""See `connect_mat`"""
		self._mat_object.connect()
	def connect_matlab(self):
		"""See `connect_mat`"""
		self._mat_object.connect()
	def connect_mat(self):
		"""Connect to an Matlab environment
		Does nothing if already connected
		"""
		self._mat_object.connect()

	@property
	def m_object(self):
		"""See `mat_object`"""
		return self._mat_object
	@property
	def matlab_object(self):
		"""See `mat_object`"""
		return self._mat_object
	@property
	def mat_object(self):
		"""Returns the underlying MatlabObject"""
		return self._mat_object

	@property
	def isalive_m(self):
		"""See `isalive_mat`"""
		return self._mat_object.isalive
	@property
	def isalive_matlab(self):
		"""See `isalive_mat`"""
		return self._mat_object.isalive
	@property
	def isalive_mat(self):
		"""Returns if the Matlab environment is alive"""
		return self._mat_object.isalive

	@property
	def who_m(self):
		"""See `who_mat`"""
		return self.who_mat
	@property
	def who_matlab(self):
		"""See `who_mat`"""
		return self.who_mat
	@property
	def who_mat(self):
		"""Returns a list of the variable names in Matlab"""
		if not self.isalive_mat: return []
		return self.mat_object.who

	def m(self, code):
		"""See `mat`"""
		self.mat(code)
	def matlab(self, code):
		"""See `mat`"""
		self.mat(code)
	def mat(self, code):
		"""Run matlab code. Does not append a semicolon"""
		if not self.isalive_mat: raise Exception('mat_object not alive')
		code = code.replace('\r\n','\n').replace('\r','\n').split('\n')

		# go through the code
		end = 0
		done = ''
		while end < len(code) and code[end].strip()[:2] not in ['#!', '%!']:
			l = code[end].strip()
			if l and  l[0] not in '%#':
				# skip comments
				i = 0
				ignore = False
				while i < len(l):
					if l[i] in '\'"':
						ignore = not ignore
					elif not ignore and (l[i] in '#%'):
						break
					i += 1

				# do the thing
				# if command doesn't finish, matlab doesn't send anything in return
				self.mat_object.send(l[:i] + '\n')
				self.mat_object.expect('\r\n')

				if l[-3:] == '...':
					# if end with line continuation, nothing
					continue

				# look for balancing things to see if done
				for i in l:
					if i in '([{':
						done += i
					elif i in ')]}':
						try:
							if i == ')' and done[-1] == '(':
								done = _done[:-1]
							elif i == ']' and done[-1] == '[':
								done = _done[:-1]
							elif i == '}' and done[-1] == '}':
								done = done[-1]
						except Exception:
							pass

				if len(done) == 0:
					# if everything matches up, start over and print
					self.mat_object.expect('>>')
					print(self.mat_object.before)

			end += 1

	def m_to_r(self, names):
		"""See mat_to_r"""
		self.mat_to_r(names)
	def matlab_to_r(self, names):
		"""See mat_to_r"""
		self.mat_to_r(names)
	def mat_to_r(self, names):
		"""Move variables from Matlab to R

		Parameters
		----------
		names: str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names

		Raises
		------
		RuntimeError
			If either the R or Matlab environments are not alive
		ValueError
			If unrecognized @names
		NameError
			If a variable not in the Matlab environment
		"""
		## input validation
		if not self.isalive_mat: raise RuntimeError('mat_object is not alive')
		elif not self.isalive_r: raise RuntimeError('r_object is not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check the variables
		who = self.who_mat
		for i in names:
			if i not in who:
				raise NameError(str(i) + ' not in Matlab environment')

		# bundle them
		random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.mat_object.sendline(random_name + ' = tempname')
		temp_file = self.mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]
		self.mat_object.sendlines([
				'save ' + temp_file + ' ' + ' '.join(names),
				'clear ' + random_name
			])

		# load them
		self.random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.r_object.sendlines(
			[
				'library("R.matlab")',
				random_name + ' <- readMat("' + temp_file + '.mat")'
			] + [
				n + ' <- ' + random_name + '$' + n
					for n in names
			] + [
				'rm(' + random_name + ')'
			]
		)

	def m_to_py(self, names):
		"""See `mat_to_py`"""
		return self.mat_to_py(names)
	def matlab_to_py(self, names):
		"""See `mat_to_py`"""
		return self.mat_to_py(names)
	def mat_to_py(self, names, load=True):
		"""Move variables from Matlab to Python
		Use `globals().update(mat_to_py(@names))` to add directly to local session

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names
		load : bool
			Whether to add to Python variable dict
			Default: True

		Returns
		-------
		dict[str: object]
			The requested variables

		Raises
		------
		RuntimeError
			If the Matlab environment is not alive
		ValueError
			If unrecognized names
		NameError
			If a variable not in the Matlab environment
		"""
		## input validation
		if not self.isalive_mat: raise RuntimeError('mat_object is not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check the variables
		who = self.who_mat
		for i in names:
			if i not in who:
				raise NameError(str(i) + ' not in Matlab environment')

		# bundle them
		random_name = ''.join(choices('abcdefghijklmnopqrstuvwxyz', k=10))
		self.mat_object.sendline(random_name + ' = tempname')
		temp_file = self.mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]

		# get them
		self.mat_object.sendlines([
				'save ' + temp_file + ' ' + ' '.join(names),
				'clear ' + random_name
			])
		
		# load them and return
		ret = sio.loadmat(temp_file, squeeze_me=True)
		del ret['__globals__'], ret['__header__'], ret['__version__']
		if load: self._variables.update(ret)
		return ret

	def m_to_bash(self, names):
		"""See `mat_to_bash`"""
		self.mat_to_bash(names)
	def matlab_to_bash(self, names):
		"""See `mat_to_bash`"""
		self.mat_to_bash(names)
	def mat_to_bash(self, names):
		"""Move variables from Matlab to bash
		Variables must be str,int,float

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names

		Raises
		------
		RuntimeError
			If the Matlab environment is not alive
		ValueError
			If unrecognized names
		NameError
			If a variable not in the Matlab environment
		TypeError
			If a variable is not str,int,float
		"""
		## input validation
		if not self.isalive_mat: raise RuntimeError('mat_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check and get the variables
		dump = self.dump_mat(load=False)
		ret = {}
		for i in names:
			if i not in dump:
				raise NameError(str(i) + ' not in Matlab environment.')
			elif type(dump[i]) not in [str, int, float]:
				raise TypeError('Only str, int, float can be passed to bash')
			else:
				ret[i] = _dump[i]

		# load them
		self._environ.update(ret)

	def py_to_m(self, names):
		"""See `py_to_mat`"""
		self.py_to_mat(names)
	def py_to_matlab(self, names):
		"""See `py_to_mat`"""
		self.py_to_mat(names)
	def py_to_mat(self, names, **kwargs):
		"""Move variables from Python to Matlab
		Make sure you have loaded the variables first with `load` or `load_from_dict`
		Use @as_array = True to pass pd.DataFrame as np.ndarray

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names
		**kwargs

		Raises
		------
		RuntimeError
			If the Matlab environment is not alive
		ValueError
			If unrecognized names
		NameError
			If a variable not in the Python environment
		"""
		## input validation
		if not self.isalive_mat: raise RuntimeError('mat_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check the variables
		for i in names:
			if i not in self._variables:
				raise NameError(i + ' not in Python environment.')

		# get them
		to_load = {i: self._variables[i] for i in names}
		if 'as_array' in kwargs and kwargs['as_array']:
			# do as_array and replace
			temp = list(to_load.keys())
			if 'extras' in kwargs:
				extras = kwargs['extras']
				temp = [as_array(i, extras) for i in temp]
			else:
				temp = [as_array(i) for i in temp]
			to_load = {k:v for d in temp for k,v in d.items()}

		# bundle them
		temp_file = NamedTemporaryFile(suffix='.mat')
		sio.savemat(temp_file, {i: self._variables[i] for i in names})
		temp_file.seek(0)

		# load them
		self.mat_object.sendline('load \'' + temp_file.name + '\';')

	def dump_m(self, load : bool = False):
		"""See `dump_mat`"""
		return self.dump_mat(load)
	def dump_matlab(self, load : bool = False):
		"""See `dump_mat`"""
		return self.dump_mat(load)
	def dump_mat(self, load : bool = False):
		"""Returns all the variables from the Matlab environment

		Parameters
		----------
		load : bool
			Whether to also add the variables to the Python variable dict
			Default: False

		Returns
		-------
		dict[str, object]
			The variables loaded from the Matlab environment
		"""
		return self.mat_to_py(self.who_mat, load)

	def dump_to_m(self):
		"""See `dump_to_mat`"""
		self.dump_to_mat()
	def dump_to_matlab(self):
		"""See `dump_to_mat`"""
		self.dump_to_mat()
	def dump_to_mat(self):
		"""Move all variables from Python variable dict to the Matlab environment"""
		self.py_to_mat(self.who_py)



	@property
	def who_bash(self):
		"""Returns a list of the variable names in bash"""
		return [k for k in self._environ.keys() if k not in self._orig_env]

	@property
	def bash_object(self):
		"""Underlying dict that represents the bash environment"""
		return self._environ
	

	def dump_bash(self, load : bool = False):
		"""Returns all the variables from the bash environment

		Parameters
		----------
		load : bool
			Whether to also add the variables to the Python variable dict
			Default: False

		Returns
		-------
		dict[str, object]
			The variables loaded from the Matlab environment
		"""
		return self.bash_to_py(self.who_bash, load)

	def bash(self, code):
		"""Run bash code"""
		code = code.replace('\r\n','\n').replace('\r','\n').split('\n')
		subprocess.run('\n'.join(code), shell=True, env={k:str(v) for k,v in self._environ.items()}, executable='/bin/bash').check_returncode()
		self._environ = os.environ.copy()

	def py_to_bash(self, names):
		"""Move variables from Python to bash
		Make sure you have loaded the variables first with `load` or `load_from_dict`

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names
		**kwargs

		Raises
		------
		ValueError
			If unrecognized names
		NameError
			If a variable not in the Python environment
		TypeError
			If a variable is not str,int,float
		"""
		## input validation
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized name')

		# check and get the variables
		for i in names:
			if i not in self._variables:
				raise NameError(i + ' not in Python environment.')
			elif type(i) not in [str, int, float]:
				raise TypeError('Only str, int, float can be passed to bash')

		# load them
		to_load = {i: self._variables[i] for i in names}
		self._environ.update(to_load)

	def dump_to_bash(self):
		"""Move all variables from Python variable dict to the Matlab environment"""
		self.py_to_bash(self.who_py)

	def bash_to_py(self, names, load : bool = True):
		"""Move variables from bash to Python
		Use `globals().update(bash_to_py(@names))` to add directly to local session

		Parameters
		----------
		names : str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names
		load : bool
			Whether to add to Python variable dict
			Default: True

		Returns
		-------
		dict[str: object]
			The requested variables

		Raises
		------
		ValueError
			If unrecognized names
		NameError
			If a variable not in the bash environment
		"""
		## input validation
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')

		# check and get the variables
		ret = {}
		for i in names:
			if i not in self._environ:
				raise NameError(str(i) + ' not in bash environment')
			else:
				ret[i] = self._environ[i]

		# load and return them
		if load: self._variables.update(ret)
		return ret

	def bash_to_r(self, names):
		"""Move variables from bash to R

		Parameters
		----------
		names: str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names

		Raises
		------
		RuntimeError
			If either the R environment is not alive
		ValueError
			If unrecognized @names
		NameError
			If a variable not in the bash environment
		"""
		## input validation
		if not self.isalive_r: raise RuntimeError('r_object is not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')
		
		# check and get the variables
		out = {}
		for i in names:
			if i not in self._environ:
				raise NameError(str(i) + ' not in bash environment.')
			else:
				out[i] = self._environ[i]
		
		# load them
		self._r_object.sendlines([
				k + ' <- ' + ('"' + v + '"' if type(v) is str else str(v))
					for k, v in out.items()
			]
		)

	def bash_to_mat(self, names):
		"""Move variables from bash to Matlab

		Parameters
		----------
		names: str, Iterable[str]
			If str: comma-separated list of variable names
			If Iterable[str]: list of variable names

		Raises
		------
		RuntimeError
			If either the Matlab environment is not alive
		ValueError
			If unrecognized @names
		NameError
			If a variable not in the bash environment
		"""
		## input validation
		if not self.isalive_mat: raise RuntimeError('mat_object is not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]): names = list(names)
		else: raise ValueError('Unrecognized @names')
		
		# check and get the variables
		out = {}
		for i in names:
			if i not in self._environ:
				raise NameError(str(i) + ' not in bash environment.')
			else:
				out[i] = self._environ[i]
		
		# bundle them
		temp_file = NamedTemporaryFile(suffix='.mat')
		sio.savemat(temp_file, out)
		temp_file.seek(0)

		# load them
		self._mat_object.sendlines('load \'' + temp_file.name + '\';')




# ------------------------------- Defaults ------------------------------- #
DEFAULT_DUMP = dump_dict
DEFAULT_DUMPS = dumps_json

# set system specific
if system() == 'Windows': as_multilang = as_multilang_windows
else: as_multilang = as_multilang_unix