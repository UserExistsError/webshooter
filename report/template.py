import string
import jinja2

PAGE_TEMPLATE='report/page_template.html'

def populate(title, rows, pages, pageno, pageno_prev, pageno_next):
    template = jinja2.Template(open(PAGE_TEMPLATE, 'rb').read().decode())
    return template.render(title=title, rows=rows, pages=pages, pageno=pageno,
                           pageno_prev=pageno_prev, pageno_next=pageno_next)
