import shutil
import os.path
import subprocess
from setuptools import setup, find_packages


package_data = {
    'report': ['*.css', '*.js', 'templates/*.html'],
    'screen': ['*.js']
}

# skip browser download since it won't be included in our bundle and is instead discarded.
# we could set PUPPETEER_DOWNLOAD_PATH and have capture_service.js look there instead but for now
# the browser will be downloaded on first run.
env = { 'PUPPETEER_SKIP_CHROMIUM_DOWNLOAD': 'true' }

if not shutil.which('npm'):
    from urllib.request import urlopen
    from zipfile import ZipFile
    import platform, tarfile, glob
    print('npm not found. Installing.')
    node_links = {
        'linux-x86_64': 'https://nodejs.org/dist/v16.15.0/node-v16.15.0-linux-x64.tar.xz',
        'windows-x86_64': 'https://nodejs.org/dist/v16.15.0/node-v16.15.0-win-x64.zip',
        'darwin-x86_64': 'https://nodejs.org/dist/v16.15.0/node-v16.15.0-darwin-x64.tar.gz'
    }
    target = platform.system().lower() + '-' + platform.machine()
    if target not in node_links:
        print(f'Unrecognized platform {target}. Install node and npm, then re-run this installer.')
        sys.exit(1)
    url = node_links[target]
    filename = os.path.basename(url)
    bin_dir = None
    extract_dir = None
    node_dir = os.path.join('screen', 'nodejs')
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
    env['PATH'] = os.path.join(os.getcwd(), bin_dir) + sep + os.environ['PATH']
else:
    # NodeJS may already be installed
    env['PATH'] = os.environ['PATH']

try:
    print('Running `npm install`')
    subprocess.run(['npm', 'install'], capture_output=True, check=True, env=env)
    print('Running `npm run build`')
    subprocess.run(['npm', 'run', 'build'], capture_output=True, check=True, env=env)
except subprocess.CalledProcessError as e:
    print(f'Command failed with code {e.returncode}:', e.stderr)
    sys.exit(e.returncode)

# save the NodeJS install and JS bundle
cwd = os.getcwd()
os.chdir('screen')
package_data['screen'].extend(glob.glob('**', recursive=True))
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
    package_data=package_data,
    entry_points={
        'console_scripts': [
            'webshooter=cli:run'
        ]
    }
)
