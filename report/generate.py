import logging

import report.template

logger = logging.getLogger(__name__)


def title_sort(x):
    return x['title'].lower()

def server_sort(x):
    return x['server'].lower()

def all_sort(x):
    return title_sort(x) if x['title'] else server_sort(x)

def get_index(r):
    return r['title'].lower() if r['title'] else r['server'].lower()

def from_session(session, template, page_size):
    ''' {'url': url, 'url_final', url, 'title': page_title, 'server': server_header, 'status': status_code,
    'image': file} '''
    results = session.get_results()
    if len(results) == 0:
        return
    logger.debug('Generating report: {} screenshot(s)'.format(len(results)))
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
        pageno_prev = (pageno+len(pages)-1) % len(pages)
        pageno_next = (pageno+1) % len(pages)
        rows = results[i:i+page_size]
        for j, r in enumerate(rows):
            r['id'] = 'result-id-{}'.format(pageno * page_size + j)
        pages_index = [{'href': p, 'number':i} for i, p in enumerate(pages)]
        page = report.template.populate(template, 'Page {}'.format(pageno), rows, len(results),
                                        pages_index, pageno, pageno_prev, pageno_next)
        logger.debug('Generating {}'.format(pages[pageno]))
        open(pages[pageno], 'w').write(page)
    open('index.html', 'w').write(report.template.populate_index(report.template.Template.Index, index_list))
