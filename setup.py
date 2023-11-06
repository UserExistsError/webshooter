import shutil
import os.path
import subprocess
from setuptools import setup
from setuptools.command.install import install as default_install


class Install(default_install):
    ''' Overrides the default install command to ensure NodeJS dependencies are installed '''
    description = 'Install Webshooter and dependencies'
    def run(self):
        install_node()
        default_install.run(self)

def install_node():
    def get_download_url(NODE_VERSION='v20.9.0'):
        node_links = {
            'linux-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-linux-x64.tar.xz',
            'windows-amd64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-win-x64.zip',
            'darwin-x86_64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-x64.tar.gz',
            'darwin-arm64': f'https://nodejs.org/dist/{NODE_VERSION}/node-{NODE_VERSION}-darwin-arm64.tar.gz'
        }
        target = (platform.system() + '-' + platform.machine()).lower()
        if target not in node_links:
            raise RuntimeError(f'Unrecognized platform {target}. Install node and npm, then re-run this installer.')
        return node_links[target]
    npm_env = dict(os.environ)
    if not shutil.which('npm', path=npm_env['PATH']):
        from urllib.request import urlopen
        from zipfile import ZipFile
        import platform, tarfile
        print('npm not found. Installing.')
        url = get_download_url()
        filename = os.path.basename(url)
        bin_dir = None
        extract_dir = None
        node_dir = os.path.join('webshooter', 'screen', 'nodejs')
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

    cwd = os.getcwd()
    os.chdir(os.path.join('webshooter', 'screen'))
    print('Running `npm install`')
    # see https://docs.python.org/3/library/subprocess.html#subprocess.Popen
    npm_path = shutil.which('npm', path=npm_env['PATH'])
    try:
        result = subprocess.run([npm_path, 'install'], capture_output=True, check=True, env=npm_env)
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print('Error `npm install`:', e.stderr)
        raise e
    os.chdir(cwd)

setup(
    cmdclass={
        'install': Install
    }
)
