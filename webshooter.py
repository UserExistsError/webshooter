#!/usr/bin/env python3
import argparse
import logging

import urls.nmap
import report.generate
import screen.shoot
import screen.session

logger = logging.getLogger(__name__)

DEFAULT_HTTP_PORTS = [80, 8080]
DEFAULT_HTTPS_PORTS = [443, 8443]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output')
    parser.add_argument('-x', '--nmap-xml', dest='nmap_xml', help='nmap xml')
    parser.add_argument('-u', '--url-file', dest='url_file', help='urls 1 per line. include scheme')
    parser.add_argument('urls', default=[], nargs='*', help='urls including scheme')
    parser.add_argument('-n', '--node-path', dest='node_path', default='node', help='nodejs path')
    parser.add_argument('-t', '--timeout', default=5000, type=int, help='timeout in millisec')
    parser.add_argument('-w', '--threads', default=10, type=int, help='worker thread count')
    parser.add_argument('-p', '--page-size', dest='page_size', default=40, type=int, help='results per page')
    parser.add_argument('-s', '--session', required=True, help='save progress')
    parser.add_argument('--http-ports', dest='http_ports', default=','.join(map(str, DEFAULT_HTTP_PORTS)),
                                                                            help='comma-separated')
    parser.add_argument('--https-ports', dest='https_ports', default=','.join(map(str, DEFAULT_HTTPS_PORTS)),
                                                                            help='comma-separated')
    args = parser.parse_args()

    if args.debug:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter('[%(levelname)s] %(filename)s:%(lineno)s %(message)s'))
        for n in [__name__, 'js', 'urls', 'report', 'screen']:
            l = logging.getLogger(n)
            l.setLevel(logging.DEBUG)
            l.addHandler(h)

    # get urls to screenshot
    urls = set(args.urls)
    if args.url_file:
        s.update([u.strip() for u in open(args.url_file)])
    if args.nmap_xml:
        s.update(urls.nmap.from_xml(args.nmap_xml, args.http_ports, args.https_ports))

    # shoot the pages and generate html report
    session = screen.session.WebShooterSession(args.session, urls)
    urls = session.get_queued_urls()
    print('shooting {} url(s)'.format(len(urls)))
    if screen.shoot.from_urls(urls, args.threads, args.timeout, args.node_path, session):
        report.generate.from_session(session, args.page_size)
