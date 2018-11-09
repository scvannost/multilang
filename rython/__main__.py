from rython import as_rython
from sys import argv

if __name__ == '__main__':
	if len(argv) > 1:
		as_rython(argv[1])