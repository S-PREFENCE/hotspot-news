"""快手热榜抓取模块"""
import requests
import logging
import re

logger = logging.getLogger(__name__)

# 快手 GraphQL API（免费、无需认证、稳定）
KUAISHOU_GRAPHQL_URL = "https://www.kuaishou.com/graphql"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.kuaishou.com/",
    "Accept": "application/json",
    "Content-Type": "application/json",
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


def fetch_kuaishou_hot() -> list:
    """通过快手GraphQL API抓取热榜，返回标准化热点列表"""
    try:
        payload = {
            "operationName": "visionHotRank",
            "query": 'query visionHotRank($page: String) { visionHotRank(page: $page) { items { rank name hotValue iconUrl } } }',
            "variables": {"page": "1"},
        }
        resp = requests.post(
            KUAISHOU_GRAPHQL_URL,
            json=payload,
            headers=HEADERS,
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()

        items = (
            data.get("data", {})
                 .get("visionHotRank", {})
                 .get("items", [])
        )
        if not items:
            logger.warning("快手GraphQL返回空数据")
            return []

        result = []
        for i, item in enumerate(items[:25], 1):
            title = item.get("name", "").strip()
            if not title:
                continue

            hot_str = item.get("hotValue", "0")
            hot_value = parse_hot_value(hot_str)

            url = f"https://www.kuaishou.com/search/video?searchKey={requests.utils.quote(title)}"

            result.append({
                "rank": i,
                "title": title,
                "hot_value": hot_value,
                "source": "kuaishou",
                "category": classify_category(title),
                "url": url,
            })

        logger.info(f"快手热榜抓取成功(GraphQL)，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"快手热榜抓取失败: {e}")
        return []
