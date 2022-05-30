import shutil
import os.path
import subprocess
from setuptools import setup, find_packages
from setuptools.command.install import install as default_install


class Install(default_install):
    ''' Overrides the default install command to ensure NodeJS dependencies are installed '''
    description = 'Install Webshooter and dependencies'
    def run(self):
        install_node()
        default_install.run(self)

def install_node():
    def get_download_url(NODE_VERSION='v16.15.0'):
        node_links = {
            'linux-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-x64.tar.xz',
            'windows-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-win-x64.zip',
            'darwin-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-x64.tar.gz',
            'darwin-arm64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-arm64.tar.gz'
        }
        target = platform.system().lower() + '-' + platform.machine()
        if target not in node_links:
            raise RuntimeError(f'Unrecognized platform {target}. Install node and npm, then re-run this installer.')
        return node_links[target]
    npm_env = {}
    if not shutil.which('npm'):
        from urllib.request import urlopen
        from zipfile import ZipFile
        import platform, tarfile
        print('npm not found. Installing.')
        url = get_download_url()
        filename = os.path.basename(url)
        bin_dir = None
        extract_dir = None
        node_dir = os.path.join('screen', 'nodejs')
        if os.path.exists(node_dir):
            raise FileExistsError(f'Did not expect to find directory: {node_dir}')
        print('Downloading from', url)
        with urlopen(url) as response:
            with open(filename, 'wb') as dest:
                shutil.copyfileobj(response, dest)
        print(f'Downloaded to {filename}. Extracting.')
        if filename.endswith('.tar.xz') or filename.endswith('.tar.gz'):
            with tarfile.open(filename) as tar:
                tar.extractall()
                extract_dir = tar.getnames()[0]
            bin_dir = os.path.join(node_dir, 'bin')
        elif filename.endswith('.zip'):
            with ZipFile(filename, 'r') as zipf:
                zipf.extractall()
                extract_dir = zipf.namelist()[0]
            bin_dir = node_dir
        shutil.move(extract_dir, node_dir)
        sep = ';' if platform.system().lower() == 'windows' else ':'
        npm_env['PATH'] = os.path.abspath(bin_dir) + sep + os.environ['PATH']
    else:
        # NodeJS may already be installed
        npm_env['PATH'] = os.environ['PATH']

    cwd = os.getcwd()
    os.chdir('screen')
    print('Running `npm install`')
    result = subprocess.run(['npm', 'install'], capture_output=True, check=True, env=npm_env)
    print(result.stdout.decode())
    os.chdir(cwd)

setup(
    name='webshooter',
    version='0.1.0',
    author='UserExistsError',
    url='https://github.com/UserExistsError/webshooter',
    description='Capture screenshots of web sites',
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'Jinja2>=2,<4'
    ],
    # include files under version control. files generated during install must be added to MANIFEST.in
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'webshooter=cli:run'
        ]
    },
    cmdclass={
        'install': Install
    }
)
