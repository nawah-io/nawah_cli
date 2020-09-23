import os


def main():
	if os.path.exists(os.path.join('.', 'nawah_app.py')):
		# [REF] https://stackoverflow.com/a/3964691/2393762
		import sys, glob

		whl_name = glob.glob('nawah_*.whl')[0]
		# [REF] http://avrilomics.blogspot.com/2015/11/import-python-module-from-egg-file.html
		sys.path.insert(0, os.path.join('.', whl_name))
		from nawah.cli import nawah_cli

		nawah_cli()
	else:
		from nawah_cli.cli import nawah_cli

		nawah_cli()


if __name__ == '__main__':
	main()
