import os
import sys
import json
import jinja2
import logging
import tempfile
import subprocess
import urllib.parse

logger = logging.getLogger(__name__)

# javascript to pass to node and take a screen shot
JS_TEMPLATE_FILE=os.path.join(os.path.dirname(__file__), 'screen.js')

def filename_from_url(url):
    u = urllib.parse.urlparse(url)
    host = u.netloc
    if ':' in host:
        host, port = host.split(':')
    else:
        if u.scheme.lower() == 'http':
            port = 80
        else:
            port = 443
    return '{}-{}-{}'.format(u.scheme, host, port).replace('/', '').replace('\\', '')

def build(url, timeout=5000, mobile=False, headers={}, screen_wait_ms=2000):
    js_h, js_tmp = tempfile.mkstemp(prefix='script.', suffix='.js', dir='.')
    os.close(js_h)

    img_h, img_tmp = tempfile.mkstemp(prefix=filename_from_url(url)+'.', suffix='.png', dir='.')
    os.close(img_h)

    inf_h, inf_tmp = tempfile.mkstemp(prefix='info.', suffix='.json', dir='.')
    os.close(inf_h)

    script = jinja2.Template(open(JS_TEMPLATE_FILE, 'rb').read().decode())
    rendered = script.render(
        url=url,
        image=img_tmp.replace('\\', '\\\\'),
        timeout=timeout,
        mobile=str(mobile).lower(),
        screen_wait=screen_wait_ms,
        headers=json.dumps(headers),
        page_info_file=inf_tmp.replace('\\', '\\\\'))
    open(js_tmp, 'wb').write(rendered.encode())
    return js_tmp, img_tmp, inf_tmp

def run(script_path, node_path='node'):
    cmd = [node_path, script_path]
    try:
        subprocess.check_call(cmd, timeout=60)
    except Exception as e:
        logger.error('Failed to call node: '+str(e))
        return False
    return True
