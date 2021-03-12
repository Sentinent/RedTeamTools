import socket
import sqlite3
import time
import threading

from select import select

class PasteServiceThread(threading.Thread):
    def __init__(self, host, port, database_path, webserver_host):
        super(PasteServiceThread, self).__init__()

        self.host = host
        self.port = port
        self.db_path = database_path
        self.webserver_host = webserver_host

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True

    def run(self):
        self.db_conn = sqlite3.connect(self.db_path)
        self.db_cur = self.db_conn.cursor()

        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen()

        while self.running:
            readable, _, _ = select([self.socket], [], [], 5)
            if len(readable) > 0:
                data = b''
                conn, addr = self.socket.accept()
                while True:
                    part = conn.recv(4096)
                    data += part
                    if len(part) < 4096:
                        break
                
                is_text = True
                try:
                    data.decode('utf-8')
                except UnicodeDecodeError: 
                    is_text = False

                t = time.time()
                self.db_cur.execute('INSERT INTO pastes (name, date, content, size, is_text) VALUES (?, ?, ?, ?, ?)',
                (
                    str(t) + ('.txt' if is_text else ''),
                    t,
                    data,
                    len(data),
                    is_text
                ))
                self.db_conn.commit()

                conn.send(f'http://{self.webserver_host}/download_paste/{self.db_cur.lastrowid}'.encode('ascii'))
                conn.close()

        self.socket.close()
        self.db_conn.close()
        print('Paste service stopped.')

    def cleanup(self):
        print('Paste service cleaning up...')
        self.running = False

def create_paste_thread(host, port, database_path, webserver_host):
    t = PasteServiceThread(host, port, database_path, webserver_host)
    t.start()
    return t

if __name__ == '__main__':
    print('This file is not meant to be run directly. You probably meant to run server.py.')