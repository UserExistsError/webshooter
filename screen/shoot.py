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

import auth.basic
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
        return False
    def base_url(self) -> str:
        return '{}://{}:{}'.format(self.scheme, self.host, self.port)
    def headers(self) -> str:
        return {'token': self.token, 'content-type': 'application/json'}
    def capture(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        body = {
            'url': url,
            'mobile': self.mobile,
            'render_wait_ms': self.render_wait_ms,
            'headers': headers,
            'timeout_ms': self.page_load_timeout_ms
        }
        req = urllib.request.Request(self.base_url() + '/capture', data=json.dumps(body).encode(), headers=self.headers(), method='POST')
        err = None
        try:
            with urllib.request.urlopen(req, timeout=self.service_timeout) as resp:
                if 200 <= resp.status < 300:
                    return json.load(resp)
                err = json.load(resp)['error']
        except urllib.error.HTTPError as e:
            err = json.load(e)['error']
        except Exception as e:
            err = str(e)
        raise CaptureError(err)
    def shutdown(self):
        try:
            req = urllib.request.Request(self.base_url() + '/shutdown', headers=self.headers(), method='POST')
            resp = urllib.request.urlopen(req, timeout=self.service_timeout)
        except:
            logger.error('Failed to gracefully terminate capture service')
        try:
            self.proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            logger.debug('Forcibly terminating the capture service')
            self.proc.terminate()
        os.unlink(self.script)
    def status(self) -> dict[str, Any]:
        req = urllib.request.Request(self.base_url() + '/status', headers=self.headers(), method='POST')
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


def shoot_thread(url: str, capcli: CaptureService, session: WebShooterSession, creds: list[list[str]]):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {'User-Agent': capcli.user_agent}
    if creds is None:
        creds = []

    username, password = None, None
    screen = {'username': None, 'password': None}
    ssl_version_error = False

    for i in range(len(creds)+1):
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=capcli.service_timeout, context=ctx)
        except urllib.error.HTTPError as e:
            logger.error('GET {} - {}'.format(url, str(e)))
            resp = e
        except urllib.error.URLError as e:
            logger.error('GET {} - {}'.format(url, str(e)))
            if 'unsupported protocol' in str(e).lower():
                ssl_version_error = True
                break
            session.update_url(url, Status.INVALID)
            return
        except Exception as e:
            logger.error('GET {} - {}'.format(url, str(e)))
            session.update_url(url, Status.INVALID)
            return

        if resp.getcode() == 401:
            if i == len(creds):
                # no more creds to try
                break
            username, password = None, None
            for h, v in resp.getheaders():
                if h.lower() == 'www-authenticate' and v.lower().startswith('basic '):
                    username, password = creds[i][0], creds[i][1]
                    headers.update(auth.basic.get_headers(username, password))
                    logger.debug('Trying "{}", "{}": {}'.format(username, password, url))
            if username is None:
                # no basic auth header
                break
        elif 'Authorization' in headers:
            logger.debug('Creds valid: "{}", "{}": {}'.format(username, password, url))
            screen['username'] = username
            screen['password'] = password
            break

    # get final url after following redirects
    if ssl_version_error:
        target_url = url
    else:
        target_url = resp.geturl()
        if url.lower() != target_url.lower():
            logger.debug('Redirected: {} -> {}'.format(url, target_url))

    # check if final url was already captured. there is a race condition here with multiple workers
    # but report generation will catch it.
    if session.url_screen_exists(target_url):
        logger.info('Already got a screenshot of {} -> {}'.format(url, target_url))
        session.update_url(url, Status.DUPLICATE)
        return

    # get screenshot
    headers = {}
    if screen['username'] is not None:
        headers = auth.basic.get_headers(screen['username'], screen['password'])

    logger.info('Taking screenshot: '+target_url)
    try:
        page_info = capcli.capture(target_url, headers)
        if len(page_info['image']) == 0:
            raise ValueError('got zero-length image')
        #logger.debug(page_info)
    except CaptureError as e:
        logger.error('Failed to take screenshot for {}: {}'.format(target_url, str(e)))
        session.update_url(url, Status.ERROR)
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
    url_final = page_info.get('url_final', '')
    headers = [(k, page_info['headers'][k]) for k in page_info['headers']]

    logger.debug('[{}] GET {} : title="{}", server="{}"'.format(status, url_final, title, server))

    screen.update({
        'url': url,
        'url_final': url_final,
        'title': title,
        'server': server,
        'status': status,
        'image': os.path.basename(img_file),
        'headers': json.dumps(list(sorted(headers, key=lambda h: h[0]))) # alphabetic sort on header name
    })

    try:
        session.add_screen(screen)
    except Exception as e:
        logger.error('Failed to add screenshot: '+str(e))


def shoot_thread_wrapper(url: str, capcli: CaptureService, session: WebShooterSession, creds: list[list[str]]):
    try:
        shoot_thread(url, capcli, session, creds)
    except Exception as e:
        logger.error('Failed on {}: {}'.format(url, str(e)))
        session.update_url(url, Status.ERROR)

def from_urls(urls: list[str], threads: int, timeout: int, screen_wait_ms: int, node_path: str, session: WebShooterSession, mobile: bool, creds: list[list[str]]=None):
    if len(urls) == 0:
        return
    threads = min(threads, len(urls))

    # start node server for taking capture requests
    capcli = CaptureService(node_path, mobile=mobile, timeout=timeout, render_wait_ms=screen_wait_ms)
    if not capcli.start():
        logger.error('Failed to start capture service')
        return

    work = []
    logger.debug('Scanning with {} worker(s)'.format(threads))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as e:
        work = [e.submit(shoot_thread_wrapper, u, capcli, session, creds) for u in urls]
        logger.debug('Waiting for workers to finish')
        try:
            while len(work):
                _, work = concurrent.futures.wait(work, timeout=1.0)
        except KeyboardInterrupt:
            print('Aborting! Cancelling workers...')
            for w in work:
                w.cancel()

    capcli.shutdown()