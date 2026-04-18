"""百度热搜抓取模块"""
import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

BAIDU_HOT_URL = "https://top.baidu.com/board?tab=realtime"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.baidu.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

CATEGORY_KEYWORDS = {
    "娱乐": ["明星", "综艺", "电影", "音乐", "演员", "偶像", "演唱会", "影视", "剧", "歌", "选秀", "直播"],
    "体育": ["足球", "篮球", "奥运", "冠军", "世界杯", "比赛", "赛事", "运动员", "乒乓", "羽毛球", "网球"],
    "财经": ["股市", "基金", "经济", "财经", "上涨", "下跌", "A股", "港股", "美股", "央行", "楼市", "房价"],
    "科技": ["苹果", "华为", "小米", "特斯拉", "人工智能", "AI", "芯片", "手机", "互联网", "科技", "GPT"],
    "社会": ["事故", "救援", "失踪", "罕见", "暖心", "感动", "爱心", "公益", "志愿"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "制裁", "战争", "国际", "联合国"],
    "健康": ["疫情", "医院", "疾病", "健康", "医疗", "药品", "养生", "心理", "癌症"],
}


def classify_category(title: str) -> str:
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                return cat
    return "热点"


def parse_hot_value(text: str) -> int:
    """解析热度值，如 '1234万' -> 12340000"""
    if not text:
        return 0
    text = text.strip().replace(",", "")
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


def fetch_baidu_hot() -> list:
    """抓取百度热搜榜，返回标准化热点列表"""
    try:
        resp = requests.get(BAIDU_HOT_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        result = []
        rank = 1

        # 新版百度热搜页面结构
        items = soup.select("div.category-wrap_iQLoo") or soup.select("div[class*='category-wrap']")

        if not items:
            # 备用选择器
            items = soup.find_all("div", class_=re.compile(r"category-wrap|item-wrap"))

        for item in items:
            title_el = item.select_one(".c-single-text-ellipsis") or item.select_one("[class*='title']")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title:
                continue

            hot_el = item.select_one(".hot-index_1Bl1a") or item.select_one("[class*='hot-index']") or item.select_one("[class*='num']")
            hot_value = parse_hot_value(hot_el.get_text(strip=True) if hot_el else "0")

            link_el = item.find("a", href=True)
            url = link_el["href"] if link_el else f"https://www.baidu.com/s?wd={requests.utils.quote(title)}"
            if url.startswith("/"):
                url = "https://top.baidu.com" + url

            result.append({
                "rank": rank,
                "title": title,
                "hot_value": hot_value,
                "source": "baidu",
                "category": classify_category(title),
                "url": url,
            })
            rank += 1
            if rank > 25:
                break

        logger.info(f"百度热搜抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"百度热搜抓取失败: {e}")
        return []
