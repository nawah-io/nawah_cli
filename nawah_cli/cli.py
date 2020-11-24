from nawah_cli import __version__

from typing import Dict, Literal, Any

import argparse, os, logging, datetime, sys, subprocess, asyncio, traceback, shutil, urllib.request, re, tarfile, string, random, time, json, tempfile

logger = logging.getLogger('nawah')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s  [%(levelname)s]  %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.INFO)


def nawah_cli():
	global sys, os

	if sys.version_info.major != 3 or sys.version_info.minor < 8:
		print('Nawah CLI can only run with Python >= 3.8. Exiting.')
		exit()

	# [REF] https://stackoverflow.com/a/41881271/2393762
	def api_level_type(arg_value):
		if not re.compile(r'^[0-9]\.[0-9]{1,2}$').match(arg_value):
			raise argparse.ArgumentTypeError('API Level is invalid')
		return arg_value

	parser = argparse.ArgumentParser()
	parser.add_argument(
		'--version',
		help='Show Nawah CLI version and exit',
		action='version',
		version=f'Nawah CLI v{__version__}',
	)

	subparsers = parser.add_subparsers(
		title='Command', description='Nawah CLI command to run', dest='command'
	)

	parser_create = subparsers.add_parser('create', help='Create new Nawah app')
	parser_create.set_defaults(func=create)
	parser_create.add_argument('app_name', type=str, help='Name of the app to create')
	parser_create.add_argument(
		'app_path',
		type=str,
		nargs='?',
		help='Path to create new Nawah app. [default .]',
		default='.',
	)
	parser_create.add_argument(
		'--default-config',
		help='Create new Nawah app with default config',
		action='store_true',
	)
	parser_create.add_argument(
		'--api-level',
		type=api_level_type,
		help='App API Level',
		default='1.0',
	)
	parser_create.add_argument(
		'--template',
		help='Alternative local app template path',
	)

	args = parser.parse_args()
	if args.command:
		args.func(args)
	else:
		parser.print_help()


