import os
import string
import jinja2
from jinja2 import Environment, FileSystemLoader

env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    autoescape=True
);

class Template:
    SingleColumn = 'page.html'
    Tiles = 'card.html'
    Index = 'index.html'

def populate(template, title, screens, count, pages_index, pageno, page_prev, page_next, pages):
    t = env.get_template(template)
    return t.render(
        title=title,
        screens=screens,
        count=count,
        pages_index=pages_index,
        pageno=pageno,
        page_prev=page_prev,
        page_next=page_next,
        pages=pages)

def populate_index(template, index):
    t = env.get_template(template)
    return t.render(index=index, title='Report Index')
