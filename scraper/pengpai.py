"""澎湃新闻热点抓取模块（替代国际头条）"""
import requests
import logging

logger = logging.getLogger(__name__)

# 澎湃新闻右侧栏热门API
PENGPAI_API_URL = "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.thepaper.cn/",
    "Accept": "application/json",
}

CATEGORY_KEYWORDS = {
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "国际",
             "制裁", "战争", "联合国", "G7", "北约", "中东", "导弹",
             "冲突", "特朗普", "欧盟", "峰会", "伊朗", "乌克兰"],
    "财经": ["A股", "港股", "美股", "基金", "利率", "央行", "经济",
             "GDP", "上市", "市值", "关税", "贸易", "银行"],
    "科技": ["AI", "芯片", "5G", "人工智能", "大模型", "华为", "苹果",
             "手机", "互联网", "科技", "新能源", "半导体"],
    "社会": ["事故", "救援", "诈骗", "犯罪", "政策", "民生", "执法",
             "监管", "交通", "医疗", "教育"],
    "娱乐": ["明星", "综艺", "电影", "音乐", "游戏", "直播"],
    "体育": ["比赛", "冠军", "足球", "篮球", "奥运", "赛事"],
}


def classify_category(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "热点"


def fetch_pengpai_hot() -> list:
    """抓取澎湃新闻热门列表，返回标准化热点列表"""
    try:
        resp = requests.get(PENGPAI_API_URL, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        data = resp.json()

        hot_news = data.get("data", {}).get("hotNews", [])
        if not hot_news:
            logger.warning("澎湃新闻API返回空数据")
            return []

        result = []
        seen = set()
        rank = 1

        for item in hot_news[:25]:
            title = item.get("name", "").strip()
            if not title or title in seen:
                continue
            seen.add(title)

            hot_value = item.get("praiseTimes", 0) or item.get("commentCount", 0) or 0
            try:
                hot_value = int(hot_value)
            except (ValueError, TypeError):
                hot_value = 0

            # 构建URL
            cont_id = item.get("contId", item.get("contid", ""))
            url = f"https://www.thepaper.cn/newsDetail_cont_{cont_id}" if cont_id else "#"

            result.append({
                "rank": rank,
                "title": title,
                "hot_value": hot_value if hot_value > 0 else 900 - rank * 30,
                "source": "pengpai",
                "category": classify_category(title),
                "url": url,
            })
            rank += 1

        logger.info(f"澎湃新闻热点抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"澎湃新闻热点抓取失败: {e}")
        return []
