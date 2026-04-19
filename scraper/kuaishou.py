"""快手热榜抓取模块 v3 — 多通道容错（含头条降级）
通道1: 快手PC GraphQL（国内优先）
通道2: 快手APP GraphQL（海外友好）
通道3: 快手完整头 GraphQL
通道4: 今日头条热榜（终极降级，海外可用）
"""
import requests
import logging
import re
import json

logger = logging.getLogger(__name__)

# ── 快手 API ──────────────────────────────────────
KUAISHOU_GRAPHQL_URL = "https://www.kuaishou.com/graphql"

HEADERS_PC = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.kuaishou.com/",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

HEADERS_APP = {
    "User-Agent": "kwai-android",
    "Content-Type": "application/json",
    "Accept": "*/*",
}

# ── 今日头条 API（终极降级通道）──────────────────
TOUTIAO_API_URL = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"

HEADERS_TOUTIAO = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.toutiao.com/",
    "Accept": "application/json",
}

CATEGORY_KEYWORDS = {
    "娱乐": ["明星", "综艺", "电影", "音乐", "演员", "偶像", "演唱会", "影视", "剧", "歌", "选秀", "直播", "网红"],
    "体育": ["足球", "篮球", "奥运", "冠军", "世界杯", "比赛", "赛事", "运动员", "乒乓", "羽毛球", "网球", "nba", "cba"],
    "财经": ["股市", "基金", "经济", "财经", "上涨", "下跌", "A股", "港股", "美股", "央行", "楼市", "房价", "通胀"],
    "科技": ["苹果", "华为", "小米", "特斯拉", "人工智能", "AI", "芯片", "手机", "互联网", "科技", "GPT", "数字"],
    "社会": ["事故", "救援", "失踪", "罕见", "暖心", "感动", "爱心", "公益", "志愿", "社会"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "制裁", "战争", "国际", "联合国"],
    "健康": ["疫情", "医院", "疾病", "健康", "医疗", "药品", "养生", "心理", "癌症", "病毒"],
}


