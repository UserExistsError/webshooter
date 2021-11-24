import ssl
import base64
import logging
import urllib.request

logger = logging.getLogger(__name__)

def get_headers(username: str, password: str) -> dict[str, str]:
    return {'Authorization':'Basic '+base64.b64encode((username+':'+password).encode()).decode()}

def login(url: str, username: str, password: str, timeout: int) -> bool:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=get_headers(username, password))
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
    except urllib.error.HTTPError as e:
        logger.error('Error GET {}: {}'.format(url, str(e)))
        resp = e
    except Exception as e:
        logger.error('Unknown auth error on {}: {}'.format(url, str(e)))
        return False
    logger.debug('[{}] GET {}'.format(resp.getcode(), url))
    return resp.getcode() == 200


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--username', default='')
    parser.add_argument('-p', '--password', default='')
    parser.add_argument('-t', '--timeout', type=int, default=3, help='socket timeout. default 3s')
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output')
    parser.add_argument('urls', nargs='*', help='urls to test')
    args = parser.parse_args()

    if args.debug:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter('[%(levelname)s] %(filename)s:%(lineno)s %(message)s'))
        l = logging.getLogger(__name__)
        l.setLevel(logging.DEBUG)
        l.addHandler(h)

    for u in args.urls:
        print(u, login(u, args.username, args.password, args.timeout))
