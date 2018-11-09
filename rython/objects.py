import pexpect

class RObject:
	"""A simple class that allows for R scripting"""

	def __init__(self, connect = True, load = False):
		"""If @connect, calls `connect` for you with @load."""
		self._r_object = None
		if connect: self.connect(load)

	def connect(self, load = False):
		"""Make an R environment\nDoes nothing if `isalive`; use `reconnect`\nIf @load, loads existing environment in the current location."""
		if self.isalive: return
		if load:
			self._r_object = pexpect.spawn('R', timeout=600)
		else:
			self._r_object = pexpect.spawn('R --no-restore', timeout=600)
		self._r_object.expect('\r\n>')
		self._r_object.sendline('library("R.matlab")')
		self._r_object.expect('\r\n>')

	def send(self, line):
		"""Sends bare text to the R command-line interface\nUse `sendline` if wanting to execute a command immediately."""
		if not self.isalive: raise Exception('Not connected')
		self._r_object.send(line)

	def sendline(self, line):
		"""Sends a line to the R command-line interface and waits for processing"""
		if not self.isalive: raise Exception('Not connected')
		self._r_object.sendline(line)
		self._r_object.expect(['\r\n>',r'\+'])
		if 'Error' in self.before:
			raise Exception(' '.join(self.before.split('\r\n')[1:]))

	def sendlines(self, lines):
		"""Sends a set of lines to the R command-line interface sequentially"""
		if type(lines) is str:
			lines = lines.split('\n')
		self.sendline('\n'.join(list(lines)))
		while not lines[-1].strip() in self.before:
			self.expect(['[\r\n]+>',r'\+'])
		if 'Error' in self.before:
			raise Exception(' '.join(self.before.split('\r\n')[1:]))

	def expect(self, phrase):
		"""Wraps `pexpect.spawn.expect`"""
		if not self.isalive: raise Exception('Not connected')
		self._r_object.expect(phrase)

	def close(self, save='no', runLast=True):
		"""Calls R `q()` to quit\nAll arguments passed to `q`\n\n@save tells whether or not to save the environment; ['no','yes']\n@runLast tells R whether to run the `.Last()` function before exiting."""
		if self.isalive: self._r_object.sendline('q(save="'+ save + '", runLast=' + ('TRUE' if runLast else 'FALSE') + ')')
		self._r_object = None

	def reconnect(self, force = False, load = False):
		"""Calls `close` if already `self.isalive, and calls `connect` with @load.\nIf @force, doesn't try to neatly `close` and just starts a new environment."""
		if force: self._r_object = None
		elif self.isalive: self.close()
		self.connect(load)

	@property
	def isalive(self):
		"""Returns whether is alive"""
		if self._r_object and self._r_object.isalive: return True
		else: return False

	@property
	def before(self):
		"""Returns the value R returned in the last call\nWill have non-value str characters: e.g. \\r, \\n"""
		if self.isalive: return self._r_object.before.decode('utf8').strip().replace(' \r','')
		else: return ''

	@property
	def who(self):
		"""Returns a list of variable names in the current R environment"""
		if not self.isalive: return []
		self.sendline('ls()')
		ret = self.before.replace('\r\n','').split('"')
		return ret[1::2]


class MatlabObject:
	"""A simple class that allows for Matlab scripting"""
	def __init__(self, connect = True):
		"""If @connect, calls `connect` for you."""
		self._mat_object = None
		if connect: self.connect()

	def connect(self):
		"""Make a Matlab command-line environment\nDoes nothing if `isalive`; use `reconnect`"""
		if self.isalive: return
		self._mat_object = pexpect.spawn('matlab -nojvm -nodisplay -nosplash')
		self._mat_object.expect('>>')

	def send(self, line):
		"""Sends bare text to the Matlab command-line interface\nUse `sendline` if wanting to execute a command immediately."""
		if not self.isalive: raise Exception('Not connected')
		self._mat_object.send(line)

	def sendline(self, line):
		"""Sends a line to the Matlab command-line interface and waits for processing"""
		if not self.isalive: raise Exception('Not connected')
		self._mat_object.sendline(line)
		self._mat_object.expect('>>')
		if '\x08' in self.before:
			raise Exception(self.before.split('\x08')[1][:-3])

	def sendlines(self, lines):
		"""Sends a set of lines to the Matlab command-line interface sequentially"""
		if type(lines) is str or not hasattr(lines, '__iter__'):
			self.sendline(lines)
		else:
			self.sendline('\n'.join(list(lines)))
			while not lines[-1] in self.before:
				self.expect('>>')
			if '\x08' in self.before:
				raise Exception(self.before.split('\x08')[1][:-3])

	def expect(self, phrase):
		"""Wraps `pexpect.spawn.expect`"""
		if not self.isalive: raise Exception('Not connected')
		self._mat_object.expect(phrase)

	def close(self, force = False):
		"""Calls Matlab's `exit` command\nIf @force, bypasses `finish.m`"""
		if self.isalive: self._mat_object.sendline('exit' + (' force' if force else ''))
		self._mat_object = None

	def reconnect(self, force = False):
		"""Calls `close` if already `self.isalive, and calls `connect`.\nIf @force, doesn't try to neatly `close` and just starts a new environment."""
		if force: self._mat_object = None
		elif self.isalive: self.close()
		self.connect()

	@property
	def isalive(self):
		"""Returns whether is alive"""
		if self._mat_object and self._mat_object.isalive: return True
		else: return False

	@property
	def before(self):
		"""Returns the value Matlab returned in the last call\nWill have non-value str characters: e.g. \\r, \\n"""
		if self.isalive: return self._mat_object.before.decode('utf8').strip()
		else: return ''

	@property
	def who(self):
		"""Returns a list of variable names in the current Matlab environment"""
		if not self.isalive: return []
		self.sendline('who')
		ret = self.before.split('\r\n\r\n')[2].strip().replace('\r\n','')
		return [i.strip() for i in ret.split(' ') if i]