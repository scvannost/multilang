"""
This module runs Python, R, Matlab, and bash code in the same file.
Note that the underlying connection relies on `pexpect`, which does not support a Windows environment.
Therefore this will not work in a Windows environment.

Expected uses are:
	1. In Python (interactive or script):
	   >>> import multilang
	   >>> fname = 'path/to/file.mul'
	   >>> ml = multilang.as_multilang(fname)
	   >>> # or you can do
	   >>> ml = multilang.Master()

	2. From Terminal:
	   $ python -m multilang path/to/file.mul

Passing variables between most environments is done using temporary .mat files.
Python's file interactions use scipy.io.
R's file interactions use R.matlab.
Matlab's file interactions use the `load` and `save` commands.
Bash's interactions are done using an environment dict, starting with os.environ.

Bash commands are run using Python's `subprocess.run` with `shell=True, executable='/bin/bash'`.
As Matlab is running interactively, it is a script and therefore function definitions are not allowed.
"""



# ------------------------------------ Imports ------------------------------------ #
import io
import numpy as np
import os
import pandas as pd
from random import choices
import re
import scipy.io as sio
from string import ascii_lowercase
import subprocess
from tempfile import NamedTemporaryFile

from .objects import *


# -------------------------------- Helper Functions -------------------------------- #
def py_to_bash(_line, _environ = None):
	"""
Move the variable names specificed in _line: #! bash -> <vars>
	from python into Optional[_environ].
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str]
@_environ is optional; a new environ dict is created if not given.

Returns an environ dict with the variables loaded.
	"""
	if not _environ: _environ = os.environ.copy()
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if _to_load[0] == '':
		return _environ

	_out = {}
	for _i in _to_load:
		if _i not in _VARIABLES:
			raise Exception(_i+' not in Python environment')
		elif type(_VARIABLES[_i]) not in [str, int, float]:
			# print(_i, _VARIABLES[_i], type(_VARIABLES[_i]))
			raise Exception('Only str, int, float can be passed to bash')
		else:
			_out[_i] = _VARIABLES[_i]
	_environ.update(_out)
	return _environ

def bash_to_py(_line, _environ, _load = True):
	"""
If _load, move the variable names specified in _line: #! python -> <vars>
	from _environ to the Python environment.
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str].
If _load, updates the local multilang space to include these variables; you can recover them using
	`dump()` or one of its alternatives.

Returns a dictionary of the loaded variables.
	"""
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if _to_load[0] == '':
		return {}

	_out = {}
	for _i in _to_load:
		if _i not in _environ:
			raise Exception(str(_i) + ' not in bash environment.')
		else:
			_out[_i] = _environ[_i]
	if _load:
		_VARIABLES.updat(_out)
	return _out

def bash_to_r(_line, _environ, _r_object = RObject()):
	"""
Move the variable names specified in _line: #! R -> <vars>
	from _environ into Optional[_r_object].
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str]
@_r_object is optional; a new RObject is created if not given.

Returns an RObject with the variables loaded.
	"""
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')
	
	if not _r_object.isalive:
		_r_object = RObject()
	if _to_load[0] == '':
		return _r_object

	_out = {}
	for _i in _to_load:
		if _i not in _environ:
			raise Exception(str(_i) + ' not in bash environment.')
		else:
			_out[_i] = _environ[_i]
	
	_r_object.sendlines([
			_k + ' <- ' + ('"' + _v + '"' if type(_v) is str else str(_v))
				for _k, _v in _out.items()
		]
	)
	return _r_object

def bash_to_mat(_line, _environ, _mat_object = MatlabObject()):
	"""
Move the variable names specified in _line: #! R -> <vars>
	from _environ into Optional[_mat_object].
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str]
@_mat_object is optional; a new RObject is created if not given.

Returns a MatObject with the variables loaded.
	"""
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if not _mat_object.isalive:
		_mat_object = MatlabObject()
	if _to_load[0] == '':
		return _mat_object

	_out = {}
	for _i in _to_load:
		if _i not in _environ:
			raise Exception(str(_i) + ' not in bash environment.')
		else:
			_out[_i] = _environ[_i]
	
	_temp_file = NamedTemporaryFile(suffix='.mat')
	sio.savemat(_temp_file, _out)
	_temp_file.seek(0)
	_mat_object.sendline('load \'' + _temp_file.name + '\';')

	return _mat_object

def r_to_bash(_line, _r_object, _environ = None):
	"""
Move the variable names specificed in _line: #! bash -> <vars>
	from R into Optional[_environ].
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str]
@_environ is optional; a new environ dict is created if not given.

Returns an environ dict with the variables loaded.
	"""
	if not _r_object.isalive:
		raise Exception('R connection was killed before things could be brought back to Python.')
	if not _environ: _environ = os.environ.copy()

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if _to_load[0] == '':
		return _environ

	_dump = r_to_py(_line, _r_object, _load=False)
	_out = {}
	for _i in _to_load:
		if _i not in _dump:
			raise Exception(str(_i) + ' not in R environment.')
		elif type(_dump[_i]) not in [str, int, float]:
			raise Exception('Only str, int, float can be passed to bash')
		else:
			_out[_i] = _dump[_i]
	_environ.update(_out)
	return _environ

def mat_to_bash(_line, _mat_object, _environ = None):
	"""
Move the variable names specificed in _line: #! bash -> <vars>
	from Matlab into Optional[_environ].
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str]
@_environ is optional; a new environ dict is created if not given.

Returns an environ dict with the variables loaded.
	"""
	if not _mat_object.isalive:
		raise Exception('Matlab connection was killed before things could be brought back to Python.')
	if not _environ: _environ = os.environ.copy()

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if _to_load[0] == '':
		return

	_dump = mat_to_py(_line, _mat_object, _load=False)
	_out = {}
	for _i in _to_load:
		if _i not in _dump:
			raise Exception(str(i) + ' not in Matlab environment')
		elif type(_dump[_i]) not in [str, int, float]:
			raise Exception('Only str, int, float can be passed to bash')
		else:
			_out[_i] = _dump[_i]
	_environ.update(_out)
	return _environ



