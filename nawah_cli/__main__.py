import os


def main():
	# [DOC] If Nawah CLI is started from app context, use Framework CLI
	if os.path.exists(os.path.join('.', 'nawah_app.py')):
		print('Nawah CLI is running from Nawah project directory. Using framework CLI.')
		# [REF] https://stackoverflow.com/a/3964691/2393762
		import sys, glob

		# [DOC] Check if alt framework is provided
		if '--nawah-path' in sys.argv:
			try:
				nawah_path_index = sys.argv.index('--nawah-path')
				nawah_path = os.path.realpath(sys.argv[nawah_path_index + 1])
				sys.path.insert(0, nawah_path)
				# [DOC] Remove nawah_path CLI Arg and value from sys.argv
				sys.argv.pop(nawah_path_index)
				sys.argv.pop(nawah_path_index)
			except:
				print('Either no value for \'nawah_path\' CLI Arg, or invalid. Exiting.')
				exit(1)

		# [DOC] Attempt to import Framework CLI
		try:
			from nawah.cli import nawah_cli
		except:
			print('Failed to import Nawah Framework CLI.')
			print(
				'If you are using \'nawah_path\' CLI Arg, confirm the framework path again. Make sure it is pointing to top-level framework directory, and not \'nawah\' inside it.'
			)
			print('Exiting.')
			exit(1)

		nawah_cli()

	else:
		from nawah_cli.cli import nawah_cli

		nawah_cli()


if __name__ == '__main__':
	main()
