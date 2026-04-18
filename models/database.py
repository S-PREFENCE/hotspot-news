"""SQLite 数据库操作模块"""
import sqlite3
import logging
import os
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "hotspot.db"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库，创建表"""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hotspots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                rank        INTEGER NOT NULL,
                title       TEXT    NOT NULL,
                hot_value   INTEGER DEFAULT 0,
                source      TEXT    DEFAULT '',
                category    TEXT    DEFAULT '热点',
                url         TEXT    DEFAULT '',
                summary     TEXT    DEFAULT '',
                keywords    TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON hotspots(date)")

        # 兼容旧表：自动添加新字段
        try:
            conn.execute("ALTER TABLE hotspots ADD COLUMN summary TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE hotspots ADD COLUMN keywords TEXT DEFAULT ''")
        except Exception:
            pass

        conn.commit()
        logger.info("数据库初始化完成")
    finally:
        conn.close()


def upsert_hotspots(date_str: str, items: list):
    """
    插入或更新指定日期的热点数据
    date_str 格式: 'YYYY-MM-DD'
    """
    if not items:
        logger.warning(f"[{date_str}] 没有数据可写入")
        return
    conn = get_connection()
    try:
        # 删除当天旧数据，重新写入（保持最新快照）
        conn.execute("DELETE FROM hotspots WHERE date = ?", (date_str,))
        conn.executemany(
            """INSERT INTO hotspots (date, rank, title, hot_value, source, category, url, summary, keywords)
               VALUES (:date, :rank, :title, :hot_value, :source, :category, :url, :summary, :keywords)""",
            [{**item, "date": date_str} for item in items]
        )
        conn.commit()
        logger.info(f"[{date_str}] 写入 {len(items)} 条热点")
    except Exception as e:
        conn.rollback()
        logger.error(f"数据库写入失败: {e}")
        raise
    finally:
        conn.close()


def get_hotspots_by_date(date_str: str) -> list:
    """按日期查询热点列表"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM hotspots WHERE date = ? ORDER BY rank ASC",
            (date_str,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_available_dates(limit: int = 7) -> list:
    """获取有数据的日期列表（最近 N 天）"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT date FROM hotspots ORDER BY date DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [row["date"] for row in rows]
    finally:
        conn.close()


def get_stats() -> dict:
    """获取数据库统计信息"""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM hotspots").fetchone()["cnt"]
        dates = conn.execute("SELECT COUNT(DISTINCT date) as cnt FROM hotspots").fetchone()["cnt"]
        latest = conn.execute("SELECT MAX(created_at) as t FROM hotspots").fetchone()["t"]
        return {"total_records": total, "total_dates": dates, "last_updated": latest}
    finally:
        conn.close()