def py_to_r(_line, _r_object = RObject()):
	"""
Move the variable names specified in _line: #! R -> <vars>
	from python into Optional[_r_object].
Also accepts a comma-separated str or Iterable[str]
@_r_object is optional; a new RObject is created if not given.

Returns an RObject with the variables loaded.
	"""
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')
	
	if not _r_object.isalive:
		_r_object = RObject()
	if _to_load[0] == '':
		return _r_object

	_temp = []
	_counter = 0
	while _counter < len(_to_load):
		_item = _to_load[_counter]

		# ignore if func(*args[str]), just look at func
		if '(' in _item and _item[-1] != ')':
			while _item[-1] != ')':
				_counter += 1
				_item += ',' + _to_load[_counter]

		if _item not in _VARIABLES:
			try: eval(_item.split('(')[0])
			except: raise Exception(_item.split('(')[0] + ' not in Python environment.')
			else:
				# _item is func(a[, b])
				for _i in _item[:-1].split('(')[1].split(','):
					if _i not in _VARIABLES:
						try: eval(_i)
						except: raise Exception(_i + ' not in Python environment.')
				_temp.append(_item)
		else: _temp.append(_item)

		_counter += 1

	_to_load = _temp

	_out = {}
	for _i in _to_load:
		if '(' in _i and ')' in _i:
			_name = _i.split('(')[1].split(')')[0]
			_item = [_VARIABLES[_j] if _j in _VARIABLES else eval(_j) for _j in _name.split(',')]

			try:
				_func = eval(_i.split('(')[0])
			except Exception:
				_out[_name] = _item
			else:
				_out.update(_func(*_name.split(',')))

		else: _out[_i] = _VARIABLES[_i]

	_temp_file = NamedTemporaryFile()
	sio.savemat(_temp_file, _out)
	_temp_file.seek(0)
	
	_random_name = ''.join(choices(ascii_lowercase, k=10))
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

def py_to_mat(_line, _mat_object = MatlabObject()):
	"""
Move the variable names specified in _line: #! matlab -> <vars>
	from python into Optional[_mat_object].
Also accepts a comma-separated str or Iterable[str]
@_mat_object is optional; a new MatlabObject is created if not given.

Returns a MatlabObject with the variables loaded.
	"""
	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if not _mat_object.isalive:
		_mat_object = MatlabObject()
	if _to_load[0] == '':
		return _mat_object

	_temp = []
	_counter = 0
	while _counter < len(_to_load):
		_item = _to_load[_counter]

		# ignore if func(*args[str]), just look at func
		if '(' in _item and _item[-1] != ')':
			while _item[-1] != ')':
				_counter += 1
				_item += ',' + _to_load[_counter]

		if _item not in _VARIABLES:
			try: eval(_item.split('(')[0])
			except: raise Exception(_item.split('(')[0] + ' not in Python environment.')
			else:
				# _item = func(a[, b])
				for _i in _item[:-1].split('(')[1].split(','):
					if _i not in _VARIABLES:
						try: eval(_i)
						except: raise Exception(_i + ' not in Python environment.')
				_temp.append(_item)
		else: _temp.append(_item)

		_counter += 1

	_to_load = _temp

	_out = {}
	for _i in _to_load:
		if '(' in _i and ')' in _i:
			_name = _i.split('(')[1].split(')')[0]
			_item = [_VARIABLES[_j] if _j in _VARIABLES else eval(_j) for _j in _name.split(',')]

			try:
				_func = eval(_i.split('(')[0])
			except Exception:
				_out[_name] = _item
			else:
				_out.update(_func(*_name.split(',')))

		else: _out[_i] = _VARIABLES[_i]

	_temp_file = NamedTemporaryFile(suffix='.mat')
	sio.savemat(_temp_file, _out)
	_temp_file.seek(0)
	_mat_object.sendline('load \'' + _temp_file.name + '\';')

	return _mat_object

