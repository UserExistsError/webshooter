import os
import sys
import string
import jinja2

class Template:
    Lines=os.path.join(os.path.dirname(sys.argv[0]), 'report/page_template.html')
    Tiles=os.path.join(os.path.dirname(sys.argv[0]), 'report/card_template.html')
    Index=os.path.join(os.path.dirname(sys.argv[0]), 'report/index_template.html')

def populate(template, title, rows, count, pages, pageno, pageno_prev, pageno_next):
    html = jinja2.Template(open(template, 'rb').read().decode())
    return html.render(title=title, rows=rows, count=count, pages=pages, pageno=pageno,
                       pageno_prev=pageno_prev, pageno_next=pageno_next)

def populate_index(template, index):
    html = jinja2.Template(open(template, 'rb').read().decode())
    return html.render(index=index)
