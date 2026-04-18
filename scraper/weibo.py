"""微博热搜抓取模块"""
import requests
import logging

logger = logging.getLogger(__name__)

WEIBO_HOT_URL = "https://weibo.com/ajax/side/hotSearch"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://weibo.com/",
    "Accept": "application/json, text/plain, */*",
}

CATEGORY_KEYWORDS = {
    "娱乐": ["明星", "综艺", "电影", "音乐", "演员", "偶像", "演唱会", "影视", "剧", "歌", "选秀", "直播", "抖音", "网红"],
    "体育": ["足球", "篮球", "奥运", "冠军", "世界杯", "比赛", "赛事", "运动员", "乒乓", "羽毛球", "网球", "nba", "cba"],
    "财经": ["股市", "基金", "经济", "财经", "上涨", "下跌", "A股", "港股", "美股", "央行", "楼市", "房价", "通胀", "利率"],
    "科技": ["苹果", "华为", "小米", "特斯拉", "人工智能", "AI", "芯片", "手机", "互联网", "科技", "GPT", "数字", "卫星"],
    "社会": ["事故", "救援", "失踪", "罕见", "暖心", "感动", "爱心", "公益", "志愿", "社会"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "台湾", "外交", "制裁", "战争", "国际", "联合国", "峰会"],
    "健康": ["疫情", "医院", "疾病", "健康", "医疗", "药品", "养生", "心理", "癌症", "病毒"],
}


def classify_category(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "热点"


def fetch_weibo_hot() -> list:
    """抓取微博热搜榜，返回标准化热点列表"""
    try:
        resp = requests.get(WEIBO_HOT_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("realtime", [])
        result = []
        rank = 1
        for item in items:
            if item.get("is_ad"):
                continue
            title = item.get("word", "").strip()
            if not title:
                continue
            hot_value = item.get("num", 0)
            try:
                hot_value = int(hot_value)
            except (ValueError, TypeError):
                hot_value = 0
            url = f"https://s.weibo.com/weibo?q=%23{requests.utils.quote(title)}%23"
            result.append({
                "rank": rank,
                "title": title,
                "hot_value": hot_value,
                "source": "weibo",
                "category": classify_category(title),
                "url": url,
            })
            rank += 1
            if rank > 25:
                break
        logger.info(f"微博热搜抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"微博热搜抓取失败: {e}")
        return []