def r_to_py(_line, _r_object, _load = True):
	"""
If _load, move the variable names specified in _line: #! python -> <vars>
	from _r_object back to the Python environment.
Also accepts a comma-separated str or Iterable[str].
Updates the local multilang space to include these variables; you can recover them using
	`dump()` or one of its alternatives.

Returns a dictionary of the loaded variables.
	"""
	if not _r_object.isalive:
		raise Exception('R connection was killed before things could be brought back to Python.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if _to_load[0] == '':
		return

	_who = _r_object.who
	for i in _to_load:
		if i not in _who:
			raise Exception(str(i) + ' not in R environment.')

	_random_name = ''.join(choices(ascii_lowercase, k=10))
	_r_object.sendline(_random_name + '<- tempfile(); ' + _random_name)
	_temp_file = str(_r_object.before).split('"')[1]


	_r_object.sendlines([
			'writeMat(paste(' + _random_name + ',".mat",sep=""), ' + ', '.join([i + '=' + i for i in _to_load]) + ')',
			'rm(' + _random_name + ')'
		])

	_loaded = sio.loadmat(_temp_file, squeeze_me=True)
	del _loaded['__globals__'], _loaded['__header__'], _loaded['__version__']
	if _load:
		_VARIABLES.update(_loaded)
	return _loaded

def r_to_mat(_line, _r_object, _mat_object = MatlabObject()):
	"""
Move the variable names specified in _line: #! matlab -> <vars>
	from R into Optional[_mat_object].
Also accepts a comma-separated str or Iterable[str]
@_mat_object is optional; a new MatlabObject is created if not given.

Returns a MatlabObject with the variables loaded.
	"""
	if not _r_object.isalive:
		raise Exception('R connection was killed before things could be brought to Matlab.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if not _mat_object.isalive:
		_mat_object = MatlabObject()
	if _to_load[0] == '':
		return _mat_object

	_who = _r_object.who
	for i in _to_load:
		if i not in _who:
			raise Exception(str(i) + ' not in R environment.')

	_random_name = ''.join(choices(ascii_lowercase, k=10))
	_r_object.sendline(_random_name + '<- tempfile(); ' + _random_name)
	_temp_file = str(_r_object.before).split('"')[1]

	_r_object.sendlines([
			'writeMat(paste(' + _random_name + ',".mat", sep=""), ' + ', '.join([ i + '=' + i for i in _to_load]) + ')',
			'rm(' + _random_name + ')'
		])

	_mat_object.sendline('load \'' + _temp_file + '\';')

	return _mat_object

def mat_to_py(_line, _mat_object, _load = True):
	"""
If _load, move the variable names specified in _line: #! python -> <vars>
	from _mat_object back to the Python environment.
Also accepts a comma-separated str or Iterable[str]
Updates the local multilang space to include these variables; you can recover them using
	dump()` or one of its alternatives.

Returns a dictionary of the loaded variables.
	"""
	if not _mat_object.isalive:
		raise Exception('Matlab connection was killed before things could be brought back to Python.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__'):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if _to_load[0] == '':
		return

	_who = _mat_object.who
	if any([i not in _who for i in _to_load]):
		raise Exception(str(i) + ' not in Matlab environment')

	_random_name = ''.join(choices(ascii_lowercase, k=10))
	_mat_object.sendline(_random_name + ' = tempname')
	_temp_file = _mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]

	_mat_object.sendlines([
			'save ' + _temp_file + ' ' + ' '.join(_to_load),
			'clear ' + _random_name
		])

	_loaded = sio.loadmat(_temp_file, squeeze_me=True)
	del _loaded['__globals__'], _loaded['__header__'], _loaded['__version__']
	if _load:
		_VARIABLES.update(_loaded)
	return _loaded

def mat_to_r(_line, _mat_object, _r_object = RObject()):
	"""
Move the variable names specified in _line: #! R -> <vars>
	from Matlab into Optional[_r_object].
Also accepts a comma-separated str or Iterable[str]
@_r_object is optional; a new RObject is created if not given.

Returns an RObject with the variables loaded.
	"""
	if not _mat_object.isalive:
		raise Exception('Matlab connection was killed before things could be brought back to Python.')

	if type(_line) is str and ('#!' in _line or '%!' in _line):
		if not '->' in _line:
			raise Exception('Misformatted line: "' + _line + '"')
		_to_load = _line.split('->')[1].replace(' ','').split(',')
	elif type(_line) is str:
		_to_load = _line.replace(' ','').split(',')
	elif hasattr(_line, '__iter__') and all([type(i) is str for i in _line]):
		_to_load = list(_line)
	else:
		raise Exception('Unrecognized _line')

	if not _r_object.isalive:
		_r_object = RObject()
	if _to_load[0] == '':
		return _r_object

	_who = _mat_object.who
	for i in _to_load:
		if i not in _who:
			raise Exception(str(i) + ' not in Matlab environment')

	_random_name = ''.join(choices(ascii_lowercase, k=10))
	_mat_object.sendline(_random_name + ' = tempname')
	_temp_file = _mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]

	_mat_object.sendlines([
			'save ' + _temp_file + '.mat ' + ' '.join(_to_load),
			'clear ' + _random_name
		])
	
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


def dump(_file='', **kwargs):
	"""
Defaults to `dump_dict`, and so returns a dict of all local Python variables.
Changing `DEFAULT_DUMP` changes this action.
	"""
	return DEFAULT_DUMP(_file, **kwargs)

def dumps(**kwargs):
	"""
Returns a str version of the local Python variables.
Defaults to `dumps_json`, and so the str is in JSON format.
Changing `DEFAULT_DUMPS` changes this action.
	"""
	return DEFAULT_DUMPS('', **kwargs)


def dump_dict(_file='', **kwargs):
	"""
Returns a dict of {name: value} for all local Python variables.
Use `globals().update(dump())` to bring variables into the global scope,
	or `locals().update(dump())` for the local scope.
@_file is optional and ignored if given.
**kwargs are ignored.
	"""
	return {k:v for k,v in _VARIABLES.items() if not k[0] is '_'}

def dump_mat(_file, **kwargs):
	"""
Takes @_file as a str that is the file name or a file_like with a `write`
	method and outputs all the local Python variables as a .mat file.
**kwargs are passed to` scipy.io.savemat`.
	"""
	if hasattr(_file, 'write'):
		sio.savemat(_file, *[k for k,v in _VARIABLES.items() if not k[0] is '_'], **kwargs)
	else:
		sio.savemat(open(_file, 'w'), *[k for k,v in _VARIABLES.items() if not k[0] is '_'], **kwargs)

def dump_json(_file, **kwargs):
	"""
Takes @_file as  a str that is the file name or a file_like with a `write`
	method and outputs all the localPython  variables as a .json file.
**kwargs are passed to `json.dump`
	"""
	if not '_json' in _VARIABLES:
		import json as _json

	if hasattr(_file,'write'):
		_json.dump({k:v for k,v in _VARIABLES.items() if not k[0] is '_'}, _file, **kwargs)
	else:
		_json.dump({k:v for k,v in _VARIABLES.items() if not k[0] is '_'}, open(_file, 'w'), **kwargs)

def dumps_json(_file='', **kwargs):
	"""
Returns a JSON-formatted str of {name: value} for all local Python variables.
**kwargs are passed to `json.dumps`
@_file is optional and ignored if given.
	"""
	if not '_json' in _VARIABLES:
		import json as _json
	json.dumps({k:v for k,v in _VARIABLES.items() if not k[0] is '_'}, **kwargs)

def mod(a,b):
	"""Replaces Python's modulo operator due to its use in comments"""
	return a%b

