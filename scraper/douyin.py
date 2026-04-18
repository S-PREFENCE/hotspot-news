"""抖音热榜抓取模块"""
import requests
import logging
import re

logger = logging.getLogger(__name__)

# 主通道：第三方免费API（无需认证，稳定）
DOUYIN_API_URL = "https://v2.xxapi.cn/api/douyinhot"

# 备用通道：抖音官方接口（移动端UA）
DOUYIN_DIRECT_URL = "https://www.douyin.com/aweme/v1/web/hot/search/list/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                  "Mobile/15E148 Safari/604.1",
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
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


def fetch_douyin_hot() -> list:
    """抓取抖音热榜，返回标准化热点列表（双通道：第三方API + 官方接口）"""
    # 通道1：第三方免费API
    result = _fetch_via_xxapi()
    if result:
        return result

    # 通道2：抖音官方接口（备用）
    logger.info("第三方API失败，尝试抖音官方接口...")
    result = _fetch_via_direct()
    if result:
        return result

    logger.error("抖音热榜抓取全部失败")
    return []


def _fetch_via_xxapi() -> list:
    """通过第三方免费API获取抖音热榜"""
    try:
        resp = requests.get(DOUYIN_API_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            logger.warning(f"抖音API返回非200: {data.get('msg')}")
            return []

        items = data.get("data", [])
        if not items:
            return []

        result = []
        for i, item in enumerate(items[:25], 1):
            title = item.get("word", "").strip()
            if not title:
                continue
            hot_value = item.get("hot_value", 0)
            try:
                hot_value = int(hot_value)
            except (ValueError, TypeError):
                hot_value = 0

            # 构造抖音搜索链接
            url = f"https://www.douyin.com/search/{requests.utils.quote(title)}"

            result.append({
                "rank": i,
                "title": title,
                "hot_value": hot_value,
                "source": "douyin",
                "category": classify_category(title),
                "url": url,
            })

        logger.info(f"抖音热榜抓取成功(xxapi)，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"抖音热榜xxapi抓取失败: {e}")
        return []


def _fetch_via_direct() -> list:
    """通过抖音官方接口获取热榜（备用通道）"""
    try:
        params = {"device_platform": "webapp"}
        resp = requests.get(DOUYIN_DIRECT_URL, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        word_list = (
            data.get("data", {})
                 .get("word_list", [])
        )
        if not word_list:
            return []

        result = []
        for i, item in enumerate(word_list[:25], 1):
            title = item.get("word", "").strip()
            if not title:
                continue
            hot_value = item.get("hot_value", 0)
            try:
                hot_value = int(hot_value)
            except (ValueError, TypeError):
                hot_value = 0

            url = f"https://www.douyin.com/search/{requests.utils.quote(title)}"

            result.append({
                "rank": i,
                "title": title,
                "hot_value": hot_value,
                "source": "douyin",
                "category": classify_category(title),
                "url": url,
            })

        logger.info(f"抖音热榜抓取成功(官方接口)，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"抖音官方接口抓取失败: {e}")
        return []
