#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过常驻 Tuner 桥执行 Lua 并打印结果。

用法：
    .venv\\Scripts\\python.exe tuner_eval.py --state GameCore_Tuner "print('hi')"
    .venv\\Scripts\\python.exe tuner_eval.py --state InGame --file expr.lua
    .venv\\Scripts\\python.exe tuner_eval.py --states
    .venv\\Scripts\\python.exe tuner_eval.py --port 8771 --states   # 对齐 civ6_bridge --http-port

桥地址默认 http://127.0.0.1:8770（与 civ6_bridge.py 的默认 --http-port 一致）；
civ6_bridge.py 用其它端口启动时，用 --url 或 --port 跟随。
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

DEFAULT_URL = 'http://127.0.0.1:8770'
# 兼容既有 import：模块级默认地址
HTTP = DEFAULT_URL


def _base_url(url: str | None = None, port: int | None = None) -> str:
    """HTTP 桥地址：--url 优先，其次 --port（127.0.0.1），默认 8770。"""
    if url:
        return url.rstrip('/')
    if port:
        return 'http://127.0.0.1:%d' % int(port)
    return DEFAULT_URL


def post(path, payload=None, base_url=None):
    data = json.dumps(payload or {}).encode('utf-8')
    req = urllib.request.Request((base_url or HTTP) + path, data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


def get(path, base_url=None):
    with urllib.request.urlopen((base_url or HTTP) + path, timeout=30) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


def main():
    ap = argparse.ArgumentParser(description="通过常驻 Tuner 桥（civ6_bridge）执行 Lua")
    ap.add_argument('--state', default='GameCore_Tuner')
    ap.add_argument('--file')
    ap.add_argument('--states', action='store_true')
    ap.add_argument('--url', default=None, help='桥 HTTP 地址（默认 http://127.0.0.1:8770）')
    ap.add_argument('--port', type=int, default=None,
                    help='桥 HTTP 端口（对齐 civ6_bridge --http-port，默认 8770）')
    ap.add_argument('code', nargs='?')
    args = ap.parse_args()
    base = _base_url(args.url, args.port)
    if args.states:
        d = get('/states', base)
        for k, v in sorted(d.get('states', {}).items(), key=lambda x: int(x[0])):
            print(k, v)
        return 0
    code = open(args.file, encoding='utf-8-sig').read() if args.file else args.code
    if not code:
        print('no code', file=sys.stderr)
        return 2
    d = post('/eval', {'state': args.state, 'code': code, 'wait': 4.0}, base)
    print('ok:', d.get('ok'))
    if d.get('error'):
        print('error:', d['error'])
    for line in d.get('raw') or []:
        print(line)
    for line in d.get('lines') or []:
        print(line)
    return 0 if d.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
