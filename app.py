"""
app.py - web server for the String Compiler (Python standard library only)

    GET  /          -> static/index.html  (and style.css, script.js)
    POST /compile   -> runs compiler.compile_code() on the code, returns JSON

Start it with:   python app.py      then open http://localhost:8000
"""
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from compiler import compile_code

PORT = 8000
STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC, **kwargs)

    def do_POST(self):
        if self.path != "/compile":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        code = json.loads(self.rfile.read(length))["code"]
        body = json.dumps(compile_code(code)).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"String Compiler running at http://localhost:{PORT}   (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
