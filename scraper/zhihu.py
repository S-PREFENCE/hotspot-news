"""知乎热榜抓取模块"""
import requests
import logging

logger = logging.getLogger(__name__)

ZHIHU_HOT_URL = "https://www.zhihu.com/hot"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.zhihu.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

CATEGORY_KEYWORDS = {
    "科技": ["科技", "AI", "人工智能", "编程", "算法", "芯片", "手机", "互联网", "苹果", "华为", "小米", "GPT", "大模型"],
    "财经": ["经济", "股票", "基金", "投资", "楼市", "房价", "通胀", "央行", "A股", "美股", "创业", "融资"],
    "教育": ["高考", "大学", "考研", "留学", "教育", "学校", "学生", "老师", "培训"],
    "健康": ["健康", "医疗", "疾病", "心理", "减肥", "养生", "运动", "睡眠"],
    "社会": ["社会", "新闻", "事件", "案件", "法律", "政策", "民生", "公益"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "国际", "战争", "制裁"],
    "娱乐": ["娱乐", "明星", "电影", "综艺", "音乐", "游戏", "动漫"],
    "体育": ["体育", "足球", "篮球", "奥运", "比赛", "运动"],
}


def classify_category(title: str) -> str:
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                return cat
    return "热点"


def format_hot_value(val) -> int:
    """格式化知乎热度值"""
    try:
        return int(str(val).replace(",", "").replace("万", "0000"))
    except (ValueError, TypeError):
        return 0


def fetch_zhihu_hot() -> list:
    """抓取知乎热榜，返回标准化热点列表（通过 HTML 解析）"""
    import json, re as _re
    try:
        resp = requests.get(ZHIHU_HOT_URL, headers=HEADERS, timeout=12)
        resp.raise_for_status()

        # 知乎热榜页面中内嵌了 JSON 数据
        match = _re.search(r'<script id="js-initialData" type="text/json">(.*?)</script>', resp.text, _re.S)
        if not match:
            logger.warning("知乎页面未找到内嵌数据，跳过")
            return []

        page_data = json.loads(match.group(1))
        hot_list = (
            page_data.get("initialState", {})
                     .get("topstory", {})
                     .get("hotList", {})
                     .get("data", [])
        )

        result = []
        rank = 1
        for item in hot_list:
            t = item.get("target", {})
            title = t.get("titleArea", {}).get("text", "") or t.get("title", "")
            title = title.strip()
            if not title:
                continue
            hot_str = item.get("detailArea", {}).get("text", "") or item.get("excerptArea", {}).get("text", "")
            hot_value = format_hot_value(hot_str)
            url = t.get("link", {}).get("url", "") or f"https://www.zhihu.com/question/{t.get('id','')}"

            result.append({
                "rank": rank,
                "title": title,
                "hot_value": hot_value,
                "source": "zhihu",
                "category": classify_category(title),
                "url": url,
            })
            rank += 1
            if rank > 25:
                break

        logger.info(f"知乎热榜抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"知乎热榜抓取失败: {e}")
        return []
