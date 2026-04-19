"""国际头条抓取模块 - 参考消息 + 环球网"""
import requests
import logging
import re
import json

logger = logging.getLogger(__name__)

# 参考消息网（国内可访问的国际新闻）
CANKAO_URL = "https://www.cankaoxiaoxi.com/"

# 环球网国际频道
HUANQIU_URL = "https://world.huanqiu.com/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def _fetch_cankao() -> list:
    """通过参考消息网获取国际头条"""
    try:
        resp = requests.get(CANKAO_URL, headers=HEADERS, timeout=12)
        resp.raise_for_status()

        result = []
        seen = set()
        rank = 1

        # 匹配新闻标题
        items = re.findall(r'<a[^>]*href="([^"]*)"[^>]*title="([^"]{6,80})"', resp.text)
        for url, title in items[:20]:
            title = title.strip()
            if not title or len(title) < 6:
                continue
            key = title[:8]
            if key in seen:
                continue
            seen.add(key)

            if not url.startswith("http"):
                url = "https://www.cankaoxiaoxi.com" + url

            result.append({
                "rank": rank,
                "title": title,
                "hot_value": 900 - rank * 30,
                "source": "cankao",
                "category": "国际",
                "url": url,
            })
            rank += 1

        logger.info(f"参考消息抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"参考消息抓取失败: {e}")
        return []


def _fetch_huanqiu() -> list:
    """通过环球网国际频道获取头条"""
    try:
        resp = requests.get(HUANQIU_URL, headers=HEADERS, timeout=12)
        resp.raise_for_status()

        result = []
        seen = set()
        rank = 1

        # 匹配新闻标题
        items = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([\u4e00-\u9fff][\u4e00-\u9fff\w\s\uff0c\u3002\uff01\uff1f\u3001\uff1a\uff1b\u201c\u201d\uff08\uff09\u2014\u2026\d]{6,80})</a>', resp.text)

        for url, title in items[:20]:
            title = title.strip()
            if not title or len(title) < 6:
                continue
            key = title[:8]
            if key in seen:
                continue
            seen.add(key)

            if not url.startswith("http"):
                url = "https://world.huanqiu.com" + url

            result.append({
                "rank": rank,
                "title": title,
                "hot_value": 800 - rank * 25,
                "source": "huanqiu",
                "category": "国际",
                "url": url,
            })
            rank += 1

        logger.info(f"环球网抓取成功，共 {len(result)} 条")
        return result
    except Exception as e:
        logger.error(f"环球网抓取失败: {e}")
        return []


def fetch_international_hot() -> list:
    """抓取国际头条（参考消息 + 环球网合并），所有条目标记"国际"标签"""
    all_items = []

    cankao_items = _fetch_cankao()
    huanqiu_items = _fetch_huanqiu()

    all_items = cankao_items + huanqiu_items

    # 按模拟热度排序
    all_items.sort(key=lambda x: x["hot_value"], reverse=True)

    # 重新编号
    for i, item in enumerate(all_items, 1):
        item["rank"] = i

    # 强制添加"国际"标签
    for item in all_items:
        item["_force_tags"] = ["国际"]

    logger.info(f"国际头条合并后共 {len(all_items)} 条")
    return all_items[:25]
