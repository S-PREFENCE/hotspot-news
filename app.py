"""Flask 主应用 v3.0 - 智能多维热点热榜系统"""
import logging
import os
from datetime import datetime, date, timedelta
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

from models.database import init_db, upsert_hotspots, get_hotspots_by_date, get_available_dates, get_stats, cleanup_old_data, get_available_sources
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

# ── 平台配置（v3.0） ─────────────────────────────
PLATFORM_CONFIG = {
    "weibo":        {"label": "微博",     "color": "#E6162D", "enabled": True},
    "baidu":        {"label": "百度",     "color": "#4E6EF2", "enabled": True},
    "douyin":       {"label": "抖音",     "color": "#FE2C55", "enabled": True},
    "kuaishou":     {"label": "快手",     "color": "#FF4906", "enabled": True},
    "bilibili":     {"label": "B站",      "color": "#00A1D6", "enabled": True},
    "ithome":       {"label": "IT之家",   "color": "#D63031", "enabled": True},
    "sina_finance": {"label": "新浪财经", "color": "#F39C12", "enabled": True},
    "pengpai":      {"label": "澎湃新闻", "color": "#2ECC71", "enabled": True},
    # "zhihu":      {"label": "知乎",     "color": "#0084FF", "enabled": False},  # v3.0: 默认移除
}


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
          ?source=weibo  按平台筛选
          ?tag=AI        按标签筛选
    """
    date_param = request.args.get("date", "today")
    source = request.args.get("source", None)
    tag = request.args.get("tag", None)
    today = date.today()

    if date_param == "today":
        target_date = today.strftime("%Y-%m-%d")
    elif date_param == "yesterday":
        target_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    elif date_param == "day_before":
        target_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    elif date_param == "week":
        target_date = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    else:
        target_date = date_param

    # 如果是"近7天"模式，查询最近7天所有数据
    if date_param == "week":
        items = []
        for i in range(7):
            d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            day_items = get_hotspots_by_date(d, source=source, tag=tag)
            items.extend(day_items)
        # 按热度排序
        items.sort(key=lambda x: x.get("hot_value", 0), reverse=True)
    else:
        items = get_hotspots_by_date(target_date, source=source, tag=tag)

    # 如果当天没有数据，立即触发一次抓取
    if not items and date_param in ("today", target_date):
        logger.info(f"[API] {target_date} 无缓存，立即抓取...")
        try:
            fresh = merge_and_rank(limit=30)
            if fresh:
                upsert_hotspots(target_date, fresh)
                items = get_hotspots_by_date(target_date, source=source, tag=tag)
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


@app.route("/api/sources")
def api_sources():
    """获取平台配置列表"""
    return jsonify({"platforms": PLATFORM_CONFIG})


@app.route("/api/tags")
def api_tags():
    """获取指定日期可用的标签列表"""
    date_param = request.args.get("date", "today")
    today = date.today()
    if date_param == "today":
        target_date = today.strftime("%Y-%m-%d")
    elif date_param == "yesterday":
        target_date = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date = date_param
    from models.database import get_available_tags
    tags = get_available_tags(target_date)
    return jsonify({"tags": tags})


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
    """手动触发刷新"""
    try:
        scheduled_fetch()
        return jsonify({"status": "ok", "message": "刷新成功"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/debug/kuaishou")
def api_debug_kuaishou():
    """调试端点：测试快手各通道在当前服务器的可达性"""
    from scraper.kuaishou import (
        _fetch_via_graphql_pc, _fetch_via_graphql_app,
        _fetch_via_graphql_full_headers, _fetch_via_toutiao
    )
    results = {}
    for name, func in [
        ("pc_graphql", _fetch_via_graphql_pc),
        ("app_graphql", _fetch_via_graphql_app),
        ("full_headers_graphql", _fetch_via_graphql_full_headers),
        ("toutiao_fallback", _fetch_via_toutiao),
    ]:
        try:
            items = func()
            results[name] = {"status": "ok" if items else "empty", "count": len(items)}
        except Exception as e:
            results[name] = {"status": "error", "message": str(e)[:200]}
    return jsonify(results)


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
