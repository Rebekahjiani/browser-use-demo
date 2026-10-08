"""Shared read-only Shopping request boundary over SSH; no credentials saved."""
import argparse
import getpass
import http.client
import http.server
import json
import os
import pathlib
import re
import threading
from urllib.parse import unquote, urlsplit


class BufferedChannel:
    """Keep SSH alive while HTTP reads a Connection: close response file."""
    def __init__(self, channel):
        self.channel = channel

    def makefile(self, mode, *args):
        return self.channel.makefile(mode, 65536)

    def sendall(self, data):
        return self.channel.sendall(data)

    def close(self):
        # HTTPConnection closes its socket before the response body is read.
        # A socket.makefile keeps its underlying FD alive; a ChannelFile does not.
        # The request handler explicitly closes the channel after reading.
        pass


def allowed(method, target, origin='http://127.0.0.1:7770'):
    if method not in {'GET', 'HEAD'}:
        return False
    parts = urlsplit(target)
    if (parts.scheme or parts.netloc) and f'{parts.scheme}://{parts.netloc}' != origin:
        return False
    path = unquote(parts.path)
    if '\\' in path or any(p in {'.', '..'} for p in path.split('/')):
        return False
    if path == '/':
        return True
    if path.startswith(('/static/', '/media/')):
        return True
    if re.fullmatch(r'/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*\.html', path):
        return True
    return bool(re.fullmatch(
        r'/(?:catalogsearch/(?:result|advanced|advanced/result)|checkout/cart|customer/section/load|'
        r'catalog/product/view/id/\d+|catalog/category/view/id/\d+|review/product/list/id/\d+)/?', path))


def main():
    import paramiko
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=7770)
    parser.add_argument('--remote-port', type=int, default=7770)
    parser.add_argument('--host', default='218.245.63.97')
    parser.add_argument('--ssh-port', type=int, default=2286)
    parser.add_argument('--user', default='ubuntu')
    parser.add_argument('--log', required=True)
    args = parser.parse_args()
    password = os.environ.pop('BENCHMARK_SSH_PASSWORD', None) or getpass.getpass('SSH password: ')
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.connect(args.host, port=args.ssh_port, username=args.user, password=password,
                   look_for_keys=False, allow_agent=False, timeout=20)
    password = None
    client.get_transport().set_keepalive(20)
    log = pathlib.Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def handle_request(self):
            permitted = allowed(self.command, self.path, f'http://127.0.0.1:{args.port}')
            with lock, log.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps({'method': self.command, 'path': urlsplit(self.path).path,
                                         'allowed': permitted}) + '\n')
            if not permitted:
                self.close_connection = True
                self.send_error(403, 'Benchmark read-only route boundary')
                return
            connection = http.client.HTTPConnection('127.0.0.1', args.remote_port, timeout=45)
            channel = None
            try:
                channel = client.get_transport().open_channel(
                    'direct-tcpip', ('127.0.0.1', args.remote_port), ('127.0.0.1', args.port), timeout=45)
                connection.sock = BufferedChannel(channel)
                headers = {k: v for k, v in self.headers.items()
                           if k.lower() not in {'connection', 'proxy-connection', 'transfer-encoding', 'content-length'}}
                headers['Host'] = f'127.0.0.1:{args.port}'
                headers['Connection'] = 'close'
                parts = urlsplit(self.path)
                target = parts.path + ('?' + parts.query if parts.query else '')
                connection.request(self.command, target, headers=headers)
                response = connection.getresponse()
                body = response.read()
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in {'connection', 'transfer-encoding', 'content-length'}:
                        self.send_header(key, value)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Connection', 'close')
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(body)
            except Exception as exc:
                with lock, log.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps({'event': 'upstream_error', 'type': type(exc).__name__,
                                             'reason': str(exc)}) + '\n')
                self.send_error(502, 'Shopping connection failed')
            finally:
                self.close_connection = True
                connection.close()
                if channel is not None:
                    channel.close()

        do_GET = handle_request
        do_HEAD = handle_request
        do_POST = handle_request
        do_PUT = handle_request
        do_PATCH = handle_request
        do_DELETE = handle_request
        do_OPTIONS = handle_request

        def log_message(self, *args):
            pass

    print(f'Read-only Shopping boundary listening on 127.0.0.1:{args.port}', flush=True)
    try:
        http.server.ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
    finally:
        client.close()


if __name__ == '__main__':
    main()
