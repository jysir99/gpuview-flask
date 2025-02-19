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


app = Flask(__name__)

# === 配置数据库文件路径 ===
DB_FILE = 'gpustats.db'

# ========== 数据库初始化 ==========
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpustats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                data TEXT
            )
        ''')
        conn.commit()

# ========== 保存数据到数据库 ==========
def save_to_db(timestamp, data):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO gpustats (timestamp, data) VALUES (?, ?)', (timestamp,  json.dumps(data, default=str)))
        conn.commit()

# ========== 从数据库读取最新数据 ==========
def get_latest_from_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT timestamp, data FROM gpustats ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        if row:
            return {'now': row[0], 'gpustats': json.loads(row[1])}
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
    response = core.my_gpustat()
    return jsonify(response)


# ========== 后台线程定期获取 GPU 状态 ==========
def background_gpustats_fetch():
    while True:
        gpustats = core.all_gpustats()
        now = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        
        # 保存到数据库
        save_to_db(now, gpustats)

        print(f"Data fetched at {now}")
        time.sleep(2)  # 每 2 秒执行一次


# ========== 接口：读取最新数据 ==========
@app.route('/all_gpustat', methods=['GET'])
def report_all_gpustat():
    # 从数据库读取最新数据
    latest_data = get_latest_from_db()
    
    if latest_data:
        return jsonify(latest_data)
    else:
        return jsonify({'error': 'No data available'}), 404


# ========== 程序入口 ==========
def main():
    # 初始化数据库
    init_db()

    # 启动后台线程
    threading.Thread(target=background_gpustats_fetch, daemon=True).start()

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
