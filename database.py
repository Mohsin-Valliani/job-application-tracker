import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'job_tracker'),
    )

def query(sql, params=(), one=False):
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def execute(sql, params=()):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
