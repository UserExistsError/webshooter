import logging
import urllib.parse
from collections.abc import Collection

logger = logging.getLogger(__name__)

def process_urls(urls_raw: Collection[str]) -> set[str]:
    '''
    Make sure every URL has a valid scheme. Drop any URLs that cannot be made valid.
    '''
    urls = set()
    for u in urls_raw:
        r = urllib.parse.urlparse(u)
        if not r.scheme:
            if not urllib.parse.urlparse('https://'+u).netloc:
                logger.error('invalid URL host: %s', u)
            else:
                urls.add('http://'+u)
                urls.add('https://'+u)
        elif not r.netloc:
            logger.error('invalid URL host: %s', u)
        elif r.scheme not in {'http', 'https'}:
            logger.error('invalid URL scheme: %s', u)
        else:
            urls.add(u)
    return urls

def from_file(text_file: str) -> set[str]:
    urls = set()
    with open(text_file) as fp:
        for u in fp:
            urls.add(u.strip())
    return process_urls(urls)

def from_collection(urls_raw: Collection[str]) -> set[str]:
    urls = set()
    for u in urls_raw:
        urls.add(u.strip())
    return process_urls(urls)