import os
import json
import cgi
import uuid
from wsgiref.simple_server import make_server
from urllib.parse import parse_qs

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
META_FILE = os.path.join(BASE_DIR, 'files.json')

os.makedirs(UPLOAD_DIR, exist_ok=True)
if not os.path.exists(META_FILE):
    with open(META_FILE, 'w') as f:
        json.dump([], f)

def read_meta():
    with open(META_FILE, 'r') as f:
        return json.load(f)

def write_meta(data):
    with open(META_FILE, 'w') as f:
        json.dump(data, f)

def not_found(start_response):
    start_response('404 Not Found', [('Content-Type','text/plain')])
    return [b'Not Found']

def app(environ, start_response):
    path = environ.get('PATH_INFO','')
    method = environ.get('REQUEST_METHOD','GET')

    if path == '/' and method == 'GET':
        with open('index.html','rb') as f:
            data = f.read()
        start_response('200 OK', [('Content-Type','text/html')])
        return [data]

    if path.startswith('/uploads/') and method == 'GET':
        filename = os.path.basename(path)
        file_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(file_path):
            return not_found(start_response)
        start_response('200 OK', [('Content-Type','application/octet-stream')])
        return [open(file_path,'rb').read()]

    if path == '/upload' and method == 'POST':
        fs = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ, keep_blank_values=True)
        if 'file' not in fs:
            start_response('400 Bad Request', [('Content-Type','text/plain')])
            return [b'Missing file']
        uploaded = fs['file']
        privacy = fs.getvalue('privacy','private')
        uid = str(uuid.uuid4()) + os.path.splitext(uploaded.filename)[1]
        file_path = os.path.join(UPLOAD_DIR, uid)
        with open(file_path,'wb') as f:
            f.write(uploaded.file.read())
        info = {
            'id': uid,
            'originalName': uploaded.filename,
            'size': os.path.getsize(file_path),
            'mimetype': uploaded.type,
            'privacy': privacy
        }
        meta = read_meta()
        meta.append(info)
        write_meta(meta)
        start_response('200 OK', [('Content-Type','application/json')])
        return [json.dumps({'file': info}).encode('utf-8')]

    if path == '/files' and method == 'GET':
        start_response('200 OK', [('Content-Type','application/json')])
        return [json.dumps(read_meta()).encode('utf-8')]

    if path.startswith('/files/'):
        fid = os.path.basename(path)
        meta = read_meta()
        file_info = next((f for f in meta if f['id'] == fid), None)
        if not file_info:
            return not_found(start_response)
        file_path = os.path.join(UPLOAD_DIR, fid)

        if method == 'GET':
            if not os.path.exists(file_path):
                return not_found(start_response)
            start_response('200 OK', [('Content-Type','application/octet-stream')])
            return [open(file_path,'rb').read()]
        elif method == 'DELETE':
            if os.path.exists(file_path):
                os.remove(file_path)
            meta = [f for f in meta if f['id'] != fid]
            write_meta(meta)
            start_response('200 OK', [('Content-Type','application/json')])
            return [b'{}']
        elif method == 'PATCH':
            length = int(environ.get('CONTENT_LENGTH','0'))
            body = environ['wsgi.input'].read(length)
            data = json.loads(body or b'{}')
            privacy = data.get('privacy')
            if privacy:
                file_info['privacy'] = privacy
                write_meta(meta)
            start_response('200 OK', [('Content-Type','application/json')])
            return [json.dumps(file_info).encode('utf-8')]
        else:
            start_response('405 Method Not Allowed',[('Content-Type','text/plain')])
            return [b'Method Not Allowed']

    return not_found(start_response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    with make_server('', port, app) as httpd:
        print(f"Serving on port {port}")
        httpd.serve_forever()
