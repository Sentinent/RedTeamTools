# HTTP Server
A small HTTP server that hosts folders for file sharing. Also provides a termbin-like service.

## Usage
```
python3 server.py -h

usage: server.py [-h] [-s SHARE] [--purge] [--host HOST] [-p PORT] [-ph PASTE_HOST] [-pp PASTE_PORT]

Simple Python3 HTTP Server

optional arguments:
  -h, --help            show this help message and exit
  -s SHARE, --share SHARE
                        Specifies which directories will be shared. By default, ./share will be shared.
  --purge               If set, the previous database will be cleared on start.
  --host HOST           The host to run the webserver on.
  -p PORT, --port PORT  The port to run the webserver on.
  -ph PASTE_HOST, --paste-host PASTE_HOST
                        The host to run the paste service on.
  -pp PASTE_PORT, --paste-port PASTE_PORT
                        The port to run the paste service on.
```

## Example
Starting the server

`python3 server.py --share /usr/bin --share /usr/share/wordlists`

### File Transfer
Then, navigate to `http://localhost:8080/browse` to view available files to download.


### Termbin
`ls -la | nc localhost 9999`

Then, navigate to `http://localhost:8080/pastes` to view files.
The service also accepts HTTP POST requests, for example:

`curl -X POST -d "This is binary data" http://localhost:8080/paste`