import os
import ssl
import json
import time
import math
import base64
import logging
import tempfile
import subprocess
import urllib.error
import urllib.request
import concurrent.futures
from binascii import hexlify
from typing import Any

import js.script
from screen.session import Status, WebShooterSession

logger = logging.getLogger(__name__)

class CaptureError(Exception):
    def __init__(self, message):
        super().__init__(message)

class CaptureService():
    DEFAULT_RENDER_WAIT_MS = 3000
    DEFAULT_TIMEOUT = 5
    def __init__(self, node_path: str, mobile: bool=False, timeout: int=DEFAULT_TIMEOUT, render_wait_ms: int=DEFAULT_RENDER_WAIT_MS):
        self.host = '127.0.0.1'
        self.port = 3000
        self.scheme = 'http'
        self.token = hexlify(os.urandom(16)).decode('ascii')
        # how long headless browser should wait for page load
        self.page_load_timeout_ms = timeout * 1000
        # how long to wait for capture service to respond. should always be greater than combined page load and render wait times
        self.service_timeout = math.ceil( (self.page_load_timeout_ms + render_wait_ms) / 1000 )
        self.node_path = node_path
        self.render_wait_ms = render_wait_ms
        self.mobile = mobile
        self.user_agent = ''
        self.proc = None
        self.script = None
    def __enter__(self) -> 'CaptureService':
        self.start()
        return self
    def __exit__(self, type, value, traceback):
        self.shutdown()
    def start(self) -> bool:
        self.script = js.script.build(self.token, self.port)
        self.proc = js.script.run_background(self.script, self.node_path)
        logger.info('Warming up the headless browser...')
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                res = self.status()
                self.user_agent = res['userAgentMobile'] if self.mobile else res['userAgent']
                logger.debug('Updated User-Agent: '+self.user_agent)
                return True
            except Exception as e:
                if 'connection refused' not in str(e).lower():
                    logger.error('Failed to check status of capture service: '+str(e))
                time.sleep(1)
        self.shutdown()
        return False
    def _base_url(self) -> str:
        return '{}://{}:{}'.format(self.scheme, self.host, self.port)
    def _headers(self) -> str:
        return {'token': self.token, 'content-type': 'application/json'}
    def capture(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        body = {
            'url': url,
            'mobile': self.mobile,
            'render_wait_ms': self.render_wait_ms,
            'headers': headers,
            'timeout_ms': self.page_load_timeout_ms
        }
        req = urllib.request.Request(self._base_url() + '/capture', data=json.dumps(body).encode(), headers=self._headers(), method='POST')
        err = None
        try:
            with urllib.request.urlopen(req, timeout=self.service_timeout) as resp:
                if 200 <= resp.status < 300:
                    page_info = json.load(resp)
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
        if not self.proc:
            return
        try:
            req = urllib.request.Request(self._base_url() + '/shutdown', headers=self._headers(), method='POST')
            resp = urllib.request.urlopen(req, timeout=self.service_timeout)
        except:
            logger.error('Failed to gracefully terminate capture service')
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
    def status(self) -> dict[str, Any]:
        req = urllib.request.Request(self._base_url() + '/status', headers=self._headers(), method='POST')
        return json.load(urllib.request.urlopen(req, timeout=self.service_timeout))

def image_name_from_url(url: str) -> str:
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


def shoot_thread(url: str, capsvc: CaptureService, session: WebShooterSession):
    # Handle case where a URL was already captured. We dedupe URLs before attempting screenshots but
    # another URL that was captured in this run may have redirected to this URL.
    if session.url_screen_exists(url):
        logger.info('Already got a screenshot of {}'.format(url))
        session.update_url(url, Status.DUPLICATE)
        return

    # get screenshot
    headers = {}

    logger.info('Taking screenshot: '+url)
    try:
        page_info = capsvc.capture(url, headers)
    except CaptureError as e:
        logger.error('Failed to take screenshot for {}: {}'.format(url, str(e)))
        session.update_url(url, Status.ERROR)
        return

    url_final = page_info['url_final']
    if url != url_final:
        logger.debug('Redirected: {} -> {}'.format(url, url_final))
    if session.url_screen_exists(url_final):
        logger.info('Already got a screenshot of {}'.format(url_final))
        session.update_url(url, Status.DUPLICATE)
        return

    try:
        with tempfile.NamedTemporaryFile(prefix=image_name_from_url(url)+'.', suffix='.png', dir='.', delete=False) as fp:
            img_file = fp.name
            fp.write(base64.b64decode(page_info['image']))
    except Exception as e:
        logger.error('Failed to save screenshot: '+str(e))
        session.update_url(url, Status.ERROR)
        return

    title = page_info.get('title', '')
    server = page_info['headers'].get('server', '')
    status = page_info.get('status', -1)
    headers = [(k, page_info['headers'][k]) for k in page_info['headers']]

    logger.debug('[{}] GET {} : title="{}", server="{}"'.format(status, url_final, title, server))

    screen = {
        'url': url,
        'url_final': url_final,
        'title': title,
        'server': server,
        'status': status,
        'image': os.path.basename(img_file),
        'headers': json.dumps(list(sorted(headers, key=lambda h: h[0]))) # alphabetic sort on header name
    }

    try:
        session.add_screen(screen)
    except Exception as e:
        logger.error('Failed to add screenshot: '+str(e))


def shoot_thread_wrapper(url: str, capsvc: CaptureService, session: WebShooterSession):
    try:
        shoot_thread(url, capsvc, session)
    except Exception as e:
        logger.error('Failed on {}: {}'.format(url, str(e)))
        session.update_url(url, Status.ERROR)

def capture_from_urls(urls: list[str], threads: int, session: WebShooterSession, capsvc: CaptureService):
    if len(urls) == 0:
        return
    threads = min(threads, len(urls))

    work = []
    logger.debug('Scanning with {} worker(s)'.format(threads))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as e:
        work = [e.submit(shoot_thread_wrapper, u, capsvc, session) for u in urls]
        logger.debug('Waiting for workers to finish')
        try:
            while len(work):
                _, work = concurrent.futures.wait(work, timeout=1.0)
        except KeyboardInterrupt:
            print('Aborting! Cancelling workers...')
            for w in work:
                w.cancel()
