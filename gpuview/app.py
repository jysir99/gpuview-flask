#!/usr/bin/env python

"""
Web API of gpuview.

@author Fitsum Gaim
@change Jysir
@url https://github.com/fgaim
"""
import os
import json
import sqlite3
import threading
import time
import mysql.connector
from datetime import datetime, timedelta
from flask import Flask, jsonify, send_file
from urllib.parse import urlparse
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
DB_TYPE = 'sqlite'  # 默认为sqlite
DB_URL = ''  # MySQL连接URL


def get_db_connection():
    if DB_TYPE == 'mysql':
        return mysql.connector.connect(**DB_URL)
    return sqlite3.connect(HOSTS_DB)


# ========== 数据库初始化 ==========
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    if DB_TYPE == 'mysql':
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpustats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allgpustats (
                id INT AUTO_INCREMENT PRIMARY KEY,
                data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpustats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS allgpustats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')
    conn.commit()
    conn.close()


# ========== 保存数据到数据库 ==========
def save_to_db(data, dbname):
    conn = get_db_connection()
    cursor = conn.cursor()
    if DB_TYPE == 'mysql':
        cursor.execute(f'INSERT INTO {dbname} (data) VALUES (%s)', (json.dumps(data, default=str),))
    else:
        cursor.execute(f'INSERT INTO {dbname} (data) VALUES (?)', (json.dumps(data, default=str),))
    conn.commit()
    conn.close()


# ========== 从数据库读取最新数据 ==========
def get_latest_from_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT data FROM gpustats ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def get_all_latest_from_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT data FROM allgpustats ORDER BY id DESC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


@app.route('/')
@app.route('/index')
def index():
    return send_file('views/index.html')


@app.route('/gpustat', methods=['GET'])
def report_gpustat():
    latest_data = get_latest_from_db()
    return jsonify(latest_data if latest_data else {})


# ========== 后台线程定期获取 GPU 状态 ==========
def background_gpustat_fetch():
    while True:
        gpustat = core.my_gpustat()
        save_to_db(gpustat, 'gpustats')
        print(f"Data fetched at {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}")
        time.sleep(2)  # 每 2 秒执行一次

def background_allgpustat_fetch():
    while True:
        hosts = core.load_hosts()
        gpustats = []
        for url in hosts:
            try:
                raw_resp = urlopen(url + '/gpustat')
                gpustat = json.loads(raw_resp.read())
                raw_resp.close()
                if 'gpus' in gpustat:
                    gpustats.append(gpustat)
            except Exception as e:
                print(f'Error: {str(e)} getting gpustat from {url}')
                continue

        save_to_db(gpustats, 'allgpustats')
        print(f"Data fetched at {datetime.now().strftime('%Y-%m-%d %H-%M-%S')}")
        time.sleep(2)  # 每 2 秒执行一次
        
def cleanup_old_data():
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()

        if DB_TYPE == 'mysql':
            cursor.execute("DELETE FROM gpustats WHERE created_at < NOW() - INTERVAL 3 DAY")
            cursor.execute("DELETE FROM allgpustats WHERE created_at < NOW() - INTERVAL 3 DAY")
        else:
            three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("DELETE FROM gpustats WHERE created_at < ?", (three_days_ago,))
            cursor.execute("DELETE FROM allgpustats WHERE created_at < ?", (three_days_ago,))

        conn.commit()
        conn.close()

        print(f"[{datetime.now()}] Completed cleanup, sleeping for 24 hours.")
        time.sleep(86400)  # 每 24 小时执行一次

@app.route('/all_gpustat', methods=['GET'])
def report_all_gpustat():
    gpustats = []
    now = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    mystat = get_latest_from_db()
    gpustats.append(mystat)
    allstat = get_all_latest_from_db()
    if len(allstat) > 0:
        gpustats = [mystat] + allstat
    return jsonify({'gpustats': sorted(gpustats, key=lambda g: g['hostname']), 'now': now})


# ========== 程序入口 ==========
def main():
    global DB_TYPE, DB_URL
    parser = utils.arg_parser()
    parser.add_argument('--db', type=str, default='sqlite', choices=['sqlite', 'mysql'], help='数据库类型')
    parser.add_argument('--db-url', type=str, help='MySQL 数据库连接字符串，例如：mysql://user:password@host/database')
    args = parser.parse_args()

    DB_TYPE = args.db
    if DB_TYPE == 'mysql' and args.db_url:
        parsed_url = urlparse(args.db_url)
        DB_URL = {
            'host': parsed_url.hostname,
            'user': parsed_url.username,
            'password': parsed_url.password,
            'database': parsed_url.path.lstrip('/')
        }
    
    init_db()
    threading.Thread(target=background_gpustat_fetch, daemon=True).start()
    threading.Thread(target=background_allgpustat_fetch, daemon=True).start()
    threading.Thread(target=cleanup_old_data, daemon=True).start()

    if args.action == 'run':
        core.safe_zone(args.safe_zone)
        app.run(host=args.host, port=args.port, debug=args.debug)
    elif args.action == 'service':
        core.install_service(host=args.host, port=args.port, safe_zone=args.safe_zone, exclude_self=args.exclude_self)
    elif args.action == 'add':
        core.add_host(args.url, args.name)
    elif args.action == 'remove':
        core.remove_host(args.url)
    elif args.action == 'hosts':
        core.print_hosts()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
