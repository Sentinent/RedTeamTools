#!/usr/bin/env python

import argparse
import atexit
import os
import sqlite3
import time
from flask import Flask, render_template, Response, request, send_file
from pathlib import Path
from typing import *

from paste import create_paste_thread

# returns a path relative to the script
def rel_path(path) -> str:
    return str((Path(__file__).parent.absolute() / path).resolve())

def short_path_to_full(path: str) -> Path:
    parts = path.split('/')
    path = '/'.join((
        app.config['path_map'].get(parts[0], parts[0]),
        '/'.join(parts[1:])
    ))

    return Path(path).resolve()

def full_path_to_short(path: Union[str, Path]) -> str:
    if type(path) != str:
        path = str(path.resolve())

    for short, full in app.config['path_map'].items():
        path = path.replace(full, short)

    return path

def path_allowed(path: Union[str, Path]) -> bool:
    if type(path) == str:
        path = Path(path)

    requested_path = path.resolve()

    for p in app.config['share_paths']:
        if str(requested_path).startswith(str(p)):
            return True
    return False

def create_db():
    path = rel_path('./database.sqlite')
    if os.path.exists(path):
        return

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute('CREATE TABLE pastes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date INTEGER, content BLOB, size INTEGER, is_text BOOL);')
    conn.commit()

# 

app = Flask('Simple HTTP Server', template_folder=rel_path('./templates'), static_folder=rel_path('./static'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/browse')
def browse():
    path = request.args.get('path', '0')

    # replace the first part with the long name if possible
    requested_path = short_path_to_full(path)

    if not path_allowed(requested_path):
        return '', 403

    path_prefix = full_path_to_short(path)

    curr_dir, dirnames, filenames = next(os.walk(requested_path))

    dirs = []
    if path_allowed(requested_path.parent):
        dirs.append((f'/browse?path={full_path_to_short(requested_path.parent)}', '..'))
    dirs.extend((os.path.join(f'/browse?path={path_prefix}', x), x) for x in dirnames)

    return render_template('browse.html',
        shared_folders=app.config['shared_hrefs'],
        curr_dir=curr_dir,
        dirs=dirs,
        files=[(os.path.join(f'/download?path={path_prefix}', x), x) for x in filenames]
    )

@app.route('/download')
def download():
    path = request.args.get('path')
    if not path:
        return 'No file specified.', 400
    
    path = short_path_to_full(path)
    if not path_allowed(path) or not path.is_file():
        return '', 403

    return send_file(path, as_attachment=True, attachment_filename=path.name)

@app.route('/pastes')
def pastes():
    with sqlite3.connect(rel_path('./database.sqlite')) as conn:
        cur = conn.cursor()

        rows = cur.execute('SELECT * FROM pastes ORDER BY id DESC;').fetchall()
        pastes = [
            {
                'id': row[0],
                'name': row[1],
                'timestamp': f'{round((time.time() - row[2]) / 60)} minutes ago',
                'content': row[3].decode('utf-8') if row[5] else '',
                'size': row[4]
            } for row in rows
        ]

        return render_template('pastes.html', pastes=pastes)


@app.route('/paste', methods=['POST'])
def paste():
    data = request.get_data()
    with sqlite3.connect(rel_path('./database.sqlite')) as conn:
        cur = conn.cursor()

        is_text = True
        try:
            data.decode('utf-8')
        except UnicodeDecodeError: 
            is_text = False

        t = time.time()
        cur.execute('INSERT INTO pastes (name, date, content, size, is_text) VALUES (?, ?, ?, ?, ?)',
        (
            str(t) + ('.txt' if is_text else ''),
            t,
            data,
            len(data),
            is_text
        ))
        conn.commit()

        return Response(f'{request.host_url}download_paste/{cur.lastrowid}', 'text/plain')

@app.route('/download_paste/<int:paste_id>')
def download_paste(paste_id):
    with sqlite3.connect(rel_path('./database.sqlite')) as conn:
        cur = conn.cursor()

        row = cur.execute('SELECT * FROM pastes WHERE id=?;', (paste_id,)).fetchone()
        if not row:
            return 'Paste not found.', 404

        data = row[3]
        if (row[5]): # is_text
            data = data.decode('utf-8')
        return Response(data, mimetype='text/plain' if row[5] else 'application/octet-stream')

def main():
    parser = argparse.ArgumentParser(description='Simple Python3 HTTP Server')
    parser.add_argument('-s', '--share', action='append', required=False, help='Specifies which directories will be shared. By default, ./share will be shared.')
    parser.add_argument('--purge', action='store_true', default=False, required=False, help='If set, the previous database will be cleared on start.')
    parser.add_argument('--host', action='store', default='0.0.0.0', type=str, required=False, help='The host to run the webserver on.', dest='host')
    parser.add_argument('-p', '--port', action='store', default=8080, type=int, required=False, help='The port to run the webserver on.', dest='port')
    
    parser.add_argument('-ph', '--paste-host', action='store', default='0.0.0.0', type=str, required=False, help='The host to run the paste service on.', dest='paste_host')
    parser.add_argument('-pp', '--paste-port', action='store', default=9999, type=int, required=False, help='The port to run the paste service on.', dest='paste_port')

    args = parser.parse_args()
    default_share = rel_path('./share')
    if not args.share:
        args.share = [default_share]
    else:
        args.share.insert(0, default_share)

    app.config['share_paths'] = []
    app.config['path_map'] = {}
    app.config['shared_hrefs'] = []
    for i, x in enumerate(args.share):
        path = Path(x).resolve()
        app.config['share_paths'].append(path)
        app.config['path_map'][str(i)] = str(path)
        app.config['shared_hrefs'].append((f'/browse?path={i}', path.parts[-1]))

    db_path = rel_path('./database.sqlite')
    if args.purge:
        try:
            os.remove(db_path)
        except FileNotFoundError:
            pass

    create_db()

    paste_thread = create_paste_thread(args.paste_host, args.paste_port, db_path, f'{args.host}:{args.port}')

    def cleanup():
        paste_thread.cleanup()
        paste_thread.join()

    atexit.register(cleanup)
    app.run(host=args.host, port=args.port)

if __name__ == '__main__':
    main()