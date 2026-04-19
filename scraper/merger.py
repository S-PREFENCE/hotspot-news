"""多平台热点数据合并、去重、排序模块 v3.0"""
import re
import json
import logging
from .weibo import fetch_weibo_hot
from .baidu import fetch_baidu_hot
# from .zhihu import fetch_zhihu_hot  # v3.0: 默认移除知乎
from .douyin import fetch_douyin_hot
from .kuaishou import fetch_kuaishou_hot
from .bilibili import fetch_bilibili_hot
from .ithome import fetch_ithome_hot
from .sina_finance import fetch_sina_finance_hot
from .pengpai import fetch_pengpai_hot
from .summarizer import enrich_items_with_summary

logger = logging.getLogger(__name__)

# ── 领域标签规则库 ──────────────────────────────
TAG_RULES = {
    "AI": ["大模型", "OpenAI", "Sora", "通义千问", "AI芯片", "生成式AI", "AI", "GPT",
           "人工智能", "ChatGPT", "Claude", "Gemini", "LLM", "文心一言", "智谱"],
    "科技": ["芯片", "5G", "华为", "苹果", "SpaceX", "机器人", "特斯拉", "小米", "手机",
             "互联网", "科技", "数码", "自动驾驶", "新能源", "半导体", "量子", "开源"],
    "教育": ["高考", "考研", "双减", "留学", "教师", "学位", "大学", "学校", "学生",
             "中考", "招生", "培训", "课程"],
    "综艺": ["明星", "综艺", "选秀", "芒果TV", "爱奇艺", "跑男", "偶像", "演员",
             "演唱会", "电影", "影视", "番剧", "动漫"],
    "国家事件": ["政策", "外交", "两会", "国防", "白皮书", "国务院", "人大常委会",
                "中央", "全国政协", "发改委", "证监会"],
    "犯罪": ["警方通报", "诈骗", "命案", "抓捕", "庭审", "通缉", "刑事", "贪污",
             "受贿", "走私", "扫黑除恶"],
    "国际": ["联合国", "战争", "制裁", "国际法院", "全球", "北约", "G7", "欧盟",
             "峰会", "导弹", "冲突", "中东"],
}


def assign_tags(title: str, force_tags: list = None) -> list:
    """
    根据标题自动打标签
    force_tags: 强制添加的标签（如国际头条强制"国际"标签）
    返回最多2个标签
    """
    tags = list(force_tags) if force_tags else []

    for tag, keywords in TAG_RULES.items():
        if tag in tags:
            continue  # 避免重复
        if any(kw in title for kw in keywords):
            tags.append(tag)

    return tags[:2]


def normalize_title(title: str) -> str:
    """标题归一化，用于去重比较"""
    title = re.sub(r"[#\s【】「」《》\[\]]", "", title)
    return title.lower()


def deduplicate(items: list) -> list:
    """去除标题高度相似的条目，跨平台同标题保留不同source以确保平台多样性"""
    # 第1步：同平台内去重（同source + 相似标题 -> 保留热度最高的）
    source_groups = {}
    for item in items:
        source = item.get("source", "unknown")
        if source not in source_groups:
            source_groups[source] = {}
        key = normalize_title(item["title"])
        short_key = key[:8] if len(key) >= 8 else key
        
        if short_key not in source_groups[source]:
            source_groups[source][short_key] = item
        else:
            if item["hot_value"] > source_groups[source][short_key]["hot_value"]:
                source_groups[source][short_key] = item
    
    # 第2步：合并所有平台，跨平台相同标题只保留热度最高的那个
    result = {}
    for source, group in source_groups.items():
        for short_key, item in group.items():
            if short_key not in result:
                result[short_key] = item
            else:
                existing = result[short_key]
                existing_source = existing.get("source", "")
                # 不同平台：两者都保留（用composite key区分）
                if existing_source != source:
                    composite_existing = f"{short_key}|{existing_source}"
                    composite_new = f"{short_key}|{source}"
                    result[composite_existing] = existing
                    result[composite_new] = item
                    del result[short_key]
                else:
                    # 同平台：保留热度更高的
                    if item["hot_value"] > existing["hot_value"]:
                        result[short_key] = item
    
    return list(result.values())


def merge_and_rank(limit: int = 30) -> list:
    """
    抓取多平台数据，合并去重后返回 Top N 条热点
    返回格式: [{"rank", "title", "hot_value", "source", "category", "url", "tags"}, ...]
    """
    all_items = []

    weibo_items = fetch_weibo_hot()
    baidu_items = fetch_baidu_hot()
    # zhihu_items = fetch_zhihu_hot()  # v3.0: 默认移除
    douyin_items = fetch_douyin_hot()
    kuaishou_items = fetch_kuaishou_hot()
    bilibili_items = fetch_bilibili_hot()
    ithome_items = fetch_ithome_hot()
    sina_finance_items = fetch_sina_finance_hot()
    pengpai_items = fetch_pengpai_hot()

    logger.info(
        f"各平台数据量: 微博={len(weibo_items)}, 百度={len(baidu_items)}, "
        f"抖音={len(douyin_items)}, 快手={len(kuaishou_items)}, "
        f"B站={len(bilibili_items)}, IT之家={len(ithome_items)}, "
        f"新浪财经={len(sina_finance_items)}, 澎湃={len(pengpai_items)}"
    )

    # 标准化热度值（各平台量级不同，做相对标准化）
    def normalize_hot(items, scale=1.0):
        if not items:
            return []
        max_hot = max(i["hot_value"] for i in items) or 1
        for item in items:
            item["_normalized_hot"] = (item["hot_value"] / max_hot) * 1000 * scale
        return items

    weibo_items = normalize_hot(weibo_items, scale=1.2)
    baidu_items = normalize_hot(baidu_items, scale=1.0)
    douyin_items = normalize_hot(douyin_items, scale=1.1)
    kuaishou_items = normalize_hot(kuaishou_items, scale=1.0)
    bilibili_items = normalize_hot(bilibili_items, scale=0.9)
    ithome_items = normalize_hot(ithome_items, scale=1.0)
    sina_finance_items = normalize_hot(sina_finance_items, scale=0.9)
    pengpai_items = normalize_hot(pengpai_items, scale=1.0)

    all_items = (
        weibo_items + baidu_items + douyin_items + kuaishou_items +
        bilibili_items + ithome_items + sina_finance_items + pengpai_items
    )

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

    # 为每条热点打标签
    for item in top_items:
        force_tags = item.pop("_force_tags", None)
        tags = assign_tags(item.get("title", ""), force_tags)
        item["tags"] = json.dumps(tags, ensure_ascii=False) if tags else ""

    # 生成 AI 摘要和关键词
    top_items = enrich_items_with_summary(top_items)

    logger.info(f"合并后热点数量: {len(top_items)}")
    return top_items
