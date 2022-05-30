import os
import sys
import json
import time
import math
import shutil
import logging
import tempfile
import subprocess
import urllib.error
import urllib.request
from binascii import hexlify
from typing import Any, TypedDict

from screen.session import Status, WebShooterSession

logger = logging.getLogger(__name__)

class CaptureError(Exception):
    def __init__(self, message):
        if isinstance(message, dict):
            message = message.get('message', str(message))
        super().__init__(message)

class CaptureRequest(TypedDict):
    url: str
    mobile: bool
    render_wait_ms: int
    timeout_ms: int
    headers: dict[str, str]

class CaptureResponse(TypedDict):
    # URL after following redirects
    url_final: str
    # page title
    title: str
    # response headers
    headers: dict[str, str]
    # HTTP response status
    status: int
    # base64 PNG
    image: str
    security: dict[Any, Any]

class CaptureService():
    '''
    Optional `proxy` argument should be scheme://host:port as expected by Chromium's
    --proxy-server option.
    '''
    CAPTURE_SERVICE_FILE=os.path.join(os.path.dirname(__file__), 'capture_service.js')
    PKG_NODE_ROOT_PATH=os.path.join(os.path.dirname(__file__), 'nodejs')
    def __init__(self, node_path: str, proxy: str=None, headless: bool=True):
        if not node_path:
            if os.path.isdir(self.PKG_NODE_ROOT_PATH):
                windows_path = os.path.join(self.PKG_NODE_ROOT_PATH, 'node')
                nix_path = os.path.join(self.PKG_NODE_ROOT_PATH, 'bin/node')
                if os.path.exists(windows_path):
                    node_path = windows_path
                elif os.path.exists(nix_path):
                    node_path = nix_path
        if not node_path:
            node_path = 'node'
        node_path = shutil.which(node_path)
        if not node_path:
            raise RuntimeError('Failed to find node executable')
        logger.debug('Using `node` path %s', node_path)
        self.node_path = node_path
        self.proc = None
        self.host = '127.0.0.1'
        self.port = 3000
        self.endpoint = f'http://{self.host}:{self.port}'
        self.token = hexlify(os.urandom(16)).decode('ascii')
        self.client = CaptureClient(self.token, self.endpoint)
        self.proxy = proxy
        self.headless = headless
        self.temp_dir = None
    def __enter__(self) -> 'CaptureClient':
        self.temp_dir = tempfile.TemporaryDirectory(prefix='webshooter-')
        logger.debug('using temp dir %s', self.temp_dir.name)
        self.start()
        return self.client
    def __exit__(self, type, value, traceback):
        self.shutdown()
        if self.temp_dir:
            try:
                self.temp_dir.cleanup()
            except Error as err:
                logger.error('Failed to cleanup temp dir: %s', str(err))
    def start(self):
        env = {
            # This sets the Chromium user data directory
            # see https://chromium.googlesource.com/chromium/src/+/HEAD/docs/user_data_dir.md
            'WEBSHOOTER_TEMP': self.temp_dir.name,
            'WEBSHOOTER_PORT': str(self.port),
            'WEBSHOOTER_TOKEN': self.token
        }
        if self.proxy:
            env['WEBSHOOTER_PROXY'] = self.proxy
        if not self.headless:
            # on linux you can set DISPLAY and run the browser with headless=false to see everything
            if 'DISPLAY' not in os.environ:
                logger.error('cannot display browser: no DISPLAY env var')
            else:
                env['DISPLAY'] = os.environ['DISPLAY']

        cmd = [self.node_path, self.CAPTURE_SERVICE_FILE]
        logger.debug('launching capture service: %s', cmd)
        try:
            self.proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=subprocess.STDOUT, env=env)
        except Exception as e:
            logger.error('Failed to call node: '+str(e))
            raise e

        logger.info('Warming up the headless browser...')
        attempts_left = 10
        while attempts_left > 0:
            try:
                self.client.status()
                return True
            except Exception as e:
                attempts_left -= 1
                if 'connection refused' not in str(e).lower():
                    logger.error('Failed to check status of capture service: '+str(e))
            time.sleep(1)
        self.shutdown()
        raise CaptureError('Failed to start capture service')
    def shutdown(self):
        if not self.proc:
            return
        self.client.shutdown()
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            logger.debug('Forcibly terminating the capture service')
            self.proc.terminate()
        self.proc = None

class CaptureClient():
    DEFAULT_RENDER_WAIT_MS = 3000
    DEFAULT_PAGE_LOAD_TIMEOUT_MS = 10000
    GRACE_PERIOD_TIMEOUT_MS = 5000
    def __init__(self, token: str, endpoint: str):
        self.endpoint = endpoint
        self.token = token
        # defaults
        self.render_wait_ms = self.DEFAULT_RENDER_WAIT_MS
        self.mobile = False
        # how long headless browser should wait for page load
        self.page_load_timeout_ms = self.DEFAULT_PAGE_LOAD_TIMEOUT_MS
    def configure(self, mobile: bool, render_wait_ms: int, page_load_timeout_ms: int):
        self.mobile = mobile
        self.render_wait_ms = render_wait_ms
        self.page_load_timeout_ms = page_load_timeout_ms
    def _service_timeout(self) -> int:
        ''' how long to wait for capture service to respond. should always be greater than
            combined page load and render wait times
        '''
        return math.ceil( (self.page_load_timeout_ms + self.render_wait_ms + self.GRACE_PERIOD_TIMEOUT_MS) / 1000 )
    def _headers(self) -> str:
        return {'token': self.token, 'content-type': 'application/json'}
    def capture(self, url: str, headers: dict[str, str]) -> CaptureResponse:
        body: CaptureRequest = {
            'url': url,
            'mobile': self.mobile,
            'render_wait_ms': self.render_wait_ms,
            'headers': headers,
            'timeout_ms': self.page_load_timeout_ms
        }
        req = urllib.request.Request(self.endpoint + '/capture', data=json.dumps(body).encode(), headers=self._headers(), method='POST')
        err = None
        try:
            with urllib.request.urlopen(req, timeout=self._service_timeout()) as resp:
                if 200 <= resp.status < 300:
                    page_info: CaptureResponse = json.load(resp)
                    if len(page_info['image']) == 0:
                        err = 'got zero-length image'
                    else:
                        return page_info
                else:
                    err = json.load(resp)['error']
        except urllib.error.HTTPError as e:
            err = json.load(e)['error']
        except Exception as e:
            err = str(e)
        raise CaptureError(err)
    def shutdown(self):
        try:
            req = urllib.request.Request(self.endpoint + '/shutdown', headers=self._headers(), method='POST')
            urllib.request.urlopen(req, timeout=self._service_timeout())
        except:
            logger.error('Failed to gracefully terminate capture service')
    def status(self) -> dict[str, Any]:
        req = urllib.request.Request(self.endpoint + '/status', headers=self._headers(), method='POST')
        try:
            return json.load(urllib.request.urlopen(req, timeout=self._service_timeout()))
        except urllib.error.HTTPError as e:
            err = json.load(e)['error']
        raise CaptureError(err)
