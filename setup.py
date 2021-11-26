from setuptools import setup, find_packages

setup(
    name='webshooter',
    version='0.1.0',
    author='UserExistsError',
    url='https://github.com/UserExistsError/webshooter',
    description='Capture screenshots of web sites',
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'Jinja2>=3,<4',
        'netaddr'
    ],
    package_data={
        'report': ['*.css', '*.js', 'templates/*.html'],
        'js': ['*.js']
    },
    entry_points={
        'console_scripts': [
            'webshooter=cli:run'
        ]
    }
)
