import os
import re
import ssl
import json
import logging
import urllib.error
import urllib.request
import concurrent.futures

import js.script
from screen.session import Status

logger = logging.getLogger(__name__)

# puppeteers version of chrome uses this User-Agent
USER_AGENT='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/69.0.3494.0 Safari/537.36'
title_regex = re.compile(b'<title>\s*(.*?)\s*</title>', re.IGNORECASE)

def http_get(url, timeout):
    ''' return response body, headers, and status code '''
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    logger.debug('GET '+url)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)

def shoot_thread(url, timeout, node_path, session):
    # get http response object
    try:
        resp = http_get(url, timeout)
    except urllib.error.HTTPError as e:
        logger.error('Error GET {}: {}'.format(url, str(e)))
        resp = e
    except urllib.error.URLError as e:
        logger.error('Error GET {}: {}'.format(url, str(e)))
        session.update_url(url, Status.INVALID)
        return
    except Exception as e:
        logger.error('Error GET {}: {}'.format(url, str(e)))
        session.update_url(url, Status.INVALID)
        return
    title = ''
    m = title_regex.search(resp.read())
    if m:
        title = m.group(1).decode()
    server = ''
    for h, v in resp.getheaders():
        if h.lower() == 'server':
            server = v
            break
    logger.debug('[{}] GET {} : title="{}", server="{}"'.format(resp.getcode(), resp.geturl(), title, server))

    # get screenshot
    js_file, img_file = js.script.build(url, timeout)
    logger.debug('Taking screenshot: '+url)
    js.script.run(js_file, node_path)
    os.unlink(js_file)
    if not os.path.exists(img_file):
        logger.error('Screenshot failed: '+url)
        session.update_url(url, Status.ERROR)
        return
    if os.path.getsize(img_file) == 0:
        logger.error('Screenshot failed: '+url)
        os.unlink(img_file)
        session.update_url(url, Status.ERROR)
        return

    screen = {
        'url': url,
        'url_final': resp.geturl(),
        'title': title,
        'server': server,
        'status': resp.getcode(),
        'image': img_file,
        'headers': json.dumps(resp.getheaders())
    }
    try:
        session.add_screen(screen)
    except Exception as e:
        logger.error('Failed to add screenshot: '+str(e))

def from_urls(urls, threads, timeout, node_path, session):
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as e:
        concurrent.futures.wait([e.submit(shoot_thread, u, timeout, node_path, session) for u in urls])
    return True
