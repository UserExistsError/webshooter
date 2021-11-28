import os
import json
import time
import math
import base64
import logging
import subprocess
import urllib.error
import urllib.request
from binascii import hexlify
from typing import Any, TypedDict

import js.script
from screen.session import Status, WebShooterSession

logger = logging.getLogger(__name__)

class CaptureError(Exception):
    def __init__(self, message):
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
    def __init__(self, node_path: str):
        self.node_path = node_path
        self.proc = None
        self.script = None
        self.host = '127.0.0.1'
        self.port = 3000
        self.endpoint = f'http://{self.host}:{self.port}'
        self.token = hexlify(os.urandom(16)).decode('ascii')
        self.client = CaptureClient(self.token, self.endpoint)
    def __enter__(self) -> 'CaptureClient':
        self.start()
        return self.client
    def __exit__(self, type, value, traceback):
        self.shutdown()
    def start(self):
        self.script = js.script.build(self.token, self.port)
        self.proc = js.script.run_background(self.script, self.node_path)
        logger.info('Warming up the headless browser...')
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                self.client.status()
                return True
            except Exception as e:
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
        try:
            os.unlink(self.script)
        except FileNotFoundError:
            pass

class CaptureClient():
    DEFAULT_RENDER_WAIT_MS = 3000
    DEFAULT_PAGE_LOAD_TIMEOUT_MS = 10000
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
        return math.ceil( (self.page_load_timeout_ms + self.render_wait_ms) / 1000 )
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
                    err = str(json.load(resp)['error'])
        except urllib.error.HTTPError as e:
            err = str(json.load(e)['error'])
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
        return json.load(urllib.request.urlopen(req, timeout=self._service_timeout()))
