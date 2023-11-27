import http.server
import socketserver
import os

class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = 'index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

def run(port: int = 8001):
    web_dir = os.path.join(os.path.dirname(__file__))
    os.chdir(web_dir)

    Handler = HttpRequestHandler

    with socketserver.TCPServer(("", port), Handler) as httpd:
        print("Serving HTTP at port", port)
        httpd.serve_forever()

if __name__ == '__main__':
    run()