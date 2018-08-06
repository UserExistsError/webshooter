#!/usr/bin/env python3
import argparse
import logging

import targets.nmap
import report.generate
import screen.shoot
import screen.session
from report.template import Template

logger = logging.getLogger(__name__)

DEFAULT_HTTP_PORTS = [80, 8080]
DEFAULT_HTTPS_PORTS = [443, 8443]

def split_ports(ports):
    return list(map(int, ports.split(',')))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output')
    parser.add_argument('-x', '--nmap-xml', dest='nmap_xml', help='nmap xml')
    parser.add_argument('-u', '--url-file', dest='url_file', help='urls 1 per line. include scheme')
    parser.add_argument('-n', '--node-path', dest='node_path', default='node', help='nodejs path')
    parser.add_argument('-t', '--timeout', default=5000, type=int, help='timeout in millisec')
    parser.add_argument('-w', '--threads', default=10, type=int, help='worker thread count')
    parser.add_argument('-p', '--page-size', dest='page_size', default=40, type=int, help='results per page')
    parser.add_argument('-s', '--session', required=True, help='save progress')
    parser.add_argument('-r', '--retry', action='store_true', help='retry failed urls')
    parser.add_argument('--ports-http', dest='ports_http', default=DEFAULT_HTTP_PORTS,
                        type=split_ports, help='comma-separated')
    parser.add_argument('--ports-https', dest='ports_https', default=DEFAULT_HTTPS_PORTS,
                        type=split_ports, help='comma-separated')
    parser.add_argument('--tiles', action='store_true', help='Generate report with tiles')
    parser.add_argument('--mobile', action='store_true', help='Emulate mobile device')
    parser.add_argument('urls', default=[], nargs='*', help='urls including scheme')
    args = parser.parse_args()

    if args.debug:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter('[%(levelname)s] %(filename)s:%(lineno)s %(message)s'))
        for n in [__name__, 'js', 'targets', 'report', 'screen']:
            l = logging.getLogger(n)
            l.setLevel(logging.DEBUG)
            l.addHandler(h)

    # get urls to screenshot
    urls_raw = set(args.urls)
    if args.url_file:
        urls_raw.update([u.strip() for u in open(args.url_file)])
    if args.nmap_xml:
        urls_raw.update(targets.nmap.from_xml(args.nmap_xml, args.ports_http, args.ports_https))
    urls = set()
    for u in urls_raw:
        if u.startswith('http'):
            urls.add(u)
        else:
            urls.add('http://'+u)
            urls.add('https://'+u)

    # shoot the pages and generate html report
    session = screen.session.WebShooterSession(args.session, urls)
    urls = session.get_queued_urls()
    if args.retry:
        urls.extend(session.get_failed_urls())

    print('shooting {} url(s)'.format(len(urls)))
    screen.shoot.from_urls(urls, args.threads, args.timeout, args.node_path, session, args.mobile)
    template = Template.Tiles if args.tiles else Template.Lines
    report.generate.from_session(session, template, args.page_size)