def as_array(var: str, extras: str = 'True'):
	"""
Built-in function to pass as an np.array of values
For some special types, additional information is also passed when @extras is 'True'.
If it is a pd.DataFrame, df_index and df_columns are also passed as lists.

To define you own wrapping functions, use the @multilang decorator in the Python environment.
	Currently only available from Python to another environment.
It should take only str as inputs, with its first as the name of the variable.
	Local variables can be accessed by _VARIABLES[name], see example.
It should return a dict of {name: value} of things to pass through `sio.savemat` into the next environment.

The definition of this function follows as an example:
	[1] #! multilang
	[2] import pandas as pd
	[3]
	[4] @multilang
	[5] def as_array(var: str, extras: str = 'True'):
	[6] 	obj = _VARIABLES[var]
	[7] 	if extras != 'True':
	[8] 		return {var: np.array(obj)}
	[9] 	elif type(obj) is pd.core.frame.DataFrame:
	[10] 		return {var: np.array(obj),
	[11]				var+'_index': obj.index.values.tolist(),
	[12]				var+'_columns': obj.columns.values.tolist()}
	[13]	else:
	[14]		return {var: np.array(obj)}
	"""

	obj = _VARIABLES[var]

	if extras != 'True':
		return {var: np.array(obj)}
	elif type(obj) is pd.core.frame.DataFrame:
		return {var: np.array(obj),
				var+'_index': obj.index.values.tolist(),
				var+'_columns': obj.columns.values.tolist()}
	else:
		return {var: np.array(obj)}



# ----------------------------------- Constants ----------------------------------- #
global _VARIABLES
_VARIABLES = {}

DEFAULT_DUMP = dump_dict
DEFAULT_DUMPS = dumps_json

SUPPORTED = ['python', 'matlab', 'r', 'bash']


# -------------------------------- Main Functions -------------------------------- #
def as_multilang_windows(_lines):
	"""
A simple interface for rython coding on Windows.
Not yet implemented, but will recapitulate `as_multilang`.
	"""
	raise NotImplementedError('To be used in a Windows environment')


