import os
import re
import ssl
import json
import logging
import http.client
import urllib.error
import urllib.request
import concurrent.futures

import auth.basic
import js.script
from screen.session import Status

logger = logging.getLogger(__name__)

# puppeteers version of chrome uses this User-Agent
USER_AGENT='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/69.0.3494.0 Safari/537.36'
USER_AGENT_MOBILE='Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1'

def http_get(url, timeout, user_agent):
    ''' return response body, headers, and status code '''
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    logger.debug('GET '+url)
    req = urllib.request.Request(url, headers={'User-Agent': user_agent})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)

def shoot_thread(url, timeout, screen_wait_ms, node_path, session, mobile, creds):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    user_agent = USER_AGENT_MOBILE if mobile else USER_AGENT
    headers = {'User-Agent': user_agent}
    if not creds:
        creds = [(None, None)]

    username, password = None, None
    screen = {'username': None, 'password': None}
    ssl_version_error = False

    for i in range(len(creds)+1):
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
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
    js_file, img_file, inf_file = js.script.build(target_url, timeout * 1000, mobile, headers)
    logger.info('Taking screenshot: '+target_url)
    js.script.run(js_file, node_path)
    os.unlink(js_file)

    if os.path.exists(inf_file):
        j = open(inf_file).read()
        os.unlink(inf_file)

    if not os.path.exists(img_file):
        logger.error('Screenshot failed: {}'.format(target_url or 'error'))
        session.update_url(url, Status.ERROR)
        return
    if os.path.getsize(img_file) == 0:
        logger.error('Screenshot failed: {}'.format(target_url or 'error'))
        os.unlink(img_file)
        session.update_url(url, Status.ERROR)
        return

    page_info = json.loads(j)

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


def shoot_thread_wrapper(url, timeout, screen_wait_ms, node_path, session, mobile, creds):
    try:
        shoot_thread(url, timeout, screen_wait_ms, node_path, session, mobile, creds)
    except Exception as e:
        logger.error('Failed on {}: {}'.format(url, str(e)))
        session.update_url(url, Status.ERROR)

def from_urls(urls, threads, timeout, screen_wait_ms, node_path, session, mobile, creds=None):
    if len(urls) == 0:
        return
    work = []
    logger.debug('Scanning with {} worker(s)'.format(threads))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as e:
        work = [e.submit(shoot_thread_wrapper, u, timeout, screen_wait_ms, node_path, session, mobile, creds) for u in urls]
        logger.debug('Waiting for workers to finish')
        try:
            while len(work):
                _, work = concurrent.futures.wait(work, timeout=1.0)
        except KeyboardInterrupt:
            print('Aborting! Cancelling workers...')
            for w in work:
                w.cancel()
