import os

def main():
	if os.path.exists(os.path.join('.', 'nawah', 'cli.py')):
		import sys, subprocess
		subprocess.call([sys.executable, '.'] + sys.argv[1:])
		exit()
	else:
		from nawah_cli.cli import nawah_cli
		nawah_cli()


if __name__ == '__main__':
	main()