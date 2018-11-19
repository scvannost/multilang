"""The base environment objects

This is the core of multilang, and provides interfaces for interacting
with the R and Matlab environments using the `pexpect` package.

As pexpect does not support Windows, neither does this subpackge.

Classes
-------
RObject
	An interactive R environment
MatlabObject
	An interactive Matlab environment
"""


import pexpect


class RObject:
	"""A simple class that allows for R scripting

	Properties
	----------
	isalive
		Whether the R environment is alive
	before
		The text just produced by the CLI
	who
		A list of the variable names in the R environment
	
	Functions
	---------
	connect
		Connect to the R environment
	reconnect
		Reconnect to the R environmnet
	close
		Close the connection to the R environment
	send
		Send bare text to the R environment's CLI
	sendline
		Send a line to the R environment's CLI and wait for it to run
	sendlines
		Send multiple lines to the R environment's CLI
	expect
		Wait for the CLI to say a phrase
	"""

	def __init__(self, connect : bool = True, load : bool = False, timeout : int = 600):
		"""Setup an RObject
		
		Parameters
		----------
		connect : bool
			Whether to connect to the R environment
			If False, @load and @timeout are ignored.
			Default: True
		load : bool
			Whether to load the existing R workspace
			Default: False
		timeout : int
			Number of seconds until time out
			Default: 600
		"""
		self._r_object = None
		if connect: self.connect(load, timeout)

	def connect(self, load : bool = False, timeout : int = 600):
		"""Connect to an R environment
		Does nothing if `isalive`; use `reconnect`

		Parameters
		----------
		load : bool
			Whether to load the existing R workspace
		timeout : int
			Number of seconds until time out
			Default: 600
		"""
		if self.isalive: return
		if load:
			try:
				self._r_object = pexpect.spawn('R', timeout=timeout)
			except pexpect.ExceptionPexpct:
				raise OSError('R not accessible by the command: `$ R`')
		else:
			try:
				self._r_object = pexpect.spawn('R --no-restore', timeout=timeout)
			except pexpect.ExceptionPexpct:
				raise OSError('R not accessible by the command: `$ R --no-restore\nIf `$ R` should work, try with load = True`')
		self.expect('\r\n>')
		self._r_object.sendline('library("R.matlab")')
		self.expect('\r\n>')

	def send(self, line : str):
		"""Send bare text to the R command-line interface
		Does not append a line ending
		Use `sendline` if wanting to execute a command immediately.

		Parameters
		----------
		line : str
			what to send to the CLI

		Raises
		------
		TypeError
			If line is not str
		RuntimeError
			If is not alive
		"""
		if not self.isalive: raise RuntimeError('Not connected')
		if not (isinstance(line, str) or isinstance(line, bytes)):
			raise TypeError('line must be a str. got '+ str(line))
		self._r_object.send(line)

	def sendline(self, line : str):
		"""Send a line to the R command-line interface and wait for processing
		Appends a line ending if needed

		Parameters
		----------
		line : str
			what to send to the CLI

		Raises
		------
		TypeError
			If line is not str
		RuntimeError
			If is not alive
		Exception
			If R raises an error
		"""
		if not self.isalive: raise RuntimeError('Not connected')
		if not (isinstance(line, str) or isinstance(line, bytes)):
			raise TypeError('line must be str. got ' + str(line))
		self._r_object.sendline(line)
		self.expect(['\r\n>',r'(?<=[\r\n])\+'])
		if 'Error' in self.before:
			raise Exception(' '.join(self.before.split('\r\n')[1:]))

	def sendlines(self, lines):
		"""Send a set of lines to the R command-line interface sequentially
		and wait for them to run
		Appends line endings between each line

		Parameters
		----------
		lines : str, Iterable[str]
			If str: multiple lines to send to the CLI separated by line endings
			If Iterable[str]: a list of lines to send to the CLI

		Raises
		------
		TypeError
			If lines is not str, Iterable[str]
				or any element of the Iterable is not a str
		RuntimeError
			If is not alive
		Exception
			If R raises an error
		"""
		if type(lines) is str:
			lines = lines.replace('\r\n','\n').replace('\r','\n').split('\n')
		if not hasattr(lines, '__iter__'):
			raise TypeError('lines must have an __iter__ method')

		lines = list(lines)
		for i in lines:
			if not (isinstance(i, str) or isinstance(i, bytes)):
				raise TypeError('lines must only include str. got ' + str(i))

		self.sendline('\n'.join(lines))
		while not lines[-1].strip() in self.before:
			self.expect(['[\r\n]+>',r'\+'])
		if 'Error' in self.before:
			raise Exception(' '.join(self.before.split('\r\n')[1:]))

	def expect(self, phrase=['[\r\n]',r'\+']):
		"""Wait for a specific phrase
		Wraps `pexpect.spawn.expect`

		Parameters
		----------
		phrase : str, Iterable[str]
			If str: a regex pattern to wait for
			If Iterable[str]: a list of possible regex responses
			Also acceptable are the `TimeoutError` and `EOFError` classes

		Returns
		-------
		int
			The index of the phrase received if phrase is Iterable[str]
			0 if phrase is str

		Raises
		------
		RuntimeError
			If is not connected
		TimeoutError
			If the CLI does not produce acceptable output in time
		"""
		if not self.isalive: raise RuntimeError('Not connected')
		if not (isinstance(phrase, str) or isinstance(phrase, bytes)):
			if phrase is TimeoutError:
				phrase = pexpect.TIMEOUT
			elif phrase is EOFError:
				phrase = pexpect.EOF
			elif hasattr(phrase, '__iter__'):
				i = 0
				while i < len(phrase):
					if not (isinstance(phrase[i], str) or isinstance(phrase[i], bytes)):
						if phrase[i] is TimeoutError:
							phrase[i] = pexpect.TIMEOUT
						elif phrase[i] is EOFError:
							phrase[i] = pexpect.EOF
						else:
							raise TypeError('phrase entries must be str. got ' + str(phrase[i]))
					i += 1
			else:
				raise TypeError('phrase must be a str or Iterable[str]. got ' + str(phrase))
		try:
			return self._r_object.expect(phrase)
		except pexpect.TIMEOUT:
			raise TimeoutError('R did not respond')

	def close(self, save : bool = False, runLast : bool = True):
		"""Close the R environment

		Parameters
		----------
		save : bool
			Whether to save the environment
			Default: False
		runLast : bool
			Whether to run R's `.Last()` function before exiting
			Default: True
		"""
		if self.isalive:
			self._r_object.sendline(
					'q(save="'+ ('yes' if save else 'no') + '", runLast=' + ('TRUE' if runLast else 'FALSE') + ')'
				)
		self._r_object = None

	def reconnect(self, force : bool = False, load : bool = False, save : bool = False, runLast : bool = True):
		"""Reconnects to the R environment

		Parameters
		----------
		force : bool
			Whether to skip trying to neatly `close` the environment
			Doesn't allow for saving
			Default: False
		save : bool
			Whether to save the environment
			Default: False
		runLast : bool
			Whether to run R's `.Last()` function before exiting
			Default: True
		load : bool
			Whether to load the existing workspace upon reconnecting
		"""
		if force: self._r_object = None
		elif self.isalive: self.close(save, runLast)
		self.connect(load)

	@property
	def isalive(self):
		"""Whether is alive"""
		if self._r_object and self._r_object.isalive: return True
		else: return False

	@property
	def before(self):
		"""The last value R returned
		Will have non-value str characters: e.g. \\r, \\n"""
		if self.isalive:
			ret = self._r_object.before.decode('utf8').strip().replace(' \r','')
			return ret
		else: return ''

	@property
	def who(self):
		"""The list of variable names in the current R environment"""
		if not self.isalive: return []
		self.sendline('ls()')
		ret = self.before.replace('\r\n','').split('"')
		return ret[1::2]


