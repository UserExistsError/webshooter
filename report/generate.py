import os
import shutil
import logging
from collections import deque

import report.template

logger = logging.getLogger(__name__)

report_files = [
    os.path.join(os.path.dirname(__file__), 'web.js'),
    os.path.join(os.path.dirname(__file__), 'style.css')
]

def copy_files():
    for r in report_files:
        logger.debug('Copying report file: '+r)
        shutil.copy(r, os.path.basename(r))

def title_sort(x):
    return x['title'].lower()

def server_sort(x):
    return x['server'].lower()

def all_sort(x):
    return title_sort(x) if x['title'] else server_sort(x)

def get_index(r):
    return r['title'].lower() if r['title'] else r['server'].lower()

def from_session(session, template, page_size, unique=False):
    ''' {'url': url, 'url_final', url, 'title': page_title, 'server': server_header, 'status': status_code,
    'image': file} '''
    results = session.get_results(unique)
    if len(results) == 0:
        return None
    logger.info('Generating report: {} screenshot(s)'.format(len(results)))
    results = list(sorted(results, key=all_sort))
    page_count = (len(results) + page_size - 1) // page_size
    pages = ['page.{}.html'.format(i) for i in range(page_count)]
    last_index = get_index(results[0])
    index_list = []
    for i, pageno in zip(range(0, len(results), page_size), range(len(pages))):
        # build index that maps each unique page title/server to the first occurence
        for j, r in enumerate(results[i:i+page_size]):
            index = get_index(r)
            if index != last_index:
                last_index = index
                href = '{}#result-id-{}'.format(pages[pageno], i+j)
                index_list.append([index, href, pageno])
        # pageno is zero based
        page_prev = pages[(pageno+len(pages)-1) % len(pages)]
        page_next = pages[(pageno+1) % len(pages)]
        screens = results[i:i+page_size]
        for j, s in enumerate(screens):
            s['id'] = 'result-id-{}'.format(pageno * page_size + j)
        pages_index = deque([{'href': p, 'number':i} for i, p in enumerate(pages)])
        # center active page
        pages_index.rotate(len(pages)//2 - pageno)
        page = report.template.populate(template, 'Page {}'.format(pageno), screens, len(results),
                                        pages_index, pageno, page_prev, page_next, pages)
        logger.info('Generating {}'.format(pages[pageno]))
        open(pages[pageno], 'w').write(page)
    open('index.html', 'w').write(report.template.populate_index(report.template.Template.Index, index_list))
    copy_files()
    return pages[0]