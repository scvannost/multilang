from mutlilang import as_mutlilang, as_mutlilang_windows
from platform import system
from sys import argv

if __name__ == '__main__':
	if len(argv) > 1:
		if system() == 'Windows':
			as_mutlilang_windows(argv[1])
		else:
			as_mutlilang(argv[1])