def create(args: argparse.Namespace):
	global os, subprocess

	if args.app_name == 'nawah_app':
		logger.error(
			'Value for \'app_name\' CLI Arg is invalid. Name can\'t be \'nawah_app\''
		)
		exit(1)
	elif not re.match(r'^[a-z][a-z0-9_]+$', args.app_name):
		logger.error(
			'Value for \'app_name\' CLI Arg is invalid. Name should have only small letters, numbers, and underscores.'
		)
		exit(1)

	app_path = os.path.realpath(os.path.join(args.app_path, args.app_name))
	framework_path = os.path.realpath(
		os.path.join(args.app_path, args.app_name, f'framework-{args.api_level}.whl')
	)
	stubs_path = os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah'))
	req_path = os.path.realpath(
		os.path.join(args.app_path, args.app_name, 'requirements.txt')
	)
	progress_path = os.path.realpath(
		os.path.join(args.app_path, args.app_name, 'progress.json')
	)

	progress = None

	if os.path.exists(app_path):
		logger.info(
			'Specified \'app_name\' already existing in \'app_path\'. Attempting to check for earlier progress.'
		)
		if os.path.exists(progress_path):
			logger.info('File \'progress.json\' found. Attempting to process it.')
			try:
				with open(progress_path, 'r') as progress_file:
					progress_config = json.loads(progress_file.read())
					progress = progress_config['step']
					app_config = progress_config['config']
			except Exception as e:
				logger.error(
					'An exception occurred while attempting to process file \'progress.json\'.'
				)
				logger.error(f'Exception details: {e}')
				logger.error('Exiting.')
				exit(1)
		else:
			logger.error('File \'progress.json\' was not found. Exiting.')
			exit(1)

	# [DOC] Populating app_config
	if not progress:
		app_config = create_step_config(args=args)
		logger.info('This will create an app with the following config:')
		for config_attr, config_set in app_config.items():
			logger.info(f'- {config_attr}: \'{config_set[1]}\'')
	else:
		logger.info('Continuing to create app with loaded progress config:')
		for config_attr, config_set in app_config.items():
			logger.info(f'- {config_attr}: \'{config_set[1]}\'')

	# [DOC] Create app workspace
	if not progress:

		def archive_members(
			*, archive: tarfile.TarFile, root_path: str, search_path: str = None
		):
			l = len(f'{root_path}/')
			for member in archive.getmembers():
				if member.path.startswith(f'{root_path}/{search_path or ""}'):
					member.path = member.path[l:]
					yield member

		if args.template:
			logger.info(f'Attempting to use specified \'template\': \'{args.template}\'')
			template_path = os.path.realpath(args.template)
			if (
				not os.path.exists(template_path)
				or not os.path.isdir(template_path)
				or not os.path.exists(os.path.join(template_path, 'nawah_app.py'))
			):
				logger.error('Specified \'template\' is not a valid Nawah app template. Exiting.')
				exit(1)

			logger.info(
				'Attempting to create temporary template archive from specified \'template\''
			)
			temp_template_archive = tempfile.NamedTemporaryFile(mode='w')
			# [REF] https://stackoverflow.com/a/17081026
			# [REF] https://stackoverflow.com/a/16000963
			with tarfile.open(temp_template_archive.name, 'w:gz') as archive:
				archive.add(
					template_path,
					arcname=f'nawah_app_template-APIv{args.api_level}',
					filter=lambda member: None if '.git/' in member.name else member,
				)
			logger.info('Template archive created successfully!')
			template_archive = temp_template_archive.name
		else:
			template_url = f'https://github.com/nawah-io/nawah_app_template/archive/APIv{args.api_level}.tar.gz'
			logger.info(f'Attempting to download Nawah app template from: {template_url}')
			# [REF] https://stackoverflow.com/a/7244263/2393762
			template_archive, _ = urllib.request.urlretrieve(template_url)
			logger.info('Template archive downloaded successfully!')

		logger.info(f'Attempting to extract template archive to: {app_path}')
		with tarfile.open(name=template_archive, mode='r:gz') as archive:
			archive.extractall(
				path=app_path,
				members=archive_members(
					archive=archive, root_path=f'nawah_app_template-APIv{args.api_level}'
				),
			)
		logger.info('Template archive extracted successfully!')

		framework_url = f'https://github.com/nawah-io/nawah_framework_wheels/raw/master/{args.api_level}/nawah.whl'
		logger.info(f'Attempting to download Nawah framework from: {framework_url}')
		# [REF] https://stackoverflow.com/a/7244263/2393762
		with urllib.request.urlopen(framework_url) as response, open(
			framework_path, 'wb'
		) as framework_file:
			framework_file.write(response.read())
		logger.info('Framework downloaded successfully!')

		stubs_url = f'https://github.com/nawah-io/nawah_framework_wheels/raw/master/{args.api_level}/stubs.tar.gz'
		logger.info(f'Attempting to download Nawah framework stubs from: {stubs_url}')
		stubs_archive, _ = urllib.request.urlretrieve(stubs_url)
		logger.info('Nawah framework stubs archive downloaded successfully!')
		logger.info(f'Attempting to extract Nawah framework stubs archive to: {stubs_path}')
		with tarfile.open(name=stubs_archive, mode='r:gz') as archive:
			archive.extractall(
				path=stubs_path,
				members=archive_members(archive=archive, root_path='.'),
			)
		logger.info('Nawah framework stubs archive extracted successfully!')

		req_url = f'https://github.com/nawah-io/nawah_framework_wheels/raw/master/{args.api_level}/requirements.txt'
		logger.info(f'Attempting to download Nawah framework requirements from: {req_url}')
		# [REF] https://stackoverflow.com/a/7244263/2393762
		with urllib.request.urlopen(req_url) as response, open(req_path, 'wb') as req_file:
			req_file.write(response.read())
		logger.info('Framework requirements downloaded successfully!')

	if not progress or progress == 1:
		progress = None
		logger.info('Attempting to install Nawah framework requirements')
		pip_command = [sys.executable, '-m', 'pip', 'install', '--user', '-r']
		try:
			pip_call = subprocess.call(
				pip_command + [os.path.join(args.app_path, args.app_name, 'requirements.txt')]
			)
			if pip_call != 0:
				raise Exception()
		except Exception as e:
			dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=1)
			logger.error('\'pip\' call failed. Check console for more details. Exiting.')
			exit(1)

	if not progress or progress == 2:
		progress = None
		logger.info('Moving Nawah frameworks and deleting temp files')

		logger.info('Attempting to initialise empty Git repo for new Nawah app.')
		try:
			init_call = subprocess.call(
				['git', 'init'],
				cwd=os.path.realpath(os.path.join(args.app_path, args.app_name)),
			)
			if init_call != 0:
				raise Exception()
			logger.info('Git repo initialised successfully!')
		except Exception as e:
			dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=2)
			logger.error(
				'Git init call failed. Check console for details, then create Git repo yourself.'
			)
			exit(1)

	if not progress or progress == 3:
		progress = None
		logger.info('Attempting to config app template for new Nawah app.')
		try:
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah_app.py')), 'r'
			) as f:
				nawah_app_file = f.read()
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah_app.py')), 'w'
			) as f:
				nawah_app_file = nawah_app_file.replace('__PROJECT_NAME__', args.app_name, 2)
				for config_set in app_config.values():
					nawah_app_file = nawah_app_file.replace(config_set[0], config_set[1], 1)
				f.write(nawah_app_file)
		except Exception as e:
			dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=3)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 4:
		progress = None
		try:
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, '.gitignore')), 'r'
			) as f:
				gitignore_file = f.read()
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, '.gitignore')), 'w'
			) as f:
				f.write(gitignore_file.replace('PROJECT_NAME', args.app_name, 1))
		except Exception as e:
			dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=4)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 5:
		progress = None
		try:
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, 'LICENSE')), 'w'
			) as f:
				f.write('')
		except Exception as e:
			dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=5)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 6:
		progress = None
		try:
			with open(
				os.path.realpath(os.path.join(args.app_path, args.app_name, 'README.md')), 'w'
			) as f:
				f.write(
					f'''# {args.app_name}
This Nawas app project was created with Nawah CLI v{__version__}, with API Level {args.api_level}.'''
				)
		except Exception as e:
			dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=6)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	if not progress or progress == 7:
		progress = None
		try:
			os.rename(
				os.path.realpath(
					os.path.join(args.app_path, args.app_name, 'packages', 'PROJECT_NAME')
				),
				os.path.realpath(
					os.path.join(args.app_path, args.app_name, 'packages', args.app_name)
				),
			)
		except Exception as e:
			dump_progress(args=args, app_config=app_config, progress_path=progress_path, step=7)
			logger.error('An exception occurred.')
			logger.error(f'Exception details: {e}')
			logger.error('Exiting.')
			exit(1)

	logger.info(f'Congrats! Your Nawah app {args.app_name} is successfully created!')


