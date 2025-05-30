import os
import socket
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

def get_db_connection():
    # 确定当前环境和配置文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    default_env_path = os.path.join(current_dir, '.env')
    
    # 加载默认环境配置
    load_dotenv(default_env_path)
    
    # 无论内网还是公网，都使用相同的数据库连接配置
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        cursor_factory=RealDictCursor,
        connect_timeout=5  # 5秒超时
    )
    return conn
