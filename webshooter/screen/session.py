import os
import json
import sqlite3
import logging
import threading
import urllib.parse
from typing import Any

logger = logging.getLogger(__package__)

class Status:
    QUEUED=0
    FINISHED=1
    ERROR=2
    INVALID=3
    DUPLICATE=4

class WebShooterSession():
    local = threading.local()
    def __init__(self, session_file: str, urls: list[str]=[]):
        self.connections = 0
        self.session_file = session_file
        if not os.path.exists(session_file):
            logger.info('Creating new session file: '+session_file)
        self._init_db(urls)
    def _get_conn(self) -> Any:
        if not getattr(self.local, 'conn', None):
            self.local.conn = sqlite3.connect(self.session_file)
            self.connections += 1
        return self.local.conn
    def _init_db(self, urls: list[str]):
        conn = self._get_conn()
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS urls
            (id INTEGER PRIMARY KEY, url TEXT, status INTEGER, UNIQUE(url))''')
            conn.execute('''CREATE TABLE IF NOT EXISTS screens
            (id INTEGER PRIMARY KEY, url TEXT, url_final TEXT, title TEXT, server TEXT, headers TEXT,
            status INTEGER, image TEXT, UNIQUE(url))''')
            conn.executemany('INSERT OR IGNORE INTO urls (url, status) VALUES (?, ?)',
                             [(u, Status.QUEUED) for u in urls])
    def update_url(self, url: str, value: Status):
        conn = self._get_conn()
        with conn:
            conn.execute('UPDATE urls SET status=? WHERE url=?', (value, url))
    def add_screen(self, screen):
        conn = self._get_conn()
        with conn:
            conn.execute('''INSERT OR IGNORE INTO screens
            (url, url_final, title, server, headers, status, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
                         (screen['url'], screen['url_final'], screen['title'], screen['server'],
                          screen['headers'], screen['status'], screen['image']))
            conn.execute('UPDATE urls SET status = ? WHERE url = ?', (Status.FINISHED, screen['url']))
    def url_screen_exists(self, url_final: str):
        conn = self._get_conn()
        with conn:
            cur = conn.execute('SELECT url FROM screens WHERE url_final = ? COLLATE NOCASE', (url_final,))
            return cur.fetchone()
    def get_queued_urls(self) -> list[str]:
        conn = self._get_conn()
        cursor = conn.execute('SELECT * FROM urls WHERE status = ?', (Status.QUEUED,))
        return [r[1] for r in cursor.fetchall()]
    def get_failed_urls(self) -> list[str]:
        conn = self._get_conn()
        cursor = conn.execute('SELECT * FROM urls WHERE status = ?', (Status.ERROR,))
        return [r[1] for r in cursor.fetchall()]
    def _normalize_url(self, u: str, ignore_params: bool=False) -> str:
        p = urllib.parse.urlparse(u)
        port = p.port
        if port is None:
            if p.scheme.lower() == 'http':
                port = 80
            elif p.scheme.lower() == 'https':
                port = 443
            else:
                port = ''
        return '{}://{}:{}/{}?{}'.format(p.scheme, p.hostname, port, p.path.strip('/'), '' if ignore_params else p.query)
    def get_results(self, ignore_errors: bool=False, unique: bool=True) -> list[dict[str, Any]]:
        conn = self._get_conn()
        if ignore_errors:
            cursor = conn.execute('SELECT url, url_final, title, server, headers, status, image FROM screens WHERE status >= 200 AND status < 400 ORDER BY title, server ASC')
        else:
            cursor = conn.execute('SELECT url, url_final, title, server, headers, status, image FROM screens ORDER BY title, server ASC')

        results = [{
            'url': r[0], 'url_final': r[1], 'title': r[2], 'server': r[3], 'headers': json.loads(r[4]),
            'status': r[5], 'image': r[6]
        } for r in cursor.fetchall()]
        if unique:
            # XXX there is an issue here because mobile emulation may result in a final url of "about:blank"
            uniq = {self._normalize_url(r['url_final']): r for r in results}
            results = uniq.values()
        return results
