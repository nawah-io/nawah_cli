import setuptools

with open('README.md', 'r') as f:
	long_description = f.read()

setuptools.setup(
	name='nawah_cli',
	version='0.1.0',
	author='Mahmoud Abduljawad',
	author_email='mahmoud@masaar.com',
	description='CLI for Nawah--Rapid app development framework',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/nawah-io/nawah_cli',
	project_urls={
		'Docs: Github': 'https://github.com/nawah-io/nawah_docs',
		'GitHub: issues': 'https://github.com/nawah-io/nawah_cli/issues',
		'GitHub: repo': 'https://github.com/nawah-io/nawah_cli',
	},
	classifiers=[
		'Programming Language :: Python :: 3',
		'Programming Language :: Python :: 3.8',
		'Development Status :: 5 - Production/Stable',
		'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
		'Operating System :: OS Independent',
		'Topic :: Internet :: WWW/HTTP',
		'Framework :: AsyncIO',
	],
	python_requires='>=3.8',
	entry_points={
		'console_scripts': {
			'nawah = nawah_cli.__main__:main',
		}
	},
)
