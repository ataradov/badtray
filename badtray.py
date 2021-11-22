#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2021, Alex Taradov <alex@taradov.com>. All rights reserved.
import html
import os
import time
import http.server
import socketserver
import configparser

# curl -T test.bin -utest:12345 http://127.0.0.1:12345/test/1/test-linux.bin

#------------------------------------------------------------------------------
config = configparser.ConfigParser()
config.read('config.ini')

PORT       = eval(config['main']['port'])
AUTH       = config['main']['auth']
PATH       = config['main']['path']
VPATH      = config['main']['vpath']
MAX_SIZE   = eval(config['main']['max_size'])

#------------------------------------------------------------------------------
STYLE = [
  '<style>',
  '* { font-family: Arial, Helvetica, sans-serif; background: #fff; }',
  'table { border-spacing: 0px; border-style: none; border-color: #000000; border-collapse: collapse; }',
  'th { border-width: 1px; border-style: solid; padding: 3pt 1em 3pt 1em; border-color: #000; background: #f0f0f0; }',
  'td { border-width: 1px; border-style: solid; padding: 3pt 1em 3pt 1em; border-color: #000; background: #ffffff; }',
  '</style>',
]

#------------------------------------------------------------------------------
def build_file_index(name):
  path = os.path.join(PATH, name)

  dir_list = os.listdir(path)

  if 'index.html' in dir_list:
    dir_list.remove('index.html')

  dir_list.sort(key=int, reverse=True)

  text = [
    '<!doctype html>',
    '<html lang=en>',
    '<head>',
    '<meta charset=utf-8>',
    '<title>Binaries for %s</title>' % html.escape(name),
    '\n'.join(STYLE),
    '</head>',
    '<body>',
    '<table>'
    '<tr><th>Index</th><th>Created</th><th>Files</th>',
  ]

  for d in dir_list:
    dir_path = os.path.join(path, d)

    mtime = os.path.getmtime(dir_path)
    last_mod = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(mtime))

    files = os.listdir(dir_path)
    files.sort()

    files_str = ''.join(['<a href="%s">[%s]</a>&emsp;' % (html.escape(os.path.join(VPATH, name, d, f)), html.escape(f)) for f in files])

    text += ['<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (html.escape(d), html.escape(last_mod), files_str)]

  text += [
    '</table>'
    '</body>',
    '</html>',
  ]

  try:
    open(os.path.join(path, 'index.html'), 'w').write('\n'.join(text))
  except:
    return False

  return True

#------------------------------------------------------------------------------
def build_index():
  dir_list = os.listdir(PATH)

  if 'index.html' in dir_list:
    dir_list.remove('index.html')

  dir_list.sort()

  text = [
    '<!doctype html>',
    '<html lang=en>',
    '<head>',
    '<meta charset=utf-8>',
    '<title>Binaries</title>',
    '\n'.join(STYLE),
    '</head>',
    '<body>',
    '<p>Available binaries:</p>',
    '<ul>'
  ]

  for d in dir_list:
    text += ['<li><a href="%s">%s</a></li>' % (html.escape(os.path.join(VPATH, d)), html.escape(d))]

  text += [
    '</ul>',
    '</body>',
    '</html>',
  ]

  try:
    open(os.path.join(PATH, 'index.html'), 'w').write('\n'.join(text))
  except:
    return False

  for d in dir_list:
    if not build_file_index(d):
      return False

  return True

#------------------------------------------------------------------------------
def name_valid(name):
  if name in ['.', '..']:
    return False

  for c in name:
    if not c.isalnum() and c not in ['-', '_', '.']:
      return False

  return True

#------------------------------------------------------------------------------
class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

  def send_reply(self, messsage):
    self.send_response(200)
    self.send_header('Content-type', 'text/plain')
    self.end_headers()
    self.wfile.write(('%s\n' % messsage).encode())

  def do_PUT(self):
    print('Request headers:')
    print(self.headers)

    if self.headers['Expect'] == '100-continue':
      self.send_response(100)
      self.end_headers()

    if self.headers['Authorization'] != AUTH:
      self.send_reply('Not authorized')
      return

    content_length = int(self.headers['Content-Length'], 0)

    if content_length == 0 or content_length > MAX_SIZE:
      self.send_reply('Invalid content length')
      return

    path = self.translate_path(self.path)

    if path == None:
      self.send_reply('Invalid path')
      return

    print('Saving file %s, %d bytes' % (path, content_length))

    try:
      os.makedirs(os.path.dirname(path))
    except FileExistsError:
      pass

    try:
      open(path, 'wb').write(self.rfile.read(content_length))
    except:
      self.send_reply('File write failed')
      return

    if not build_index():
      self.send_reply('Index build failed')
      return

    self.send_reply('OK')

  def translate_path(self, path):
    parts = path.strip('/').split('/')

    if len(parts) != 3:
      return None

    for part in parts:
      if not name_valid(part):
        return None

    if not parts[1].isdigit():
      return None

    return os.path.join(PATH, parts[0], parts[1], parts[2])

#------------------------------------------------------------------------------
socketserver.TCPServer.allow_reuse_address = True

print('Serving on port %d' % PORT)
httpd = socketserver.TCPServer(('', PORT), CustomHTTPRequestHandler)
httpd.serve_forever()


