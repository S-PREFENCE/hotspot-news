"""B站热门视频抓取模块"""
import requests
import logging

logger = logging.getLogger(__name__)

# B站热门视频API（无需认证）
BILIBILI_API_URL = "https://api.bilibili.com/x/web-interface/popular"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json",
}

CATEGORY_KEYWORDS = {
    "娱乐": ["明星", "综艺", "电影", "音乐", "演员", "偶像", "演唱会", "影视", "剧", "歌", "选秀", "直播", "网红", "番剧", "动漫"],
    "体育": ["足球", "篮球", "奥运", "冠军", "世界杯", "比赛", "赛事", "运动员", "乒乓", "羽毛球", "网球", "nba", "cba", "电竞"],
    "财经": ["股市", "基金", "经济", "财经", "上涨", "下跌", "A股", "港股", "美股", "央行", "楼市", "房价"],
    "科技": ["苹果", "华为", "小米", "特斯拉", "人工智能", "AI", "芯片", "手机", "互联网", "科技", "GPT", "数码", "测评"],
    "社会": ["事故", "救援", "失踪", "罕见", "暖心", "感动", "爱心", "公益", "志愿"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "制裁", "战争", "国际", "联合国"],
    "健康": ["疫情", "医院", "疾病", "健康", "医疗", "药品", "养生", "心理", "癌症", "病毒"],
    "教育": ["高考", "考研", "双减", "留学", "教师", "学位", "大学", "课程", "学习"],
}


def classify_category(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "热点"


def fetch_bilibili_hot() -> list:
    """抓取B站热门视频，返回标准化热点列表"""
    try:
        params = {"ps": 30, "pn": 1}
        resp = requests.get(BILIBILI_API_URL, headers=HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            logger.warning(f"B站API返回错误: {data.get('message')}")
            return []

        items = data.get("data", {}).get("list", [])
        if not items:
            return []

        result = []
        for i, item in enumerate(items[:25], 1):
            title = item.get("title", "").strip()
            if not title:
                continue

            # B站热度用stat.view播放量
            hot_value = item.get("stat", {}).get("view", 0)
            try:
                hot_value = int(hot_value)
            except (ValueError, TypeError):
                hot_value = 0

            bvid = item.get("bvid", "")
            url = f"https://www.bilibili.com/video/{bvid}" if bvid else "#"

            # 用owner.name作为额外信息
            owner = item.get("owner", {}).get("name", "")

            result.append({
                "rank": i,
                "title": title,
                "hot_value": hot_value,
                "source": "bilibili",
                "category": classify_category(title),
                "url": url,
            })

        logger.info(f"B站热门抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"B站热门抓取失败: {e}")
        return []
