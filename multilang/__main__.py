from multilang import as_multilang # platform already sorted here
from platform import system
from sys import argv

if __name__ == '__main__':
	if len(argv) > 1:
		as_multilang(argv[1])