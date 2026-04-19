"""快手热榜抓取模块 v2 — 多通道容错"""
import requests
import logging
import re
import json

logger = logging.getLogger(__name__)

# 通道1：快手 GraphQL API（免费、无需认证）
KUAISHOU_GRAPHQL_URL = "https://www.kuaishou.com/graphql"

# 通道2：快手 APP 端 GraphQL（不同UA，海外IP友好）
KUAISHOU_GRAPHQL_URL_ALT = "https://www.kuaishou.com/graphql"

# 通道3：第三方热榜聚合API
THIRD_PARTY_APIS = [
    "https://api.cunyuapi.top/api/kshot",
]

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


def _build_standard_items(raw_items: list, title_key: str = "name", hot_key: str = "hotValue") -> list:
    """统一构建标准化热点列表"""
    result = []
    for i, item in enumerate(raw_items[:25], 1):
        title = item.get(title_key, "").strip()
        if not title:
            continue

        hot_raw = item.get(hot_key, "0")
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
            result = _build_standard_items(items)
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
            KUAISHOU_GRAPHQL_URL_ALT,
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
            result = _build_standard_items(items)
            logger.info(f"快手热榜抓取成功(APP GraphQL)，共 {len(result)} 条")
            return result
        logger.warning("快手APP GraphQL返回空数据")
        return []
    except Exception as e:
        logger.warning(f"快手APP GraphQL失败: {e}")
        return []


def _fetch_via_graphql_with_origin() -> list:
    """通道3：带Origin头的GraphQL（更完整请求模拟）"""
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
            result = _build_standard_items(items)
            logger.info(f"快手热榜抓取成功(完整头GraphQL)，共 {len(result)} 条")
            return result
        logger.warning("快手完整头GraphQL返回空数据")
        return []
    except Exception as e:
        logger.warning(f"快手完整头GraphQL失败: {e}")
        return []


def _fetch_via_third_party() -> list:
    """通道4：第三方聚合API"""
    for api_url in THIRD_PARTY_APIS:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            }
            resp = requests.get(api_url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # 兼容多种返回格式
            items = data.get("data", [])
            if not items and isinstance(data, list):
                items = data

            if items:
                # 检测字段名
                first = items[0]
                title_key = "name" if "name" in first else ("title" if "title" in first else "word")
                hot_key = "hotValue" if "hotValue" in first else ("hot" if "hot" in first else "hot_value")

                result = _build_standard_items(items, title_key=title_key, hot_key=hot_key)
                if result:
                    logger.info(f"快手热榜抓取成功(第三方API)，共 {len(result)} 条")
                    return result
        except Exception as e:
            logger.warning(f"快手第三方API({api_url})失败: {e}")
            continue
    return []


def fetch_kuaishou_hot() -> list:
    """抓取快手热榜，多通道容错：PC GraphQL → APP GraphQL → 完整头GraphQL → 第三方API"""
    channels = [
        ("PC GraphQL", _fetch_via_graphql_pc),
        ("APP GraphQL", _fetch_via_graphql_app),
        ("完整头 GraphQL", _fetch_via_graphql_with_origin),
        ("第三方API", _fetch_via_third_party),
    ]

    for name, func in channels:
        result = func()
        if result:
            return result
        logger.info(f"快手通道[{name}]失败，尝试下一通道...")

    logger.error("快手热榜全部通道失败")
    return []
