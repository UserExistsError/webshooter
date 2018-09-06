import os
import sys
import json
import jinja2
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

# javascript to pass to node and take a screen shot
JS_TEMPLATE_FILE=os.path.join(os.path.dirname(__file__), 'screen.js')

def build(url, timeout=5000, mobile=False, headers={}):
    js_h, js_tmp = tempfile.mkstemp(prefix='script.', suffix='.js', dir='.')
    os.close(js_h)
    img_h, img_tmp = tempfile.mkstemp(prefix='screen.', suffix='.png', dir='.')
    os.close(img_h)
    script = jinja2.Template(open(JS_TEMPLATE_FILE, 'rb').read().decode())
    rendered = script.render(url=url, image=img_tmp, timeout=timeout, mobile=str(mobile).lower(),
                             headers=json.dumps(headers))
    open(js_tmp, 'wb').write(rendered.encode())
    return js_tmp, img_tmp

def run(script_path, node_path='node'):
    cmd = [node_path, script_path]
    logger.debug('Running script: {}'.format(' '.join(cmd)))
    try:
        subprocess.check_call(cmd)
    except:
        return False
    return True