def create_step_config(*, args: argparse.Namespace):
	app_config = {
		# [REF]: https://stackoverflow.com/a/47073723/2393762
		'admin_password': [
			'__ADMIN_PASSWORD__',
			''.join(
				[
					random.choice(string.ascii_letters + string.digits + string.punctuation)
					for n in range(18)
				]
			)
			.replace('\'', '^')
			.replace('\\', '/'),
		],
		'anon_token_suffix': [
			'__ANON_TOKEN_SUFFIX__',
			''.join([random.choice(string.digits) for n in range(24)]),
		],
	}

	envs_defaults = {
		'dev_local': 'mongodb://localhost',
		'dev_server': 'mongodb://admin:admin@mongodb',
		'prod': 'mongodb://admin:admin@prod',
	}

	if not args.default_config:
		# [DOC] Allow user to specify custom config per the following Config Attrs
		logger.info(
			'Not detected \'default-config\' CLI Arg. Attempting to create Nawah app with custom Config.'
		)
		logger.info(
			'If you would like to have app created with default config, stop the process, and re-run Nawah CLI with \'default-config\' CLI Arg.'
		)
		# [DOC] envs: data_server
		logger.info(
			'\'envs\' Config Attr provides environment-specific configuration. You will be required to specify \'data_server\' for each of the default available Nawah environments, namely \'dev_local\', \'dev_server\', and \'prod\'.'
		)
		for env in envs_defaults.keys():
			while True:
				config_attr_val = input(
					f'\n> What would be the value for \'data_server\' Config Attr for environment \'{env}\'; The connection string to connect to your MongoDB host? [{envs_defaults[env]}]\n- '
				)
				if not config_attr_val:
					logger.info(
						f'Setting \'data_server\' Config Attr for environment \'{env}\' to default \'{envs_defaults[env]}\'.'
					)
					app_config[f'{env}:data_server'] = [
						f'__{env.upper()}_DATA_SERVER__',
						(config_attr_val := envs_defaults[env]),
					]
				else:
					logger.info(
						f'Setting \'data_server\' Config Attr for environment \'{env}\' to: \'{config_attr_val}\'.'
					)
					app_config[f'{env}:data_server'] = [
						f'__{env.upper()}_DATA_SERVER__',
						config_attr_val,
					]
				break
		# [DOC] env
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'env\'; Config Attr for default environnement to be used when invoking Nawah CLI \'launch\' command? [$__env.ENV]\n- '
			)
			if not config_attr_val:
				logger.info('Setting \'env\' Config Attr to default: \'$__env.ENV\'.')
				app_config['data_name'] = ['__ENV__', (config_attr_val := '$__env.ENV')]
				break
			elif config_attr_val not in list(envs_defaults.keys()) and not re.match(
				r'^\$__env\.[A-Za-z_]+$', config_attr_val
			):
				logger.error(
					'\'env\' Config Attr can only be one of the environments names defined in \'envs\' Config Attr, or a valid Env Variable.'
				)
			else:
				logger.info(f'Setting \'env\' Config Attr to: \'{config_attr_val}\'.')
				app_config['env'] = ['__ENV__', config_attr_val]
				break
		# [DOC] data_name
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'data_name\'; Config Attr for database name to be created on \'data_server\'? [nawah_data]\n- '
			)
			if not config_attr_val:
				logger.info('Setting \'data_name\' Config Attr to default: \'nawah_data\'.')
				app_config['data_name'] = ['__DATA_NAME__', (config_attr_val := 'nawah_data')]
				break
			elif not re.match(r'^[a-zA-Z0-9\-_]+$', config_attr_val):
				logger.error(
					'\'data_name\' Config Attr can\'t have special characters other than underscores and hyphens in it.'
				)
			else:
				logger.info(f'Setting \'data_name\' Config Attr to: \'{config_attr_val}\'.')
				app_config['data_name'] = ['__DATA_NAME__', config_attr_val]
				break
		# [DOC] locales
		while True:
			config_attr_val = input(
				'\n> What would be the comma-separated, language_COUNTRY-formatted value for \'locales\'; Config Attr for localisations of your app? [ar_AE, en_AE]\n- '
			)
			if not config_attr_val:
				logger.info('Setting \'locales\' Config Attr to default: \'ar_AE, en_AE\'.')
				locales = ['ar_AE', 'en_AE']
				app_config['locales'] = ['__LOCALES__', (config_attr_val := 'ar_AE\', \'en_AE')]
				break
			else:
				try:
					locales = [
						re.match(r'^([a-z]{2}_[A-Z]{2})$', locale.strip()).group(0)
						for locale in config_attr_val.split(',')
					]
					logger.info(f'Setting \'locales\' Config Attr to: \'{config_attr_val}\'.')
					app_config['locales'] = ['__LOCALES__', '\', \''.join(locales)]
					break
				except:
					logger.error('An exception occurred while attempting to process value provided.')
					logger.error(
						'\'locales\' Config Attr value should be provided as comma-separated, language_COUNTRY-formatted list of localisations.'
					)
		# [DOC] locale
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'locale\'; Config Attr for default localisation of your app? [first value of \'locales\' Config Attr]\n- '
			)
			if not config_attr_val:
				logger.info(
					f'Setting \'locale\' Config Attr to first value of \'locales\' Config Attr: \'{locales[0]}\'.'
				)
				app_config['locale'] = ['__LOCALE__', (config_attr_val := locales[0])]
				break
			elif config_attr_val not in locales:
				logger.error(
					'\'locale\' Config Attr can only be one of the localisations defined in \'locales\' Config Attr.'
				)
			else:
				logger.info(f'Setting \'locale\' Config Attr to: \'{config_attr_val}\'.')
				app_config['locale'] = ['__LOCALE__', config_attr_val]
				break
		# [DOC] admin_doc: email
		while True:
			config_attr_val = input(
				'\n> What would be the value for \'admin_doc\'.\'email\'; Config Attr? [admin@app.nawah.localhost]\n- '
			)
			if not config_attr_val:
				logger.info(
					'Setting \'admin_doc\'.\'email\' Config Attr to default: \'admin@app.nawah.localhost\'.'
				)
				app_config['admin_doc:email'] = [
					'__ADMIN_DOC_EMAIL__',
					(config_attr_val := 'admin@app.nawah.localhost'),
				]
				break
			elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', config_attr_val):
				logger.error(
					'\'admin_doc\'.\'email\' Config Attr value is not a valid email address.'
				)
			else:
				logger.info(
					f'Setting \'admin_doc\'.\'email\' Config Attr to: \'{config_attr_val}\'.'
				)
				app_config['admin_doc:email'] = ['__ADMIN_DOC_EMAIL__', config_attr_val]
				break
	else:
		for env in envs_defaults.keys():
			app_config[f'{env}:data_server'] = [
				f'__{env.upper()}_DATA_SERVER__',
				envs_defaults[env],
			]
		app_config.update(
			{
				'env': ['__ENV__', '$__env.ENV'],
				'data_name': ['__DATA_NAME__', 'nawah_data'],
				'locales': ['__LOCALES__', '\', \''.join(['ar_AE', 'en_AE'])],
				'locale': ['__LOCALE__', 'ar_AE'],
				'admin_doc:email': ['__ADMIN_DOC_EMAIL__', 'admin@app.nawah.localhost'],
			}
		)

	return app_config


def dump_progress(
	*, args: argparse.Namespace, app_config: Dict[Any, Any], progress_path: str, step: int
):
	with open(progress_path, 'w') as progress_file:
		progress_file.write(
			json.dumps(
				{
					'step': step,
					'args': {
						'app_path': args.app_path,
						'app_name': args.app_name,
					},
					'config': app_config,
				}
			)
		)
