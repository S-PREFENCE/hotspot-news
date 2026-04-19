"""虎嗅热门文章抓取模块"""
import requests
import logging
import re
import json

logger = logging.getLogger(__name__)

# 虎嗅首页（HTML解析）
HUXIU_URL = "https://www.huxiu.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.huxiu.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

CATEGORY_KEYWORDS = {
    "科技": ["AI", "人工智能", "芯片", "手机", "苹果", "华为", "小米", "特斯拉", "自动驾驶", "5G",
             "量子", "机器人", "大模型", "GPT", "互联网", "算法", "开源", "软件", "硬件", "科技",
             "数字化", "元宇宙", "新能源", "电动车"],
    "财经": ["股票", "基金", "A股", "港股", "美股", "上市", "融资", "并购", "市值", "营收", "利润",
             "GDP", "央行", "利率", "经济", "金融", "投资", "创业", "破产", "裁员", "房价", "股市"],
    "娱乐": ["明星", "综艺", "电影", "音乐", "游戏", "直播", "网红", "短剧"],
    "体育": ["比赛", "冠军", "足球", "篮球", "奥运", "体育", "赛事"],
    "教育": ["高考", "考研", "教育", "学校", "大学", "培训"],
    "社会": ["社会", "事故", "犯罪", "诈骗", "案件", "政策", "民生"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "外交", "国际", "制裁", "战争"],
    "健康": ["健康", "医疗", "疫情", "疾病"],
}


def classify_category(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "热点"


def fetch_huxiu_hot() -> list:
    """抓取虎嗅热门文章，通过HTML解析"""
    try:
        resp = requests.get(HUXIU_URL, headers=HEADERS, timeout=12)
        resp.raise_for_status()

        result = []
        seen = set()
        rank = 1

        # 尝试从页面内嵌JSON中提取数据
        json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', resp.text, re.S)
        if json_match:
            try:
                page_data = json.loads(json_match.group(1))
                articles = page_data.get("articleList", page_data.get("topList", []))
                if isinstance(articles, dict):
                    articles = articles.get("dataList", articles.get("list", []))
                for item in articles[:20]:
                    title = item.get("title", "").strip()
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    aid = item.get("aid", item.get("id", ""))
                    url = f"https://www.huxiu.com/article/{aid}.html" if aid else "#"
                    hot_value = item.get("count_click", 0) or item.get("views", 0) or 0
                    try:
                        hot_value = int(hot_value)
                    except:
                        hot_value = 0
                    result.append({
                        "rank": rank, "title": title, "hot_value": hot_value,
                        "source": "huxiu", "category": classify_category(title), "url": url,
                    })
                    rank += 1
            except (json.JSONDecodeError, AttributeError):
                pass

        # 如果JSON方式没拿到数据，用HTML解析
        if not result:
            # 匹配文章链接和标题
            items = re.findall(r'<a[^>]*href="/article/(\d+)\.html"[^>]*>([\u4e00-\u9fff][^<]{4,80})</a>', resp.text)
            for aid, title in items[:20]:
                title = title.strip()
                if not title or title in seen:
                    continue
                seen.add(title)
                url = f"https://www.huxiu.com/article/{aid}.html"
                result.append({
                    "rank": rank, "title": title, "hot_value": 500 - rank * 20,
                    "source": "huxiu", "category": classify_category(title), "url": url,
                })
                rank += 1

        logger.info(f"虎嗅热门抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"虎嗅热门抓取失败: {e}")
        return []
