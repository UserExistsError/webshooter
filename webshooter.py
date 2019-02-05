#!/usr/bin/env python3
import json
import logging
import netaddr
import argparse

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

def expand_cidr(cidr):
    n = netaddr.IPNetwork(cidr)
    return [str(a) for a in n.iter_hosts()]

def process_url(url):
    if url.startswith('http'):
        return [url]
    try:
        return expand_cidr(url)
    except:
        pass
    # probably a url w/o scheme
    return [url]

def handle_scan(args):
    # get urls to screenshot
    if args.all_open:
        args.ports_http = list(range(2**16))
        args.ports_https = list(range(2**16))

    urls_raw = set()
    for u in args.urls:
        urls_raw.update(process_url(u.strip()))
    if args.url_file:
        for u in open(args.url_file):
            urls_raw.update(process_url(u.strip()))
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

    creds = []
    if args.creds:
        creds = json.loads(open(args.creds).read())

    print('Shooting {} url(s)'.format(len(urls)))
    screen.shoot.from_urls(urls, args.threads, args.timeout, args.screen_wait, args.node_path, session, args.mobile, creds)

def handle_report(args):
    template = Template.Tiles if args.tiles else Template.Lines
    session = screen.session.WebShooterSession(args.session)
    name = report.generate.from_session(session, template, args.page_size, args.unique, args.ignore_errors)
    if name:
        print('Report generated: '+name)
    else:
        print('Nothing to do')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help='Choose an action')

    # Global options
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug output')
    parser.add_argument('-v', '--verbose', action='store_true', help='enable verbose output')
    parser.add_argument('-s', '--session', required=True, help='session file')
    parser.set_defaults(handle=lambda x:parser.print_help())

    # scan
    scan_parser = subparsers.add_parser('scan', help='Screenshot urls')
    scan_parser.set_defaults(handle=handle_scan)
    scan_parser.add_argument('-x', '--nmap-xml', dest='nmap_xml', help='nmap xml')
    scan_parser.add_argument('-u', '--url-file', dest='url_file', help='urls 1 per line. include scheme')
    scan_parser.add_argument('-n', '--node-path', dest='node_path', default='node', help='nodejs path')
    scan_parser.add_argument('-t', '--timeout', default=5, type=int, help='timeout in seconds')
    scan_parser.add_argument('-w', '--threads', default=10, type=int, help='worker thread count')
    scan_parser.add_argument('-l', '--screen-wait', dest='screen_wait', default=2000, type=int, help='wait in millisecs between page load and screenshot')
    scan_parser.add_argument('--mobile', action='store_true', help='Emulate mobile device')
    scan_parser.add_argument('-r', '--retry', action='store_true', help='retry failed urls')
    scan_parser.add_argument('-c', '--creds', help='json file for basic auth: [["user", "pass"], ...]')
    scan_parser.add_argument('--ports-http', dest='ports_http', default=DEFAULT_HTTP_PORTS,
                        type=split_ports, help='comma-separated')
    scan_parser.add_argument('--ports-https', dest='ports_https', default=DEFAULT_HTTPS_PORTS,
                        type=split_ports, help='comma-separated')
    scan_parser.add_argument('--all-open', dest='all_open', action='store_true', help='scan all open ports')
    scan_parser.add_argument('urls', default=[], nargs='*', help='urls including scheme')

    # report
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.set_defaults(handle=handle_report)
    report_parser.add_argument('-i', '--ignore-errors', dest='ignore_errors',action='store_true',
                               help='ignore non-2XX responses')
    report_parser.add_argument('-t', '--tiles', action='store_true', help='Generate report with tiles')
    report_parser.add_argument('-u', '--unique', action='store_true', help='Ignore duplicate urls from redirects')
    report_parser.add_argument('-p', '--page-size', dest='page_size', default=40, type=int, help='results per page')

    args = parser.parse_args()

    if args.debug or args.verbose:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter('[%(levelname)s] %(filename)s:%(lineno)s %(message)s'))
        for n in [__name__, 'js', 'targets', 'report', 'screen']:
            l = logging.getLogger(n)
            if args.debug:
                l.setLevel(logging.DEBUG)
            else:
                l.setLevel(logging.INFO)
            l.addHandler(h)

    args.handle(args)
