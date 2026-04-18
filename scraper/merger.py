"""多平台热点数据合并、去重、排序模块"""
import re
import logging
from .weibo import fetch_weibo_hot
from .baidu import fetch_baidu_hot
from .zhihu import fetch_zhihu_hot
from .summarizer import enrich_items_with_summary

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """标题归一化，用于去重比较"""
    title = re.sub(r"[#\s【】「」《》\[\]]", "", title)
    return title.lower()


def deduplicate(items: list) -> list:
    """去除标题高度相似的条目，优先保留热度更高的"""
    seen = {}
    for item in items:
        key = normalize_title(item["title"])
        # 截取前8个字符作为相似度 key
        short_key = key[:8] if len(key) >= 8 else key
        if short_key not in seen:
            seen[short_key] = item
        else:
            # 保留热度更高的
            if item["hot_value"] > seen[short_key]["hot_value"]:
                seen[short_key] = item
    return list(seen.values())


def merge_and_rank(limit: int = 20) -> list:
    """
    抓取三平台数据，合并去重后返回 Top N 条热点
    返回格式: [{"rank", "title", "hot_value", "source", "category", "url"}, ...]
    """
    all_items = []

    weibo_items = fetch_weibo_hot()
    baidu_items = fetch_baidu_hot()
    zhihu_items = fetch_zhihu_hot()

    logger.info(f"各平台数据量: 微博={len(weibo_items)}, 百度={len(baidu_items)}, 知乎={len(zhihu_items)}")

    # 标准化热度值（各平台量级不同，做相对标准化）
    def normalize_hot(items, scale=1.0):
        if not items:
            return []
        max_hot = max(i["hot_value"] for i in items) or 1
        for item in items:
            item["_normalized_hot"] = (item["hot_value"] / max_hot) * 1000 * scale
        return items

    weibo_items = normalize_hot(weibo_items, scale=1.2)  # 微博流量大，权重略高
    baidu_items = normalize_hot(baidu_items, scale=1.0)
    zhihu_items = normalize_hot(zhihu_items, scale=0.9)

    all_items = weibo_items + baidu_items + zhihu_items

    # 去重
    all_items = deduplicate(all_items)

    # 按标准化热度排序
    all_items.sort(key=lambda x: x.get("_normalized_hot", 0), reverse=True)

    # 截取 Top N，重新编号
    top_items = all_items[:limit]
    for i, item in enumerate(top_items, 1):
        item["rank"] = i
        item.pop("_normalized_hot", None)

    # 若数据不足，补充剩余数据
    if len(top_items) < limit:
        logger.warning(f"热点数据不足 {limit} 条，实际获取 {len(top_items)} 条")

    # 生成 AI 摘要和关键词
    top_items = enrich_items_with_summary(top_items)

    logger.info(f"合并后热点数量: {len(top_items)}")
    return top_items
