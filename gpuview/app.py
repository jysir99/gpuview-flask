#!/usr/bin/env python

"""
Web API of gpuview.

@author Fitsum Gaim
@change Jysir
@url https://github.com/fgaim
"""

import os
import json
from datetime import datetime
import sqlite3
import threading
import time
from datetime import datetime
# from bottle import Bottle, TEMPLATE_PATH, template, response, static_file
from flask import Flask, jsonify, render_template, send_file

from . import utils
from . import core

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
    
app = Flask(__name__)

# === 配置数据库文件路径 ===
ABS_PATH = os.path.dirname(os.path.realpath(__file__))
HOSTS_DB = os.path.join(ABS_PATH, 'mygpustat.db')

# ========== 数据库初始化 ==========
def init_db():
    with sqlite3.connect(HOSTS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpustats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT
            )
        ''')
        conn.commit()

# ========== 保存数据到数据库 ==========
def save_to_db(data):
    with sqlite3.connect(HOSTS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO gpustats (data) VALUES (?)', (json.dumps(data, default=str),))
        conn.commit()

# ========== 从数据库读取最新数据 ==========
def get_latest_from_db():
    with sqlite3.connect(HOSTS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM gpustats ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        # print(row)
        if row:
            return json.loads(row[0])
        return None


EXCLUDE_SELF = False  # Do not report to `/gpustat` calls.


@app.route('/')
@app.route('/index')
def index():
    return send_file('views/index.html')

@app.route('/gpustat', methods=['GET'])
def report_gpustat():
    """
    Returns the gpustat of this host.
        See `exclude-self` option of `gpuview run`.
    """
    
    latest_data = get_latest_from_db()
    
    if latest_data:
        return jsonify(latest_data)
    else:
        return jsonify({})


# ========== 后台线程定期获取 GPU 状态 ==========
def background_gpustat_fetch():
    while True:
        gpustat = core.my_gpustat()
        now = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        
        # 保存到数据库
        save_to_db(gpustat)

        print(f"Data fetched at {now}")
        time.sleep(2)  # 每 2 秒执行一次


# ========== 接口：读取最新数据 ==========
@app.route('/all_gpustat', methods=['GET'])
def report_all_gpustat():
    
    gpustats = []
    now = datetime.now().strftime('%Y-%m-%d %H-%M-%S')

    mystat = get_latest_from_db()
    if 'gpus' in mystat:
            gpustats.append(mystat)
    hosts = core.load_hosts()
    for url in hosts:
        try:
            raw_resp = urlopen(url + '/gpustat')
            gpustat = json.loads(raw_resp.read())
            raw_resp.close()
            if not gpustat or 'gpus' not in gpustat:
                continue
            if hosts[url] != url:
                gpustat['hostname'] = hosts[url]
            gpustats.append(gpustat)
        except Exception as e:
            print('Error: %s getting gpustat from %s' %
                  (getattr(e, 'message', str(e)), url))

    try:
        sorted_gpustats = sorted(gpustats, key=lambda g: g['hostname'])
        if sorted_gpustats is not None:
            return jsonify({'gpustats': sorted_gpustats, 'now': now})

    except Exception as e:
        print("Error: %s" % getattr(e, 'message', str(e)))

    return jsonify({'gpustats': gpustats, 'now': now})



# ========== 程序入口 ==========
def main():
    # 初始化数据库
    init_db()

    # 启动后台线程
    threading.Thread(target=background_gpustat_fetch, daemon=True).start()

    parser = utils.arg_parser()
    args = parser.parse_args()

    if 'run' == args.action:
        core.safe_zone(args.safe_zone)
        global EXCLUDE_SELF
        EXCLUDE_SELF = args.exclude_self
        app.run(host=args.host, port=args.port, debug=args.debug)
    elif 'service' == args.action:
        core.install_service(host=args.host,
                             port=args.port,
                             safe_zone=args.safe_zone,
                             exclude_self=args.exclude_self)
    elif 'add' == args.action:
        core.add_host(args.url, args.name)
    elif 'remove' == args.action:
        core.remove_host(args.url)
    elif 'hosts' == args.action:
        core.print_hosts()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
