import os
import sys
import jinja2
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

# javascript to pass to node and take a screen shot
JS_TEMPLATE_FILE=os.path.join(os.path.dirname(__file__), 'screen.js')


def build(token: str, port: int) -> str:
    js_h, js_tmp = tempfile.mkstemp(prefix='script.', suffix='.js', dir='.')
    os.close(js_h)

    script = jinja2.Template(open(JS_TEMPLATE_FILE, 'rb').read().decode())
    rendered = script.render(token=token, port=port)
    open(js_tmp, 'wb').write(rendered.encode())
    return js_tmp


def run_background(script_path: str, node_path: str='node') -> subprocess.Popen:
    cmd = [node_path, script_path]
    try:
        return subprocess.Popen(cmd, stdout=sys.stdout, stderr=subprocess.STDOUT)
    except Exception as e:
        logger.error('Failed to call node: '+str(e))
    return None