class MatlabObject:
	"""A simple class that allows for Matlab scripting

	Properties
	----------
	isalive
		Whether the Matlab environment is alive
	before
		The text just produced by the CLI
	who
		A list of the variable names in the Matlab environment
	
	Functions
	---------
	connect
		Connect to the Matlab environment
	reconnect
		Reconnect to the Matlab environmnet
	close
		Close the connection to the Matlab environment
	send
		Send bare text to the Matlab environment's CLI
	sendline
		Send a line to the Matlab environment's CLI and wait for it to run
	sendlines
		Send multiple lines to the Matlab environment's CLI
	expect
		Wait for the CLI to say a phrase
	"""
	def __init__(self, connect = True, timeout : int = 600):
		"""Setup an MatlabObject
		
		Parameters
		----------
		connect : bool
			Whether to connect to the Matlab environment
			If False, @timeout is ignored
			Default: True
		timeout : int
			Number of seconds until time out
			Default: 600
		"""
		self._mat_object = None
		if connect: self.connect(timeout)

	def connect(self, timeout : int = 600):
		"""Connect to an Matlab environment
		Does nothing if `isalive`; use `reconnect`

		Parameters
		----------
		timeout : int
			Number of seconds until time out
			Default: 600
		"""
		if self.isalive: return
		try:
			self._mat_object = pexpect.spawn('matlab -nojvm -nodisplay -nosplash', timeout=timeout)
		except pexpect.ExceptionPexpct:
			raise OSError('Matlab not accessible by the command: `$ matlab -nojvm -nodisplay -nosplash`')
		self.expect('>>')

	def send(self, line):
		"""Send bare text to the Matlab command-line interface
		Does not append a line ending or ';'
		Use `sendline` if wanting to execute a command immediately.

		Parameters
		----------
		line : str
			what to send to the CLI

		Raises
		------
		RuntimeError
			If is not alive
		"""
		if not self.isalive: raise RuntimeError('Not connected')
		self._mat_object.send(line)

	def sendline(self, line):
		"""Send a line to the Matlab command-line interface and wait for processing
		Appends a line ending if needed

		Parameters
		----------
		line : str
			what to send to the CLI

		Raises
		------
		TypeError
			If line is not str
		RuntimeError
			If is not alive
		Exception
			If Matlab raises an error
		"""
		if not self.isalive: raise RuntimeError('Not connected')
		self._mat_object.sendline(line)
		self.expect('>>')
		if '\x08' in self.before:
			raise Exception(self.before.split('\x08')[1][:-3])

	def sendlines(self, lines):
		"""Send a set of lines to the Matlab command-line interface sequentially
		and wait for them to run
		Appends line endings between each line

		Parameters
		----------
		lines : str, Iterable[str]
			If str: multiple lines to send to the CLI separated by line endings
			If Iterable[str]: a list of lines to send to the CLI

		Raises
		------
		TypeError
			If lines is not str, Iterable[str]
				or any element of the Iterable is not a str
		RuntimeError
			If is not alive
		Exception
			If Matlab raises an error
		"""
		if type(lines) is str or not hasattr(lines, '__iter__'):
			self.sendline(lines)
		else:
			self.sendline('\n'.join(list(lines)))
			while not lines[-1] in self.before:
				self.expect('>>')
			if '\x08' in self.before:
				raise Exception(self.before.split('\x08')[1][:-3])

	def expect(self, phrase):
		"""Wait for a specific phrase
		Wraps `pexpect.spawn.expect`

		Parameters
		----------
		phrase : str, Iterable[str]
			If str: a regex pattern to wait for
			If Iterable[str]: a list of possible regex responses
			Also acceptable are the `TimeoutError` and `EOFError` classes

		Returns
		-------
		int
			The index of the phrase received if phrase is Iterable[str]
			0 if phrase is str

		Raises
		------
		RuntimeError
			If is not connected
		TimeoutError
			If the CLI does not produce acceptable output in time
		"""
		if not self.isalive: raise RuntimeError('Not connected')
		if not (isinstance(phrase, str) or isinstance(phrase, bytes)):
			if phrase is TimeoutError:
				phrase = pexpect.TIMEOUT
			elif phrase is EOFError:
				phrase = pexpect.EOF
			elif hasattr(phrase, '__iter__'):
				i = 0
				while i < len(phrase):
					if not (isinstance(phrase[i], str) or isinstance(phrase[i], bytes)):
						if phrase[i] is TimeoutError:
							phrase[i] = pexpect.TIMEOUT
						elif phrase[i] is EOFError:
							phrase[i] = pexpect.EOF
						else:
							raise TypeError('phrase entries must be str. got ' + str(phrase[i]))
					i += 1
			else:
				raise TypeError('phrase must be a str or Iterable[str]. got ' + str(phrase))
		try:
			return self._mat_object.expect(phrase)
		except pexpect.TIMEOUT:
			raise TimeoutError('Matlab did not respond')

	def close(self, force = False):
		"""Close the R environment

		Parameters
		----------
		force : bool
			Whether to bypass finish.m
			Default: False
		"""
		if self.isalive: self._mat_object.sendline('exit' + (' force' if force else ''))
		self._mat_object = None

	def reconnect(self, force = False):
		"""Reconnects to the Matlab environment

		Parameters
		----------
		force : bool
			Whether to skip trying to neatly `close` the environment
			Doesn't allow for saving
			Default: False
		"""
		if force: self._mat_object = None
		elif self.isalive: self.close()
		self.connect()

	@property
	def isalive(self):
		"""Whether is alive"""
		if self._mat_object and self._mat_object.isalive: return True
		else: return False

	@property
	def before(self):
		"""The last value Matlab returned
		Will have non-value str characters: e.g. \\r, \\n"""
		if self.isalive:
			ret = self._mat_object.before.decode('utf8').strip()
			return ret
		else: return ''

	@property
	def who(self):
		"""List of variable names in the current Matlab environment"""
		if not self.isalive: return []
		self.sendline('who')
		ret = self.before.split('\r\n\r\n')[2].strip().replace('\r\n','')
		return [i.strip() for i in ret.split(' ') if i]