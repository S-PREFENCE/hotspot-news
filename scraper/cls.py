"""财联社电报抓取模块"""
import requests
import logging
import json

logger = logging.getLogger(__name__)

# 财联社电报滚动API（POST方式）
CLS_ROLL_URL = "https://www.cls.cn/nodeapi/updateTelegraphList"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.cls.cn/telegraph",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.cls.cn",
}

CATEGORY_KEYWORDS = {
    "财经": ["A股", "港股", "美股", "基金", "利率", "央行", "通胀", "经济", "GDP", "融资",
             "上市", "并购", "营收", "利润", "市值", "降息", "加息", "关税", "贸易", "债",
             "银行", "保险", "证券", "期货", "黄金", "原油"],
    "科技": ["AI", "芯片", "5G", "量子", "人工智能", "大模型", "算力", "数字化", "新能源",
             "光伏", "锂电", "储能", "半导体", "自动驾驶"],
    "国际": ["美国", "俄罗斯", "欧洲", "日本", "韩国", "外交", "国际", "制裁", "战争",
             "联合国", "G7", "北约", "中东", "乌克兰"],
    "社会": ["政策", "法规", "监管", "执法", "交通", "房地产", "住房", "就业"],
}


def classify_category(title: str) -> str:
    title_lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in title_lower:
                return cat
    return "财经"


def fetch_cls_hot() -> list:
    """抓取财联社电报"""
    try:
        # 方法1：POST方式请求电报列表
        payload = {
            "app": "CailianpressWeb",
            "os": "web",
            "sv": "8.4.6",
            "refresh_type": 1,
        }
        resp = requests.post(CLS_ROLL_URL, headers=HEADERS, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("data", {}).get("roll_data", [])
        if not items:
            logger.warning("财联社API返回空数据")
            return []

        result = []
        seen = set()
        rank = 1
        for item in items[:25]:
            title = item.get("title", "") or item.get("content", "") or item.get("brief", "")
            title = title.strip()
            if not title or len(title) < 4:
                continue
            key = title[:10]
            if key in seen:
                continue
            seen.add(key)

            hot_value = item.get("score", 0) or 0
            try:
                hot_value = int(hot_value)
            except:
                hot_value = 0

            item_id = item.get("id", "")
            url = f"https://www.cls.cn/detail/{item_id}" if item_id else "#"

            result.append({
                "rank": rank, "title": title, "hot_value": hot_value,
                "source": "cls", "category": classify_category(title), "url": url,
            })
            rank += 1

        logger.info(f"财联社电报抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"财联社电报抓取失败: {e}")
        return []
