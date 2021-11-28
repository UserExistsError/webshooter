import sys
import json
import shutil
import logging
import argparse

import targets.nmap
import targets.urls
import report.generate
import screen.shoot
import screen.session
import screen.capture
from report.template import Template

logger = logging.getLogger(__name__)

DEFAULT_HTTP_PORTS = {80, 8080}
DEFAULT_HTTPS_PORTS = {443, 8443}

def split_ports(ports: str) -> set[int]:
    return set(map(int, ports.split(',')))

def handle_scan(args):
    # verify node exists
    if shutil.which(args.node_path) is None:
        print('Failed to find node executable')
        sys.exit(1)

    # get urls to screenshot
    if args.all_open:
        args.ports_http = set(range(2**16))
        args.ports_https = set(range(2**16))

    urls = set()
    if args.urls:
        urls.update(targets.urls.from_iterator(args.urls))
    if args.url_file:
        urls.update(targets.urls.from_file(args.url_file))
    if args.nmap_xml:
        urls.update(targets.nmap.from_xml(args.nmap_xml, args.ports_http, args.ports_https))

    # The session will dedupe URLs. We add failed URLs back in if requested.
    session = screen.session.WebShooterSession(args.session, urls)
    urls = set(session.get_queued_urls())
    if args.retry:
        failed_urls = session.get_failed_urls()
        print('Retrying {} failed URL(s)'.format(len(failed_urls)))
        for u in failed_urls:
            logger.debug('retrying failed URL: %s', u)
        urls.update(failed_urls)

    print('Shooting {} URL(s)'.format(len(urls)))

    if args.dryrun:
        for u in urls:
            print('Shooting', u)
        return

    if len(urls) == 0:
        return

    with screen.capture.CaptureService(args.node_path) as client:
        client.configure(args.mobile, args.screen_wait_ms, args.page_wait_ms)
        screen.shoot.capture_from_urls(urls, args.threads, session, client)

def handle_report(args):
    template = Template.SingleColumn if args.column else Template.Tiles
    session = screen.session.WebShooterSession(args.session)
    name = report.generate.from_session(session, template, args.page_size, args.ignore_errors, args.embed_images)
    if name:
        print('Report generated: '+name)
    else:
        print('Nothing to do')

def run():
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
    scan_parser.add_argument('-w', '--threads', default=5, type=int, help='number of concurrent screenshots to take. default 5')
    scan_parser.add_argument('-t', '--page-timeout', dest='page_wait_ms', default=5000, type=int, help='timeout in millisecs for page load event')
    scan_parser.add_argument('-l', '--screen-wait', dest='screen_wait_ms', default=2000, type=int, help='wait in millisecs between page load and screenshot')
    scan_parser.add_argument('--mobile', action='store_true', help='Emulate mobile device')
    scan_parser.add_argument('-r', '--retry', action='store_true', help='retry failed urls')
    scan_parser.add_argument('--ports-http', dest='ports_http', default=DEFAULT_HTTP_PORTS,
                        type=split_ports, help='comma-separated')
    scan_parser.add_argument('--ports-https', dest='ports_https', default=DEFAULT_HTTPS_PORTS,
                        type=split_ports, help='comma-separated')
    scan_parser.add_argument('--all-open', dest='all_open', action='store_true', help='scan all open ports')
    scan_parser.add_argument('urls', default=[], nargs='*', help='urls including scheme')
    scan_parser.add_argument('--dryrun', action='store_true', help='list URLs to scan')

    # report
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.set_defaults(handle=handle_report)
    report_parser.add_argument('-i', '--ignore-errors', dest='ignore_errors',action='store_true',
                               help='ignore non-2XX responses')
    report_parser.add_argument('--column', action='store_true', help='Generate report with single column')
    report_parser.add_argument('-p', '--page-size', dest='page_size', default=8, type=int, help='results per page')
    report_parser.add_argument('--embed-images', dest='embed_images', action='store_true', help='Embed images in HTML as base64')

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
