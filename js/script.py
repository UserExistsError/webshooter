import os
import sys
import jinja2
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

# javascript to pass to node and take a screen shot
CAPTURE_SERVICE_FILE=os.path.join(os.path.dirname(__file__), 'screen.js')

def run_background(node_path: str='node', env: dict={}) -> subprocess.Popen:
    cmd = [node_path, CAPTURE_SERVICE_FILE]
    try:
        return subprocess.Popen(cmd, stdout=sys.stdout, stderr=subprocess.STDOUT, env=env)
    except Exception as e:
        logger.error('Failed to call node: '+str(e))
    return None