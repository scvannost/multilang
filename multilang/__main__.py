
import argparse

parser = argparse.ArgumentParser(prog='python -m multilang',description='Run code in Python/R/Matlab/bash')
parser.add_argument('file', help='the file name to run')
parser.add_argument('-v', '--verbosity', nargs='?', default=1, type=int, choices=[0, 1, 2, 3], help='the level of things to print;\n0 is silent, 1 is default, 2 also prints switching environments, 3 is max')
parser.add_argument('-s', '--silent', action='store_true', help='same as `--verbosity 0`')
parser.add_argument('-t','--timeout', nargs='?', type=int, default=600, help='the number of seconds to wait for R or matlab to respond; default 600')

args = parser.parse_args()

from multilang import as_multilang
if args.silent:
	args.verbosity = 0

as_multilang(args.file, _verbosity=args.verbosity, _timeout=args.timeout)