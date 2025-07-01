import os
import socket
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

def get_db_connection():
    # 直接使用本地数据库配置
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="scan_db",
        user="fh",
        password="yb123456",
        cursor_factory=RealDictCursor,
        connect_timeout=5  # 5秒超时
    )
    return conn
