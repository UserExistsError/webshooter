import json
import sqlite3
import threading

class Status:
    QUEUED=0
    FINISHED=1
    ERROR=2
    INVALID=3

class WebShooterSession():
    def __init__(self, session_file, urls=[]):
        self.session_file = session_file
        self.local = None
        self.init_db(urls)
    def get_conn(self):
        if not getattr(self.local, 'conn', None):
            self.local = threading.local()
            self.local.conn = sqlite3.connect(self.session_file)
        return self.local.conn
    def init_db(self, urls):
        conn = self.get_conn()
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS urls
            (id INTEGER PRIMARY KEY, url TEXT, status INTEGER, UNIQUE(url))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS screens
            (id INTEGER PRIMARY KEY, url TEXT, url_final TEXT, title TEXT, server TEXT, headers TEXT,
            status INTEGER, image TEXT, UNIQUE(url))''')
            conn.executemany('INSERT OR IGNORE INTO urls (url, status) VALUES (?, ?)',
                             [(u, Status.QUEUED) for u in urls])
    def update_url(self, url, value):
        conn = self.get_conn()
        with conn:
            conn.execute('UPDATE urls SET status=? WHERE url=?', (value, url))
    def add_screen(self, screen):
        conn = self.get_conn()
        with conn:
            conn.execute('''INSERT OR IGNORE INTO screens (url, url_final, title, server, headers, status, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (screen['url'], screen['url_final'], screen['title'],
                          screen['server'], screen['headers'], screen['status'], screen['image']))
            conn.execute('UPDATE urls SET status=1 WHERE url=?', (screen['url'],))
    def get_queued_urls(self):
        conn = self.get_conn()
        cursor = conn.execute('SELECT * FROM urls WHERE status = ?', (Status.QUEUED,))
        return [r[1] for r in cursor.fetchall()]
    def get_failed_urls(self):
        conn = self.get_conn()
        cursor = conn.execute('SELECT * FROM urls WHERE status = ?', (Status.ERROR,))
        return [r[1] for r in cursor.fetchall()]
    def get_results(self):
        conn = self.get_conn()
        cursor = conn.execute('SELECT url, url_final, title, server, headers, status, image FROM screens')
        return [{
            'url': r[0], 'url_final': r[1], 'title': r[2], 'server': r[3], 'headers': json.loads(r[4]),
            'status': r[5], 'image': r[6]
        } for r in cursor.fetchall()]
