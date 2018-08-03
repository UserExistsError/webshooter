import os
import sys
import string
import jinja2

PAGE_TEMPLATE=os.path.join(os.path.dirname(sys.argv[0]), 'report/page_template.html')

def populate(title, rows, count, pages, pageno, pageno_prev, pageno_next):
    template = jinja2.Template(open(PAGE_TEMPLATE, 'rb').read().decode())
    return template.render(title=title, rows=rows, count=count, pages=pages, pageno=pageno,
                           pageno_prev=pageno_prev, pageno_next=pageno_next)
