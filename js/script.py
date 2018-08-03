import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

# javascript to pass to node and take a screen shot
JS_TEMPLATE_FILE='js/screen.js'
URL_PLACEHOLDER='::URL::'
IMAGE_PLACEHOLDER='::IMAGE::'
TIMEOUT_PLACEHOLDER='::TIMEOUT::'

def build(url, timeout=5000):
    js_tmp = tempfile.mkstemp(prefix='script.', suffix='.js', dir='.')[-1]
    img_tmp = tempfile.mkstemp(prefix='screen.', suffix='.png', dir='.')[-1]
    script = open(JS_TEMPLATE_FILE).read()
    script = script.replace(URL_PLACEHOLDER, url)
    script = script.replace(IMAGE_PLACEHOLDER, img_tmp)
    script = script.replace(TIMEOUT_PLACEHOLDER, str(timeout))
    open(js_tmp, 'wb').write(script.encode())
    return js_tmp, img_tmp

def run(script_path, node_path='node'):
    cmd = [node_path, script_path]
    logger.debug('Running script: {}'.format(' '.join(cmd)))
    try:
        subprocess.check_call(cmd)
    except:
        return False
    return True