def classify_category(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "热点"


def parse_hot_value(text) -> int:
    """解析热度值，如 '1344.9万' -> 13449000"""
    if not text:
        return 0
    text = str(text).strip().replace(",", "")
    match = re.search(r"([\d.]+)\s*(万|亿)?", text)
    if not match:
        return 0
    num = float(match.group(1))
    unit = match.group(2)
    if unit == "万":
        num *= 10000
    elif unit == "亿":
        num *= 100000000
    return int(num)


def _build_kuaishou_items(raw_items: list) -> list:
    """构建快手标准化热点列表"""
    result = []
    for i, item in enumerate(raw_items[:25], 1):
        title = item.get("name", "").strip()
        if not title:
            continue

        hot_raw = item.get("hotValue", "0")
        if isinstance(hot_raw, (int, float)):
            hot_value = int(hot_raw)
        else:
            hot_value = parse_hot_value(hot_raw)

        url = f"https://www.kuaishou.com/search/video?searchKey={requests.utils.quote(title)}"

        result.append({
            "rank": i,
            "title": title,
            "hot_value": hot_value,
            "source": "kuaishou",
            "category": classify_category(title),
            "url": url,
        })
    return result


def _build_toutiao_items(raw_items: list) -> list:
    """构建头条标准化热点列表（降级通道，source标记kuaishou以保持前端兼容）"""
    result = []
    for i, item in enumerate(raw_items[:25], 1):
        title = item.get("Title", "").strip()
        if not title:
            continue

        hot_value = item.get("HotValue", 0)
        try:
            hot_value = int(float(hot_value))
        except (ValueError, TypeError):
            hot_value = 0

        url = item.get("Url", "")
        if not url:
            cluster_id = item.get("ClusterId", "")
            url = f"https://www.toutiao.com/trending/{cluster_id}/" if cluster_id else "#"

        result.append({
            "rank": i,
            "title": title,
            "hot_value": hot_value,
            "source": "kuaishou",  # 保持前端兼容，仍标记为kuaishou
            "category": classify_category(title),
            "url": url,
        })
    return result


def _fetch_via_graphql_pc() -> list:
    """通道1：PC端GraphQL"""
    try:
        payload = {
            "operationName": "visionHotRank",
            "query": 'query visionHotRank($page: String) { visionHotRank(page: $page) { items { rank name hotValue iconUrl } } }',
            "variables": {"page": "1"},
        }
        resp = requests.post(
            KUAISHOU_GRAPHQL_URL,
            json=payload,
            headers=HEADERS_PC,
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        items = (
            data.get("data", {})
                 .get("visionHotRank", {})
                 .get("items", [])
        )
        if items:
            result = _build_kuaishou_items(items)
            logger.info(f"快手热榜抓取成功(PC GraphQL)，共 {len(result)} 条")
            return result
        logger.warning("快手PC GraphQL返回空数据")
        return []
    except Exception as e:
        logger.warning(f"快手PC GraphQL失败: {e}")
        return []


def _fetch_via_graphql_app() -> list:
    """通道2：APP端GraphQL（海外IP友好）"""
    try:
        payload = {
            "operationName": "visionHotRank",
            "query": 'query visionHotRank($page: String) { visionHotRank(page: $page) { items { rank name hotValue iconUrl } } }',
            "variables": {"page": "1"},
        }
        resp = requests.post(
            KUAISHOU_GRAPHQL_URL,
            json=payload,
            headers=HEADERS_APP,
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        items = (
            data.get("data", {})
                 .get("visionHotRank", {})
                 .get("items", [])
        )
        if items:
            result = _build_kuaishou_items(items)
            logger.info(f"快手热榜抓取成功(APP GraphQL)，共 {len(result)} 条")
            return result
        logger.warning("快手APP GraphQL返回空数据")
        return []
    except Exception as e:
        logger.warning(f"快手APP GraphQL失败: {e}")
        return []


def _fetch_via_graphql_full_headers() -> list:
    """通道3：带完整头的GraphQL"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.kuaishou.com/",
            "Origin": "https://www.kuaishou.com",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        payload = {
            "operationName": "visionHotRank",
            "query": 'query visionHotRank($page: String) { visionHotRank(page: $page) { items { rank name hotValue iconUrl } } }',
            "variables": {"page": "1"},
        }
        resp = requests.post(
            KUAISHOU_GRAPHQL_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        items = (
            data.get("data", {})
                 .get("visionHotRank", {})
                 .get("items", [])
        )
        if items:
            result = _build_kuaishou_items(items)
            logger.info(f"快手热榜抓取成功(完整头GraphQL)，共 {len(result)} 条")
            return result
        logger.warning("快手完整头GraphQL返回空数据")
        return []
    except Exception as e:
        logger.warning(f"快手完整头GraphQL失败: {e}")
        return []


def _fetch_via_toutiao() -> list:
    """通道4：今日头条热榜（终极降级，海外可用）"""
    try:
        resp = requests.get(
            TOUTIAO_API_URL,
            headers=HEADERS_TOUTIAO,
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        if items:
            result = _build_toutiao_items(items)
            logger.info(f"快手降级通道(今日头条)抓取成功，共 {len(result)} 条")
            return result
        logger.warning("今日头条API返回空数据")
        return []
    except Exception as e:
        logger.warning(f"今日头条降级通道失败: {e}")
        return []


def fetch_kuaishou_hot() -> list:
    """抓取快手热榜，4通道容错：
    1. PC GraphQL → 2. APP GraphQL → 3. 完整头GraphQL → 4. 今日头条降级
    """
    channels = [
        ("PC GraphQL", _fetch_via_graphql_pc),
        ("APP GraphQL", _fetch_via_graphql_app),
        ("完整头 GraphQL", _fetch_via_graphql_full_headers),
        ("今日头条降级", _fetch_via_toutiao),
    ]

    for name, func in channels:
        result = func()
        if result:
            return result
        logger.info(f"快手通道[{name}]失败，尝试下一通道...")

    logger.error("快手热榜全部通道失败")
    return []