def as_multilang(_lines, _r_object = RObject(), _mat_object = MatlabObject(), _environ = None, **kwargs):
	"""
A simple interface for multilang coding.
Takes an IO buffer with `readlines -> Iterable[Union[str, bytes]]` (preferred) or
						`read -> Union[str, bytes]` method,
	  a Union[str, bytes] with line breaks, or
	  an Iterable[Union[str,bytes]] without linebreaks.
You can pass @_r_object or @_mat_object to use those instead of creating new ones.
kwargs are set as variables in the Python environment
Returns a `Master` object of the environments used to run the script.

"Shebangs" (i.e. #! or %!) are used as the statements to both say this is multilang code
	and to switch between R, Python, Matlab, and bash.
The file/str/bytes should read as so:
	[1] #! multilang [R, Python, Matlab, bash]
	[2] # code here`
	[3] #! R/Python/Matlab/bash -> vars
	[4] # code here
	[.] # ...
	[n] #! Python -> vars

All multilang scripts start with `#! multilang` then an optional language.
If no initial language is given, Python is assumed.
Scripts should end with a Python switch line to retrieve any variables back
	into the Python environment.
The suggested extension for a multilang file is .mul.

To switch languages, `#! <lang> -> <vars>` is used to switched to <lang>.
	<vars> is an optional comma-separated list of variables to transfer between the environemnts.
Language names are NOT case-sensitive and depend only on the existence of 'r', 'p', 'm', or 'b'.
Spaces after shebangs are optional.
Variables to pass can also be wrapped in functions such as `as_array`.
	This is currently only available when switching out of Python.

Note that Python's modulo operator `%` is overwritten as a comment initiator.
Use `mod(a,b)` to perform this option.
Python's `%=` is not affected.

Use @multilang to define a function in the rython space.
This is useful for defining custom variables-wrapping functions to pass custom objects between environments.
See `as_array` for an explanation of how these work.
Any built-in Python/Multilang function can also be used in this way.
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
	if _lines[0][:2] not in ['#!','%!'] or 'multilang' not in _lines[0].lower():
		# if not multilang format, just run it as Python script
		exec('\n'.join(_lines))
		_VARIABLES.update({k:v for k,v in locals().items() if not k[0] is '_'})
		return
	for _n, _i in enumerate(_lines[1:]):
		if len(_i) > 2 and _i[:2] in ['#!', '%!']:
			_l = _i[2:].strip().replace(' ','').split('->')
			if not any([i in _l[0].lower() for i in 'rpmb']) or len(_l) > 2:
				raise Exception('Improperly formatted call in line ' + str(_n+2))

	while not _lines[0]:
		_lines = _lines[1:]

	
	_temp = _lines[0].split(' ')[-1].lower()
	if 'multilang' in _temp or 'p' in _temp:
		_lang = 'p'
	elif 'r' in _temp:
			_lang = 'r'
	elif 'm' in _temp:
		_lang = 'm'
	elif 'b' in _temp and not 'm' in _temp:
		# avoid b from matlab
		_lang = 'b'
	else:
		raise Exception('Unknown language was specified')

	if kwargs:
		_VARIABLES.update(kwargs)
	if not _environ: _environ = os.environ.copy()			

	# loop through given code
	_counter = 1 # skip first line
	# print(_lines)
	while _counter < len(_lines):
		_current_line = _lines[_counter].strip()
		# print(_counter, _current_line)
		if not _current_line or (_current_line[0] in '#%' and _current_line[1] != '!'):
			# print('comment')
			_counter += 1
			continue

		# if currently in python
		elif _lang == 'p':
			# print('python')
			if _current_line[:2] in ['#!','%!']:
				# print('shebang')
				if 'r' in _current_line.lower().split('->')[0]:
					_lang = 'r'
					_r_object = py_to_r(_current_line, _r_object)
				elif 'm' in _current_line.lower().split('->')[0]:
					_lang = 'm'
					_mat_object = py_to_mat(_current_line, _mat_object)
				elif 'b' in _current_line.lower().split('->')[0]:
					_lang = 'b'
					_environ = py_to_bash(_current_line, _environ)
				_counter += 1
				continue
			elif '@multilang' in _current_line and re.search(r'^def\s*[a-zA-Z_]+\s*\(.*?\)\s*:$', _lines[_counter+1].strip()):
				# print('multilang function')
				_end = _counter + 1
				_l = _lines[_end].strip(' ')
				_comment = re.search(r'(?<!\\)[#%]', _l)
				_l = _l[:_comment.end() if _comment and _comment.start() > 0 else len(_l)]

				_name = _l.split('def ')[1].split('(')[0].strip()

				_search = re.search(r'\t+(?:.)', _l)
				_tabs = _search.end() if _search and _search.end() > 0 else 0
				_to_exec = [_l[_tabs:]]
				while _l and _l[:2] not in ['#!', '%!'] and _end < len(_lines)-1:
					_end += 1
					_l = _lines[_end].strip(' ')
					_search = re.search(r'\t+(?:.)', _l)
					_curr_tabs = _search.end() if _search and _search.end() > 0 else 0
					if _curr_tabs <= _tabs:
						break
					elif _l and _l[0] not in '%#':
						_comment = re.search(r'(?<!\\)[#%](?!=)', _l)
						_to_exec.append(_l[_tabs:_comment.start() if _comment and _comment.start() > 0 else len(_l)])

				# exec('\n'.join(_to_exec))
				globals().update({_name: locals()[_name]})
				_counter = _end
				continue

			else: # otherwise, do the thing
				# print('executing python...')
				globals().update(_VARIABLES)

				_end = _counter
				_l = _lines[_end].strip(' ')
				_comment = re.search(r'(?<!\\)[#%]', _l)
				_l = _l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)]

				_to_exec = [_l] if _l and _l[0] not in '%#' else []
				while _l and _l[:2] not in ['#!','%!'] and '@multilang' not in _l and _end < len(_lines)-1:
					_end += 1
					_l = _lines[_end]
					# print(_end, _lines[_end])
					if _l and  _l[0] not in '%#':
						_comment = re.search(r'(?<!\\)[#%](?!=)', _l)
						_to_exec.append(_l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)])
				# [print(i) for i in _to_exec]
				exec('\n'.join(_to_exec))

				_VARIABLES.update({k:v for k,v in locals().items() if not k[0] is '_'})
				_counter = _end+1 if _end == len(_lines)-1 else _end
				# print(_counter)
				continue

		# if currently in bash
		elif _lang == 'b':
			if _current_line[:2] in ['#!', '%!']:
				if 'p' in _current_line.lower().split('->')[0]:
					_lang = 'p'
					mat_to_py(_current_line, _mat_object)
				elif 'r' in _current_line.lower().split('->')[0]:
					_lang = 'r'
					_r_object = mat_to_r(_current_line, _mat_object, _r_object)
				elif 'm' in _current_line.lower().split('->')[0]:
					_lang = 'm'
					_mat_object = py_to_mat(_current_line, _mat_object)
				_counter += 1
				continue
			else: # otherwise do the thing
				_end = _counter
				_l = _lines[_end].strip(' ')
				_comment = re.search(r'(?<!\\)[#%]', _l)
				_l = _l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)]

				_to_exec = [_l] if _l and _l[0] not in '%#' else []
				while _l and _l[:2] not in ['#!','%!'] and _end < len(_lines)-1:
					_end += 1
					_l = _lines[_end]
					# print(_end, _lines[_end])
					if _l and  _l[0] not in '%#':
						_comment = re.search(r'(?<!\\)[#%](?!=)', _l)
						_to_exec.append(_l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)])
				# [print(i) for i in _to_exec]
				subprocess.run('\n'.join(_to_exec), shell=True, env={k:str(v) for k,v in _environ.items()}, executable='/bin/bash').check_returncode()

				_environ = os.environ.copy()
				_counter = _end+1 if _end == len(_lines)-1 else _end

		# if currently in R
		elif _lang == 'r':
			# print('r')
			if _current_line[:2] in ['#!','%!']:
				# print('shebang')
				if 'p' in _current_line.lower().split('->')[0]: # if switching to Python
					_lang = 'p'
					r_to_py(_current_line, _r_object)
				elif 'm' in _current_line.lower().split('->')[0]: # if switching to Matlab
					_lang = 'm'
					_mat_object = r_to_mat(_current_line, _r_object, _mat_object)
				elif 'b' in _current_line.lower().split('->')[0]: # if switching to bash
					_lang = 'b'
					_environ = r_to_bash(_line, _environ)
				_counter += 1
				continue
			else: # otherwise do the thing
				# print('executing r')
				_end = _counter
				_l = _lines[_end].strip()
				_comment = re.search(r'(?<!\\)[#%]', _l)
				_l = _l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)]
				_to_exec = [_l] if _l and _l[0] not in '#%' else []
				while _l[:2] not in ['#!', '%!'] and _end < len(_lines)-1:
					_end += 1
					_l = _lines[_end].strip()
					if _l and _l[0] not in '#%':
						_comment = re.search(
							# have to ignore all the %...% operators
							r'(?<!\\|(?:[(?:in)(?:between)(?:chin)\+(?:\+replace):(?:do)(?:dopar)>(?:<>)(?:T>)$/\*ox]))[#%](?![(?:in)(?:between)(?:chin)\+(?:\+replace):(?:do)(?:dopar)>(?:<>)(?:T>)$/\*ox]*%)',
							_l)
						_to_exec.append(_l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)])
				# [print(i) for i in _to_exec]
				_r_object.sendlines(_to_exec)
				_counter = _end+1 if _end == len(_lines)-1 else _end
				continue

		# if currently in Matlab
		elif _lang == 'm':
			# print('matlab')
			if _current_line[:2] == '#!':
				# print('shebang')
				if 'p' in _current_line.lower().split('->')[0]:
					_lang = 'p'
					mat_to_py(_current_line, _mat_object)
				elif 'r' in _current_line.lower().split('->')[0]:
					_lang = 'r'
					_r_object = mat_to_r(_current_line, _mat_object, _r_object)
				elif 'b' in _current_line.lower().split('->')[0]:
					_lang = 'b'
					_environ = mat_to_bash(_line, _environ)
				_counter += 1
				continue
			else: # otherwise do the thing
				# print('executing matlab')
				_end = _counter
				_l = _lines[_end].strip()
				_comment = re.search(r'(?<!\\)[#%]', _l)
				_l = _l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)]
				_to_exec = [_l] if _l[0] not in '#%' else []

				while _l[:2] not in ['#!', '%!'] and _end < len(_lines)-1:
					_end += 1
					_l = _lines[_end].strip()
					if _l and _l[0] not in '#%':
						_comment = re.search(r'(?<!\\)[#%]', _l)
						_to_exec.append(_l[:_comment.start() if _comment and _comment.start() > 0 else len(_l)])

				_mat_object.sendlines(_to_exec)
				_counter = _end+1 if _end == len(_lines)-1 else _end
				continue

		else:
			raise Exception('Invalid definition of _lang.')

	ret = Master(r_object=_r_object, mat_object=_mat_object)
	ret.load_from_dict(_VARIABLES)
	# print()
	return ret



# -------------------------------- Main Classes -------------------------------- #
class Master:
	"""
