from nawah_cli import __version__

from typing import Literal, Any

import argparse, os, logging, datetime, sys, subprocess, asyncio, traceback, shutil, urllib.request, re, tarfile, string, random, time

logger = logging.getLogger('nawah')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s  [%(levelname)s]  %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.setLevel(logging.INFO)


def nawah_cli():
	global sys, os

	if sys.version_info.major != 3 or sys.version_info.minor != 8:
		print('Nawah CLI can only run with Python3.8. Exiting.')
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
	
	app_config = {
		# [REF]: https://stackoverflow.com/a/47073723/2393762
		'admin_password': ['__ADMIN_PASSWORD__', ''.join([random.choice(string.ascii_letters + string.digits + string.punctuation ) for n in range(18)]).replace('\'', '^')],
		'anon_token_suffix': ['__ANON_TOKEN_SUFFIX__', ''.join([random.choice(string.digits) for n in range(24)])]
	}

	envs_defaults = {
		'dev_local': 'mongodb://localhost',
		'dev_server': 'mongodb://admin:admin@mongodb',
		'prod': 'mongodb://admin:admin@prod',
	}

	if not args.default_config:
		# [DOC] Allow user to specify custom config per the following Config Attrs
		logger.info('Not detected \'default-config\' CLI Arg. Attempting to create Nawah app with custom Config.')
		logger.info('If you would like to have app created with default config, stop the process, and re-run Nawah CLI with \'default-config\' CLI Arg.')
		# [DOC] envs: data_server
		logger.info('\'envs\' Config Attr provides environment-specific configuration. You will be required to specify \'data_server\' for each of the default available Nawah environments, namely \'dev_local\', \'dev_server\', and \'prod\'.')
		for env in envs_defaults.keys():
			while True:
				config_attr_val = input(f'\n> What would be the value for \'data_server\' Config Attr for environment \'{env}\'; The connection string to connect to your MongoDB host? [{envs_defaults[env]}]\n- ')
				if not config_attr_val:
					logger.info(f'Setting \'data_server\' Config Attr for environment \'{env}\' to default \'{envs_defaults[env]}\'.')
					app_config[f'{env}:data_server'] = [f'__{env.upper()}_DATA_SERVER__', (config_attr_val := envs_defaults[env])]
				else:
					logger.info(f'Setting \'data_server\' Config Attr for environment \'{env}\' to: \'{config_attr_val}\'.')
					app_config[f'{env}:data_server'] = [f'__{env.upper()}_DATA_SERVER__', config_attr_val]
				break
		# [DOC] env
		while True:
			config_attr_val = input('\n> What would be the value for \'env\'; Config Attr for default environnement to be used when invoking Nawah CLI \'launch\' command? [$__env.ENV]\n- ')
			if not config_attr_val:
				logger.info('Setting \'env\' Config Attr to default: \'$__env.ENV\'.')
				app_config['data_name'] = ['__ENV__', (config_attr_val := '$__env.ENV')]
				break
			elif config_attr_val not in list(envs_defaults.keys()) and not re.match(r'^\$__env\.[A-Za-z_]+$', config_attr_val):
				logger.error('\'env\' Config Attr can only be one of the environments names defined in \'envs\' Config Attr, or a valid Env Variable.')
			else:
				logger.info(f'Setting \'env\' Config Attr to: \'{config_attr_val}\'.')
				app_config['env'] = ['__ENV__', config_attr_val]
				break
		# [DOC] data_name
		while True:
			config_attr_val = input('\n> What would be the value for \'data_name\'; Config Attr for database name to be created on \'data_server\'? [nawah_data]\n- ')
			if not config_attr_val:
				logger.info('Setting \'data_name\' Config Attr to default: \'nawah_data\'.')
				app_config['data_name'] = ['__DATA_NAME__', (config_attr_val := 'nawah_data')]
				break
			elif not re.match(r'^[a-zA-Z0-9\-_]+$', config_attr_val):
				logger.error('\'data_name\' Config Attr can\'t have special characters other than underscores and hyphens in it.')
			else:
				logger.info(f'Setting \'data_name\' Config Attr to: \'{config_attr_val}\'.')
				app_config['data_name'] = ['__DATA_NAME__', config_attr_val]
				break
		# [DOC] locales
		while True:
			config_attr_val = input('\n> What would be the comma-separated, language_COUNTRY-formatted value for \'locales\'; Config Attr for localisations of your app? [ar_AE, en_AE]\n- ')
			if not config_attr_val:
				logger.info('Setting \'locales\' Config Attr to default: \'ar_AE, en_AE\'.')
				locales = ['ar_AE', 'en_AE']
				app_config['locales'] = ['__LOCALES__', (config_attr_val := 'ar_AE\', \'en_AE')]
				break
			else:
				try:
					locales = [re.match(r'^([a-z]{2}_[A-Z]{2})$', locale.strip()).group(0) for locale in config_attr_val.split(',')]
					logger.info(f'Setting \'locales\' Config Attr to: \'{config_attr_val}\'.')
					app_config['locales'] = ['__LOCALES__', '\', \''.join(locales)]
					break
				except:
					logger.error('An exception occurred while attempting to process value provided.')
					logger.error('\'locales\' Config Attr value should be provided as comma-separated, language_COUNTRY-formatted list of localisations.')
		# [DOC] locale
		while True:
			config_attr_val = input('\n> What would be the value for \'locale\'; Config Attr for default localisation of your app? [first value of \'locales\' Config Attr]\n- ')
			if not config_attr_val:
				logger.info(f'Setting \'locale\' Config Attr to first value of \'locales\' Config Attr: \'{locales[0]}\'.')
				app_config['locale'] = ['__LOCALE__', (config_attr_val := locales[0])]
				break
			elif config_attr_val not in locales:
				logger.error('\'locale\' Config Attr can only be one of the localisations defined in \'locales\' Config Attr.')
			else:
				logger.info(f'Setting \'locale\' Config Attr to: \'{config_attr_val}\'.')
				app_config['locale'] = ['__LOCALE__', config_attr_val]
				break
		# [DOC] admin_doc: email
		while True:
			config_attr_val = input('\n> What would be the value for \'admin_doc\'.\'email\'; Config Attr? [admin@app.nawah.localhost]\n- ')
			if not config_attr_val:
				logger.info('Setting \'admin_doc\'.\'email\' Config Attr to default: \'admin@app.nawah.localhost\'.')
				app_config['admin_doc:email'] = ['__ADMIN_DOC_EMAIL__', (config_attr_val := 'admin@app.nawah.localhost')]
				break
			elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', config_attr_val):
				logger.error('\'admin_doc\'.\'email\' Config Attr value is not a valid email address.')
			else:
				logger.info(f'Setting \'admin_doc\'.\'email\' Config Attr to: \'{config_attr_val}\'.')
				app_config['admin_doc:email'] = ['__ADMIN_DOC_EMAIL__', config_attr_val]
				break
	else:
		for env in envs_defaults.keys():
			app_config[f'{env}:data_server'] = [f'__{env.upper()}_DATA_SERVER__', envs_defaults[env]]
		app_config.update({
			'env': ['__ENV__', '$__env.ENV'],
			'data_name': ['__DATA_NAME__', 'nawah_data'],
			'locales': ['__LOCALES__', '\', \''.join(['ar_AE', 'en_AE'])],
			'locale': ['__LOCALE__', 'ar_AE'],
			'admin_doc:email': ['__ADMIN_DOC_EMAIL__', 'admin@app.nawah.localhost'],
		})
	
	logger.info('This will create an app with the following config:')
	for config_attr, config_set in app_config.items():
		logger.info(f'- {config_attr}: \'{config_set[1]}\'')

	def archive_members(*, archive: tarfile.TarFile, root_path: str, search_path: str = None):
		l = len(f'{root_path}/')
		for member in archive.getmembers():
			if member.path.startswith(f'{root_path}/{search_path or ""}'):
				member.path = member.path[l:]
				yield member
	
	app_path = os.path.realpath(os.path.join(args.app_path, args.app_name))
	framework_path = os.path.realpath(os.path.join(args.app_path, args.app_name, f'nawah-{args.api_level}.whl'))
	stubs_path = os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah'))
	req_path = os.path.realpath(os.path.join(args.app_path, args.app_name, 'requirements.txt'))

	template_url = f'https://github.com/nawah-io/nawah_app_template/archive/APIv{args.api_level}.tar.gz'
	logger.info(f'Attempting to download Nawah app template from: {template_url}')
	# [REF] https://stackoverflow.com/a/7244263/2393762
	template_archive, _ = urllib.request.urlretrieve(template_url)
	logger.info('Template archive downloaded successfully!')
	logger.info(f'Attempting to extract template archive to: {app_path}')
	with tarfile.open(name=template_archive, mode='r:gz') as archive:
		archive.extractall(
			path=app_path, members=archive_members(archive=archive, root_path=f'nawah_app_template-APIv{args.api_level}'),
		)
	logger.info('Template archive extracted successfully!')

	framework_url = f'https://github.com/nawah-io/nawah_framework_wheels/raw/master/{args.api_level}/nawah.whl'
	logger.info(f'Attempting to download Nawah framework from: {framework_url}')
	# [REF] https://stackoverflow.com/a/7244263/2393762
	with urllib.request.urlopen(framework_url) as response, open(framework_path, 'wb') as framework_file:
		framework_file.write(response.read())
	logger.info('Framework downloaded successfully!')

	stubs_url = f'https://github.com/nawah-io/nawah_framework_wheels/raw/master/{args.api_level}/stubs.tar.gz'
	logger.info(f'Attempting to download Nawah framework stubs from: {stubs_url}')
	stubs_archive, _ = urllib.request.urlretrieve(stubs_url)
	logger.info('Nawah framework stubs archive downloaded successfully!')
	logger.info(f'Attempting to extract Nawah framework stubs archive to: {stubs_path}')
	with tarfile.open(name=stubs_archive, mode='r:gz') as archive:
		archive.extractall(
			path=stubs_path, members=archive_members(archive=archive, root_path='.'),
		)
	logger.info('Nawah framework stubs archive extracted successfully!')

	req_url = f'https://github.com/nawah-io/nawah_framework_wheels/raw/master/{args.api_level}/requirements.txt'
	logger.info(f'Attempting to download Nawah framework requirements from: {req_url}')
	# [REF] https://stackoverflow.com/a/7244263/2393762
	with urllib.request.urlopen(req_url) as response, open(req_path, 'wb') as req_file:
		req_file.write(response.read())
	logger.info('Framework requirements downloaded successfully!')

	logger.info('Attempting to install Nawah framework requirements')
	pip_command = [sys.executable, '-m', 'pip', 'install', '--user', '-r']
	pip_call = subprocess.call(
		pip_command
		+ [os.path.join(args.app_path, args.app_name, 'requirements.txt')]
	)
	if pip_call != 0:
		logger.error(
			'\'pip\' call failed. Check console for more details. Exiting.'
		)
		exit(1)
	
	logger.info('Moving Nawah frameworks and deleting temp files')


	logger.info('Attempting to initialise empty Git repo for new Nawah app.')
	init_call = subprocess.call(
		['git', 'init'],
		cwd=os.path.realpath(os.path.join(args.app_path, args.app_name)),
	)
	if init_call != 0:
		logger.error(
			'Git init call failed. Check console for details, then create Git repo yourself.'
		)
	logger.info('Git repo initialised successfully!')

	logger.info('Attempting to config app template for new Nawah app.')
	with open(
		os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah_app.py')), 'r'
	) as f:
		nawah_app_file = f.read()
	with open(
		os.path.realpath(os.path.join(args.app_path, args.app_name, 'nawah_app.py')), 'w'
	) as f:
		nawah_app_file = nawah_app_file.replace('__PROJECT_NAME__', args.app_name, 1)
		for config_set in app_config.values():
			nawah_app_file = nawah_app_file.replace(config_set[0], config_set[1], 1)
		f.write(nawah_app_file)

	with open(
		os.path.realpath(os.path.join(args.app_path, args.app_name, '.gitignore')), 'r'
	) as f:
		gitignore_file = f.read()
	with open(
		os.path.realpath(os.path.join(args.app_path, args.app_name, '.gitignore')), 'w'
	) as f:
		f.write(gitignore_file.replace('PROJECT_NAME', args.app_name, 1))
	
	with open(
		os.path.realpath(os.path.join(args.app_path, args.app_name, 'LICENSE')), 'w'
	) as f:
		f.write('')

	with open(
		os.path.realpath(os.path.join(args.app_path, args.app_name, 'README.md')), 'w'
	) as f:
		f.write(f'''# {args.app_name}
This Nawas app project was created with Nawah CLI v{__version__}, with API Level {args.api_level}.''')

	os.rename(
		os.path.realpath(
			os.path.join(args.app_path, args.app_name, 'packages', 'PROJECT_NAME')
		),
		os.path.realpath(
			os.path.join(args.app_path, args.app_name, 'packages', args.app_name)
		),
	)

	logger.info(f'Congrats! Your Nawah app {args.app_name} is successfully created!')
