import os
import string
import jinja2

class Template:
    SingleColumn=os.path.join(os.path.dirname(__file__), 'page_template.html')
    Tiles=os.path.join(os.path.dirname(__file__), 'card_template.html')
    Index=os.path.join(os.path.dirname(__file__), 'index_template.html')

def populate(template, title, screens, count, pages_index, pageno, page_prev, page_next, pages):
    html = jinja2.Template(open(template, 'rb').read().decode())
    return html.render(
        title=title,
        screens=screens,
        count=count,
        pages_index=pages_index,
        pageno=pageno,
        page_prev=page_prev,
        page_next=page_next,
        pages=pages)

def populate_index(template, index):
    html = jinja2.Template(open(template, 'rb').read().decode())
    return html.render(index=index)
