"""Flask 主应用"""
import logging
import os
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

from models.database import init_db, upsert_hotspots, get_hotspots_by_date, get_available_dates, get_stats, cleanup_old_data
from scraper.merger import merge_and_rank

# ── 版本号 ─────────────────────────────────────────
def get_app_version():
    """读取版本号文件"""
    try:
        version_path = os.path.join(os.path.dirname(__file__), "版本号.txt")
        with open(version_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return "unknown"

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
CORS(app)  # 允许跨域访问


# ── 定时任务：抓取并存储热点 ──────────────────────
def scheduled_fetch():
    """定时抓取任务：每小时执行一次"""
    today = date.today().strftime("%Y-%m-%d")
    logger.info(f"[定时任务] 开始抓取 {today} 热点...")
    try:
        items = merge_and_rank(limit=30)
        if items:
            upsert_hotspots(today, items)
            logger.info(f"[定时任务] 抓取完成，共 {len(items)} 条")
        else:
            logger.warning("[定时任务] 抓取结果为空，跳过写入")
    except Exception as e:
        logger.error(f"[定时任务] 抓取失败: {e}")
    # 清理7天前的旧数据（保留今天+前6天）
    try:
        cleanup_old_data(days=7)
    except Exception as e:
        logger.error(f"[定时任务] 清理旧数据失败: {e}")


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
            fresh = merge_and_rank(limit=30)
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


@app.route("/api/version")
def api_version():
    """获取当前版本号，供前端检测更新"""
    return jsonify({
        "version": get_app_version(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    """手动触发刷新（管理用，需密码验证）"""
    # 密码验证
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "2005")
    try:
        data = request.get_json(silent=True) or {}
        password = data.get("password", "")
        if password != ADMIN_PASSWORD:
            return jsonify({"status": "error", "message": "密码错误"}), 403
    except Exception:
        return jsonify({"status": "error", "message": "验证失败"}), 403

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
app = application  # 兼容 Gunicorn 默认查找 app 变量

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
