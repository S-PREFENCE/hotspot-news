"""Flask 主应用"""
import logging
import os
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, render_template, request, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

from models.database import init_db, upsert_hotspots, get_hotspots_by_date, get_available_dates, get_stats
from scraper.merger import merge_and_rank

# ── 日志配置 ──────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Flask App ─────────────────────────────────────
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 确保中文不转义


# ── 定时任务：抓取并存储热点 ──────────────────────
def scheduled_fetch():
    """定时抓取任务：每小时执行一次"""
    today = date.today().strftime("%Y-%m-%d")
    logger.info(f"[定时任务] 开始抓取 {today} 热点...")
    try:
        items = merge_and_rank(limit=20)
        if items:
            upsert_hotspots(today, items)
            logger.info(f"[定时任务] 抓取完成，共 {len(items)} 条")
        else:
            logger.warning("[定时任务] 抓取结果为空，跳过写入")
    except Exception as e:
        logger.error(f"[定时任务] 抓取失败: {e}")


# ── 路由 ──────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/hotspots")
def api_hotspots():
    """
    获取指定日期热点
    参数: ?date=YYYY-MM-DD 或 ?date=today 或 ?date=yesterday
    """
    date_param = request.args.get("date", "today")
    today = date.today()

    if date_param == "today":
        target_date = today.strftime("%Y-%m-%d")
    elif date_param == "yesterday":
        target_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = date_param

    items = get_hotspots_by_date(target_date)

    # 如果当天没有数据，立即触发一次抓取
    if not items and date_param in ("today", target_date):
        logger.info(f"[API] {target_date} 无缓存，立即抓取...")
        try:
            fresh = merge_and_rank(limit=20)
            if fresh:
                upsert_hotspots(target_date, fresh)
                items = get_hotspots_by_date(target_date)
        except Exception as e:
            logger.error(f"[API] 即时抓取失败: {e}")

    return jsonify({
        "date": target_date,
        "count": len(items),
        "items": items,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/dates")
def api_dates():
    """获取有数据的日期列表"""
    dates = get_available_dates(limit=7)
    return jsonify({"dates": dates})


@app.route("/api/stats")
def api_stats():
    """获取数据统计信息"""
    return jsonify(get_stats())


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """手动触发刷新（管理用）"""
    try:
        scheduled_fetch()
        return jsonify({"status": "ok", "message": "刷新成功"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── PWA 路由 ──────────────────────────────────────
@app.route("/sw.js")
def service_worker():
    """Service Worker 文件"""
    return send_from_directory(os.path.join(app.root_path, "static"), "sw.js",
                               mimetype="application/javascript")


@app.route("/manifest.json")
def manifest():
    """PWA manifest 文件"""
    return send_from_directory(os.path.join(app.root_path, "static"), "manifest.json",
                               mimetype="application/json")


# ── 启动初始化 ────────────────────────────────────
def create_app():
    # 初始化数据库
    init_db()

    # 启动时立即抓取一次
    scheduled_fetch()

    # 配置定时任务（每小时抓取一次）
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        func=scheduled_fetch,
        trigger=IntervalTrigger(hours=1),
        id="fetch_hotspots",
        name="每小时抓取热点",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("定时任务已启动，每小时抓取一次热点")

    # 程序退出时关闭 scheduler
    atexit.register(lambda: scheduler.shutdown())

    return app


# ── 入口 ──────────────────────────────────────────
application = create_app()

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