An object that allows for interfacing with both R and Matlab environments.
Relies on RObject and MatlabObject classes.

Unlike `as_multilang()`, do not pass misformatted comments to the R/bash (no %) or Matlab (no #) environments.

m-, mat-, and matlab-based function names are all supported.
mat is the base implementation, the others just wrap.
	"""
	def __init__(self, r = True, mat = True, load_r = False, r_object = None, mat_object = None, environ = None, m = True, matlab = True):
		"""
@r and @mat specify whether to connect to R and Matlab environments respectively.
These connections can be made later using `connect`, `connect_r`, or `connect_mat`.
You can pass in existing RObjects or MatlabObjects through @r_object and @mat_object to wrap them.
For @load, see `Robject.connect`.
		"""
		if not r_object: self._r_object = RObject(r, load_r)
		else: self._r_object = r_object

		mat = mat and m and matlab
		if not mat_object: self._mat_object = MatlabObject(mat)
		else: self._mat_object = mat_object

		if not environ: self. _environ = os.environ.copy()
		else: self._environ = environ
		self._orig_env = os.environ.copy()

		self._variables = {}

	@property
	def who(self):
		"""Returns a dict of {'mat': `who_m`, 'r': `who_r`, 'py':`who_py`}"""
		return {'mat': self.who_m, 'r': self.who_r, 'py': self.who_py, 'bash': self.who_bash}

	def connect(self, r = True, mat = True, load_r = False):
		"""
Makes connections to R if @r and Matlab if @mat
Does nothing if the connection already exists.
For @load, see `Robject.connect`.
		"""
		if r: self.connect_r(load_r)
		if mat: self.connect_mat()

	def reconnect(self, r = True, mat = True, force = True, load_r = False):
		"""
Calls `r_object.reconnect` if @r and `mat_object.reconnect` if @mat
For @load, see `Robject.connect`.
		"""
		if r: self.r_object.reconnect(force, load_r)
		if mat: self.mat_object.reconnect(force)


	def to_py(self, name, value):
		"""See `load`"""
		self.load(name, value)
	def load_to_py(self, name, value):
		"""See `load`"""
		self.load(name, value)
	def load(self, name, value):
		"""Loads the given variable to the Python environment as @name = @value"""
		self._variables[name] = value

	def drop(self, name):
		"""Drop the given variable from the Python environment"""
		del self._variables[name]

	def load_from_dict(self, d):
		"""
Add the given values to the Python environment
	as {name: value}
Use `load_from_dict(globals())` to load all variables
		"""
		self._variables.update(d)

	@property
	def who_py(self):
		"""Returns a list of the variable names in the Python environment."""
		return list(self._variables.keys())

	def dump_py(self):
		"""Returns a dict of {name:value} for the variables in the Python environment"""
		return self._variables.copy()


	def dump_all(self, precedence = 'all'):
		"""
Move all the vars from the R and Matlab environments to the Python environment.
Also returns values as dict
If a variable name is repeated, @precedence sets which wins.
	If None, raises an Exception if there is a repeated name.
	If 'all', prefixes the variable name with the environment
@precedence in ['r', 'mat', 'all', None]
Use `globals().update(dump_all())` to add directly to local session
		"""
		if not self.isalive_r: raise Exception('r_object not alive')
		if not self.isalive_mat: raise Exception('mat_object not alive')

		names = self.who_r
		random_name = ''.join(choices(ascii_lowercase, k=10))
		self.r_object.sendline(random_name + '<- tempfile(); ' + random_name)
		temp_file = str(self.r_object.before).split('"')[1]
		self.r_object.sendlines([
				'writeMat(paste(' + random_name + ',".mat", sep=""), ' + ', '.join([i + '=' + i for i in names]) + ')',
				'rm(' + random_name + ')'
			])
		r = sio.loadmat(temp_file, squeeze_me=True)
		del r['__globals__'], r['__header__'], r['__version__']

		names = self.who_mat
		random_name = ''.join(choices(ascii_lowercase, k=10))
		self.mat_object.sendline(random_name + ' = tempname')
		temp_file = self.mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]
		self.mat_object.sendlines([
				'save ' + temp_file + ' ' + ' '.join(names),
				'clear ' + random_name
			])
		mat = sio.loadmat(temp_file, squeeze_me=True)
		del mat['__globals__'], mat['__header__'], mat['__version__']

		if not precedence:
			for i in r:
					raise Exception('Repeated variable name ' + i)
			# if it makes it here, no repeats
			mat.update(r)
			ret = mat
		
		elif 'r' in precedence:
			mat.update(r)
			ret = mat
		elif 'm' in precedence:
			r.update(mat)
			ret = r

		elif precedence == 'all':
			fix = []
			for i in r:
				if i in mat:
					fix.append(i)

			for i in fix:
				r['r_'+i] = r[i]
				del r[i]
				mat['mat_'+i] = mat[i]
				del mat[i]

			mat.update(r)
			ret = mat
		else:
			raise ValueError('@precedence must be \'r\', \'mat\', \'all\', or None')

		self._variables.update(ret)
		return ret

	def connect_r(self, load_r = False):
		"""Starts a connection to an R environment. See `RObject.connect`"""
		self._r_object.connect(load_r)

	@property
	def r_object(self):
		"""Returns the underlying RObject"""
		return self._r_object
	@property
	def isalive_r(self):
		"""Returns if the R environment is alive. See `RObject.isalive`"""
		return self._r_object.isalive
	@property
	def who_r(self):
		"""Returns a list of the variable names in R"""
		if not self.isalive_r: return []
		return self.r_object.who

	def r(self, code):
		"""Run R code"""
		if not self.isalive_r: raise Exception('r_object not alive')
		code = code.replace('\r\n','\n').replace('\r','\n').split('\n')
		while len(code[-1]) < 1:
			code = code[:-1]
		self.r_object.sendlines(code)

	def r_to_m(self, names):
		"""See `r_to_mat`"""
		self.r_to_mat(names)
	def r_to_matlab(self, names):
		"""See `r_to_mat`"""
		self.r_to_mat(names)
	def r_to_mat(self, names):
		"""Move the vars in @names from the R environment to the Matlab environment"""
		if not self.isalive_r: raise Exception('r_object not alive')
		elif not self.isalive_mat: self.connect_mat()
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		who = self.who_r
		if any([i not in who for i in names]):
			raise Exception(str(i) + ' not in R environment')

		random_name = ''.join(choices(ascii_lowercase, k=10))
		self.r_object.sendline(random_name + '<- tempfile(); ' + random_name)
		temp_file = str(self.r_object.before).split('"')[1]
		self.r_object.sendlines([
				'writeMat(paste(' + random_name + ',".mat", sep=""), ' + ', '.join([i + '=' + i for i in names]) + ')',
				'rm(' + random_name + ')'
			])

		self.mat_object.sendline('load \'' + temp_file + '\';')

	def r_to_py(self, names, load=True):
		"""
Load the vars in @names from the R environment to the Python environment
Also returns values as dict
Use `globals().update(r_to_py(@names))` to add directly to local session
		"""
		if not self.isalive_r: raise Exception('r_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		who = self.who_r
		for i in names:
			if i not in who:
				raise Exception(str(i) + ' not in R environment')

		random_name = ''.join(choices(ascii_lowercase, k=10))
		self.r_object.sendline(random_name + '<- tempfile(); ' + random_name)
		temp_file = str(self.r_object.before).split('"')[1]
		self.r_object.sendlines([
				'writeMat(' + random_name + ', ' + ', '.join([i + '=' + i for i in names]) + ')',
				'rm(' + random_name + ')'
			])
		ret = sio.loadmat(temp_file, appendmat=False, squeeze_me=True)
		del ret['__globals__'], ret['__header__'], ret['__version__']
		if load: self._variables.update(ret)
		return ret

	def r_to_bash(self, names):
		"""Move the vars in @names from the R environment to the bash environment"""
		if not self.isalive_r: raise Exception('r_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		dump = self.dump_r(load=False)
		ret = {}
		for i in names:
			if i not in dump:
				raise Exception(str(i) + ' not in R environment.')
			elif type(dump[i]) not in [str, int, float]:
				raise Exception('Only str, int, float can be passed to bash')
			else:
				ret[i] = _dump[i]
		self._environ.update(ret)

	def py_to_r(self, names, **kwargs):
		"""
Load the vars in @names to the R environment
@names can either be a comma-separated str or Iterable[str]
Make sure you have loaded the variables first with `load` or `load_from_dict`
Use @as_array = True to pass pd.DataFrame as np.ndarray
		"""
		if not self.isalive_r: self.connect_r()

		if type(names) is str:
			names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized name')

		for i in names:
			if i not in self._variables:
				raise Exception(i + ' not in Python environment.')

		temp_file = NamedTemporaryFile(suffix='.mat')
		to_load = {i: self._variables[i] for i in names}
		if 'as_array' in kwargs and kwargs['as_array']:
			temp = list(to_load.items())
			n = 0
			while n < len(temp):
				k,v = temp[n]
				if type(v) is pd.core.frame.DataFrame:
					to_load[k] = np.array(v)
					to_load[k + '_index'] = v.index.values.tolist()
					to_load[k + '_columns'] = v.columns.values.tolist()
				n += 1

		sio.savemat(temp_file, to_load)
		temp_file.seek(0)

		random_name = ''.join(choices(ascii_lowercase, k=10))
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

	def dump_r(self, load=True):
		"""
Move all the vars from the R environment to the Python environment
Also returns as a dict
		"""
		return self.r_to_py(self.who_r, load)

	def dump_to_r(self):
		"""Send all the vars from the Python environment to the R environment"""
		self.py_to_r(self.who_py)



	def connect_m(self):
		"""See `connect_mat`"""
		self._mat_object.connect()
	def connect_matlab(self):
		"""See `connect_mat`"""
		self._mat_object.connect()
	def connect_mat(self):
		"""Starts a connection to a Matlab environment. See `MatlabObject.connect`"""
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
		"""Returns if the Matlab environment is alive. See `MatlabObject.isalive`"""
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
		self.mat_object.sendlines(code)

	def m_to_r(self, names):
		"""See mat_to_r"""
		self.mat_to_r(names)
	def matlab_to_r(self, names):
		"""See mat_to_r"""
		self.mat_to_r(names)
	def mat_to_r(self, names):
		"""Move the vars in @names from mat_object to r_object."""
		if not self.isalive_mat: raise Exception('mat_object is not alive')
		elif not self.isalive_r: self.connect_r()
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		who = self.who_mat
		if any([i not in who for i in names]):
			raise Exception(str(i) + ' not in Matlab environment')

		random_name = ''.join(choices(ascii_lowercase, k=10))
		self.mat_object.sendline(random_name + ' = tempname')
		temp_file = self.mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]
		self.mat_object.sendlines([
				'save ' + temp_file + ' ' + ' '.join(names),
				'clear ' + random_name
			])

		self.random_name = ''.join(choices(ascii_lowercase, k=10))
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
		"""
	Load the vars in @names from the Matlab environment to the Python environment
	Also returns values as dict
	Use `globals().update(mat_to_py(@names))` to add directly to local session
		"""
		if not self.isalive_mat: raise Exception('mat_object is not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		who = self.who_mat
		if any([i not in who for i in names]):
			raise Exception(str(i) + ' not in Matlab environment')

		random_name = ''.join(choices(ascii_lowercase, k=10))
		self.mat_object.sendline(random_name + ' = tempname')
		temp_file = self.mat_object.before.split('\r\n\r\n')[2].strip()[1:-1]
		self.mat_object.sendlines([
				'save ' + temp_file + ' ' + ' '.join(names),
				'clear ' + random_name
			])
		
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
		"""Move the vars in @names from the Matlab environment to the bash environment"""
		if not self.isalive_mat: raise Exception('mat_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		dump = self.dump_mat(load=False)
		ret = {}
		for i in names:
			if i not in dump:
				raise Exception(str(i) + ' not in R environment.')
			elif type(dump[i]) not in [str, int, float]:
				raise Exception('Only str, int, float can be passed to bash')
			else:
				ret[i] = _dump[i]
		self._environ.update(ret)

	def py_to_m(self, names):
		"""See `py_to_mat`"""
		self.py_to_mat(names)
	def py_to_matlab(self, names):
		"""See `py_to_mat`"""
		self.py_to_mat(names)
	def py_to_mat(self, names):
		"""
Loads the given variables from the Python environment to the Matlab environment
@names can either be a comma-separated str or Iterable[str]
Make sure you have loaded the variables first with `load` or `load_from_dict`
		"""
		if not self.isalive_mat: self.connect_mat()
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		for i in names:
			if i not in self._variables:
				raise Exception(i + ' not in Python environment.')

		temp_file = NamedTemporaryFile(suffix='.mat')
		sio.savemat(temp_file, {i: self._variables[i] for i in names})
		temp_file.seek(0)

		self.mat_object.sendline('load \'' + temp_file.name + '\';')

	def dump_m(self, load=True):
		"""See `dump_mat`"""
		return self.dump_mat(load)
	def dump_matlab(self, load=True):
		"""See `dump_mat`"""
		return self.dump_mat(load)
	def dump_mat(self, load=True):
		"""
Move all the vars from the Matlab environment to the Python environment
Also returns as a dict
		"""
		return self.mat_to_py(self.who_mat, load)

	def dump_to_m(self):
		"""See `dump_to_mat`"""
		self.dump_to_mat()
	def dump_to_matlab(self):
		"""See `dump_to_mat`"""
		self.dump_to_mat()
	def dump_to_mat(self):
		"""Send all the vars from the Python environment to the Matlab environment"""
		self.py_to_mat(self.who_py)



	@property
	def who_bash(self):
		"""Returns a list of the variable names in R"""
		return [k for k in self._environ.keys() if k not in self._orig_env]

	def dump_bash(self,load=True):
		"""
Move all the vars from the Matlab environment to the Python environment
Also returns as a dict
		"""
		return self.bash_to_py(self.who_bash, load)

	def bash(self, code):
		"""Run bash code"""
		code = code.replace('\r\n','\n').replace('\r','\n').split('\n')
		while len(code[-1]) < 1:
			code = code[:-1]
		subprocess.run('\n'.join(code), shell=True, env={k:str(v) for k,v in self._environ.items()}, executable='/bin/bash').check_returncode()
		self._environ = os.environ.copy()

	def py_to_bash(self, names):
		"""
Move the variable names specificed to the shell.
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str]
	"""
		if type(names) is str:
			names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized name')

		for i in names:
			if i not in self._variables:
				raise Exception(i + ' not in Python environment.')

		to_load = {i: self._variables[i] for i in names}
		self._environ.update(to_load)

	def bash_to_py(self, names, load=True):
		"""
