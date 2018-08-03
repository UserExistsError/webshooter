import logging

import report.template

logger = logging.getLogger(__name__)


def title_sort(x):
    return x['title'].lower()

def server_sort(x):
    return x['server'].lower()

def from_session(session, page_size):
    ''' {'url': url, 'url_final', url, 'title': page_title, 'server': server_header, 'status': status_code,
    'image': file} '''
    results = session.get_results()
    logger.debug('Generating report: {} screenshot(s)'.format(len(results)))
    results_notitle = [r for r in results if not r['title']]
    results_title = [r for r in results if r['title']]
    results = list(sorted(results_notitle, key=server_sort)) + list(sorted(results_title, key=title_sort))
    page_count = (len(results) + page_size - 1) // page_size
    pages = ['page-{}.html'.format(i) for i in range(page_count)]
    for i, pageno in zip(range(0, len(results), page_size), range(len(pages))):
        pageno_prev = (pageno+len(pages)-1) % len(pages)
        pageno_next = (pageno+1) % len(pages)
        rows = results[i:i+page_size]
        pages_index = [{'href': p, 'number':i} for i, p in enumerate(pages)]
        page = report.template.populate('Page {}'.format(pageno), rows, len(results),
                                        pages_index, pageno, pageno_prev, pageno_next)
        logger.debug('Generating page {}'.format(pageno))
        open(pages[pageno], 'w').write(page)
