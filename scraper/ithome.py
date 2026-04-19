"""IT之家热点抓取模块（替代虎嗅）"""
import requests
import logging

logger = logging.getLogger(__name__)

# IT之家新闻列表API（无需认证）
ITHOME_API_URL = "https://api.ithome.com/json/newslist/news"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.ithome.com/",
    "Accept": "application/json",
}

CATEGORY_KEYWORDS = {
    "科技": ["AI", "芯片", "手机", "苹果", "华为", "小米", "特斯拉", "5G",
             "大模型", "GPT", "互联网", "开源", "软件", "硬件", "科技",
             "数码", "测评", "自动驾驶", "新能源", "半导体", "量子", "机器人"],
    "财经": ["股票", "基金", "A股", "上市", "融资", "市值", "营收", "利润",
             "央行", "利率", "经济", "金融", "投资", "国补", "补贴"],
    "娱乐": ["明星", "综艺", "电影", "游戏", "直播", "动漫", "番剧", "演唱"],
    "体育": ["比赛", "冠军", "足球", "篮球", "奥运", "赛事", "运动"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "国际",
             "制裁", "联合国", "中东", "关税", "特朗普", "欧盟"],
    "社会": ["事故", "救援", "诈骗", "犯罪", "政策", "民生"],
    "健康": ["健康", "医疗", "疫情", "疾病", "药品"],
    "教育": ["高考", "考研", "教育", "学校", "大学"],
}


def classify_category(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "科技"  # IT之家默认科技


def fetch_ithome_hot() -> list:
    """抓取IT之家热点新闻，返回标准化热点列表"""
    try:
        params = {"r": "0"}
        resp = requests.get(ITHOME_API_URL, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("newslist", [])
        if not items:
            return []

        result = []
        seen = set()
        rank = 1

        for item in items[:25]:
            title = item.get("title", "").strip()
            if not title or title in seen:
                continue
            seen.add(title)

            hot_value = item.get("hitcount", 0) or item.get("commentcount", 0) or 0
            try:
                hot_value = int(hot_value)
            except (ValueError, TypeError):
                hot_value = 0

            url = item.get("url", "")
            if not url and item.get("newsid"):
                url = f"https://www.ithome.com/0/{item['newsid']}.htm"

            result.append({
                "rank": rank,
                "title": title,
                "hot_value": hot_value,
                "source": "ithome",
                "category": classify_category(title),
                "url": url or "#",
            })
            rank += 1

        logger.info(f"IT之家热点抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"IT之家热点抓取失败: {e}")
        return []
