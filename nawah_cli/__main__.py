import os

def main():
	if os.path.exists(os.path.join('.', 'nawah', 'cli.py')):
		import sys, subprocess
		if sys.argv[0].endswith('nawah_cli'):
			with open(sys.argv[0], 'r') as f:
				subprocess.call([f.readline()[2:-1], '-m', 'nawah'] + sys.argv[1:])
		else:
			subprocess.call([sys.argv[0], '-m', 'nawah_cli'] + sys.argv[1:])
		exit()
	else:
		from nawah_cli.cli import nawah_cli
		nawah_cli()


if __name__ == '__main__':
	main()