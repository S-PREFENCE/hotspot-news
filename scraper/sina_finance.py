"""新浪财经7x24快讯抓取模块（替代财联社）"""
import requests
import logging
import re
import json

logger = logging.getLogger(__name__)

# 新浪财经7x24直播API
SINA_FINANCE_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/7x24/",
    "Accept": "application/json",
}

CATEGORY_KEYWORDS = {
    "财经": ["A股", "港股", "美股", "基金", "利率", "央行", "通胀", "经济", "GDP",
             "融资", "上市", "并购", "营收", "利润", "市值", "降息", "加息",
             "关税", "贸易", "银行", "保险", "证券", "期货", "黄金", "原油",
             "国债", "人民币", "美元", "指数"],
    "科技": ["AI", "芯片", "5G", "人工智能", "大模型", "算力", "新能源",
             "光伏", "锂电", "储能", "半导体", "自动驾驶"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "国际",
             "制裁", "战争", "联合国", "G7", "北约", "中东", "特朗普"],
    "社会": ["政策", "法规", "监管", "执法", "交通", "房地产", "住房", "就业"],
}


def classify_category(title: str, tags: list = None) -> str:
    """根据标题和标签分类"""
    # 优先看新浪自带的tag
    if tags:
        tag_names = [t.get("name", "") for t in tags if isinstance(t, dict)]
        for tag_name in tag_names:
            if tag_name in CATEGORY_KEYWORDS or tag_name in ["财经", "国际", "科技"]:
                return tag_name

    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "财经"  # 默认财经


def fetch_sina_finance_hot() -> list:
    """抓取新浪财经7x24快讯，返回标准化热点列表"""
    try:
        params = {
            "page": 1,
            "zhibo_id": 152,  # 财经7x24直播间
            "pagesize": 30,
            "direction": 0,
        }
        resp = requests.get(SINA_FINANCE_URL, headers=HEADERS, params=params, timeout=12)
        resp.raise_for_status()
        data = resp.json()

        feed_data = data.get("result", {}).get("data", {})
        feed_obj = feed_data.get("feed", {})
        feed_list = feed_obj.get("list", []) if isinstance(feed_obj, dict) else []
        if not feed_list:
            logger.warning("新浪财经API返回空列表")
            return []

        result = []
        seen = set()
        rank = 1

        for item in feed_list[:25]:
            # rich_text包含HTML标签，需要清理
            title = item.get("rich_text", "") or item.get("title", "")
            title = re.sub(r'<[^>]+>', '', title).strip()
            if not title or len(title) < 8:
                continue

            key = title[:15]
            if key in seen:
                continue
            seen.add(key)

            # 获取标签
            tags = item.get("tag", [])
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []

            docurl = item.get("docurl", "")
            if not docurl:
                docurl = f"https://finance.sina.com.cn/7x24/"

            result.append({
                "rank": rank,
                "title": title,
                "hot_value": 800 - rank * 25,  # 模拟热度（7x24无自然热度）
                "source": "sina_finance",
                "category": classify_category(title, tags),
                "url": docurl,
            })
            rank += 1

        logger.info(f"新浪财经快讯抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"新浪财经快讯抓取失败: {e}")
        return []
