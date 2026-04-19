"""SQLite 数据库操作模块 v3.0"""
import sqlite3
import logging
import os
import json
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "hotspot.db"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 启用WAL模式，提高并发读写性能
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=2000")
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
                tags        TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON hotspots(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON hotspots(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON hotspots(category)")
        # 复合索引：常用查询 WHERE date=? AND source=?
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date_source ON hotspots(date, source)")
        # 复合索引：近7天查询
        conn.execute("CREATE INDEX IF NOT EXISTS idx_date_rank ON hotspots(date, rank)")

        # 兼容旧表：自动添加新字段
        for col, default in [
            ("summary", "TEXT DEFAULT ''"),
            ("keywords", "TEXT DEFAULT ''"),
            ("tags", "TEXT DEFAULT ''"),
        ]:
            try:
                conn.execute(f"ALTER TABLE hotspots ADD COLUMN {col} {default}")
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
            """INSERT INTO hotspots (date, rank, title, hot_value, source, category, url, summary, keywords, tags)
               VALUES (:date, :rank, :title, :hot_value, :source, :category, :url, :summary, :keywords, :tags)""",
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


def get_hotspots_by_date(date_str: str, source: str = None, tag: str = None) -> list:
    """按日期查询热点列表，可选按平台和标签筛选"""
    conn = get_connection()
    try:
        query = "SELECT * FROM hotspots WHERE date = ?"
        params = [date_str]

        if source and source != "all":
            query += " AND source = ?"
            params.append(source)

        if tag and tag != "全部":
            # tags字段存储为JSON数组字符串，用LIKE匹配
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        query += " ORDER BY rank ASC"
        rows = conn.execute(query, params).fetchall()
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


def get_hotspots_by_date_range(start_date: str, end_date: str, source: str = None, tag: str = None) -> list:
    """按日期范围查询热点列表（单次SQL代替多次查询）"""
    conn = get_connection()
    try:
        query = "SELECT * FROM hotspots WHERE date BETWEEN ? AND ?"
        params = [start_date, end_date]

        if source and source != "all":
            query += " AND source = ?"
            params.append(source)

        if tag and tag != "全部":
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        query += " ORDER BY date DESC, rank ASC"
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
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


def get_available_sources(date_str: str) -> list:
    """获取指定日期有哪些平台的数据"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT source FROM hotspots WHERE date = ? ORDER BY source",
            (date_str,)
        ).fetchall()
        return [row["source"] for row in rows]
    finally:
        conn.close()


def get_available_tags(date_str: str) -> list:
    """获取指定日期所有可用的标签"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT tags FROM hotspots WHERE date = ? AND tags != ''",
            (date_str,)
        ).fetchall()
        all_tags = set()
        for row in rows:
            try:
                tags = json.loads(row["tags"]) if row["tags"] else []
                all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass
        return sorted(all_tags)
    finally:
        conn.close()


def cleanup_old_data(days: int = 7):
    """清理指定天数之前的旧数据，保留最近 N 天"""
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM hotspots WHERE date < ?", (cutoff,))
        conn.commit()
        if cursor.rowcount > 0:
            logger.info(f"已清理 {cutoff} 之前的 {cursor.rowcount} 条旧数据")
    except Exception as e:
        conn.rollback()
        logger.error(f"清理旧数据失败: {e}")
    finally:
        conn.close()


def get_stats() -> dict:
    """获取数据库统计信息"""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) as cnt FROM hotspots").fetchone()["cnt"]
        dates = conn.execute("SELECT COUNT(DISTINCT date) as cnt FROM hotspots").fetchone()["cnt"]
        latest = conn.execute("SELECT MAX(created_at) as t FROM hotspots").fetchone()["t"]
        sources = conn.execute("SELECT COUNT(DISTINCT source) as cnt FROM hotspots").fetchone()["cnt"]
        return {"total_records": total, "total_dates": dates, "total_sources": sources, "last_updated": latest}
    finally:
        conn.close()



