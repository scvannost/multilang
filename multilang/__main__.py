from multilang import as_multilang, as_multilang_windows
from platform import system
from sys import argv

if __name__ == '__main__':
	if len(argv) > 1:
		if system() == 'Windows':
			as_multilang_windows(argv[1])
		else:
			as_multilang(argv[1])
