import os
import json
import base64
import logging
import tempfile
import urllib.parse
import concurrent.futures

from webshooter.screen.session import Status, WebShooterSession
from webshooter.screen.capture import CaptureClient, CaptureError

logger = logging.getLogger(__package__)

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

def shoot_thread(url: str, client: CaptureClient, session: WebShooterSession):
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
        page_info = client.capture(url, headers)
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


def shoot_thread_wrapper(url: str, client: CaptureClient, session: WebShooterSession):
    try:
        shoot_thread(url, client, session)
    except Exception as e:
        logger.error('Failed on {}: {}'.format(url, str(e)))
        session.update_url(url, Status.ERROR)

def capture_from_urls(urls: list[str], threads: int, session: WebShooterSession, client: CaptureClient):
    if len(urls) == 0:
        return
    threads = min(threads, len(urls))

    work = []
    logger.debug('Scanning with {} worker(s)'.format(threads))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as e:
        work = [e.submit(shoot_thread_wrapper, u, client, session) for u in urls]
        logger.debug('Waiting for workers to finish')
        try:
            while len(work):
                _, work = concurrent.futures.wait(work, timeout=1.0)
        except KeyboardInterrupt:
            print('Aborting! Cancelling workers...')
            for w in work:
                w.cancel()