Load the vars in @names from the shell to the Python environment
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str].

Returns values as dict
Use `globals().update(bash_to_py(@names))` to add directly to local session
		"""
		if not self.isalive_r: raise Exception('r_object not alive')
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')

		ret = {}
		for i in names:
			if i not in self._environ:
				raise Exception(str(i) + ' not in bash environment')
			else:
				ret[i] = self._environ[i]
		if load: self._variables.update(ret)
		return ret

	def bash_to_r(self, names):
		"""
Load the vars in @names from the shell to the R environment
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str].
		"""
		if not self.isalive_r: self.connect_r()
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')
		
		out = {}
		for i in names:
			if i not in self._environ:
				raise Exception(str(i) + ' not in bash environment.')
			else:
				out[i] = self._environ[i]
		
		self._r_object.sendlines([
				k + ' <- ' + ('"' + v + '"' if type(v) is str else str(v))
					for k, v in out.items()
			]
		)

	def bash_to_mat(self, names):
		"""
Load the vars in @names from the shell to the Matlab environment
Only variables that are str, int, float are allowed to be passed.
Also accepts a comma-separated str or Iterable[str].
		"""
		if not self.isalive_mat: self.connect_mat()
		if type(names) is str: names = names.replace(' ','').split(',')
		elif hasattr(names, '__iter__') and all([type(i) is str for i in names]):
			names = list(names)
		else:
			raise Exception('Unrecognized @names')
		
		out = {}
		for i in names:
			if i not in self._environ:
				raise Exception(str(i) + ' not in bash environment.')
			else:
				out[i] = self._environ[i]
		
		temp_file = NamedTemporaryFile(suffix='.mat')
		sio.savemat(temp_file, out)
		temp_file.seek(0)
		self._mat_object.sendlines('load \'' + temp_file.name + '\';')