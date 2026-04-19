"""AI 摘要生成模块 - 基于规则的热点摘要提取"""

import re
import logging

logger = logging.getLogger(__name__)


# ── 领域关键词库 ──────────────────────────────
KEYWORD_CATEGORIES = {
    "娱乐": ["明星", "演员", "电影", "综艺", "歌手", "演唱会", "票房", "出道", "恋情",
             "分手", "结婚", "离婚", "出轨", "塌房", "粉丝", "偶像", "选秀", "代言",
             "红毯", "颁奖", "直播", "网红", "主播", "热搜", "吃瓜", "八卦", "导演"],
    "科技": ["AI", "人工智能", "芯片", "手机", "苹果", "华为", "特斯拉", "自动驾驶",
             "5G", "量子", "机器人", "大模型", "GPT", "互联网", "算法", "代码",
             "开源", "系统", "软件", "硬件", "数据", "平台", "智能", "科技"],
    "财经": ["股票", "基金", "A股", "港股", "美股", "上市", "融资", "并购", "市值",
             "营收", "利润", "GDP", "央行", "利率", "通胀", "经济", "金融",
             "投资", "创业", "破产", "裁员", "房价", "楼市", "股市", "降息",
             "加息", "关税", "贸易"],
    "体育": ["比赛", "冠军", "联赛", "世界杯", "奥运", "NBA", "足球", "篮球",
             "乒乓球", "羽毛球", "游泳", "田径", "选手", "教练", "比分", "进球",
             "绝杀", "逆转", "夺冠", "犯规", "赛事", "运动员"],
    "健康": ["疫情", "病毒", "疫苗", "感染", "医疗", "健康", "药物", "治疗",
             "手术", "癌症", "医保", "医院", "医生", "患者", "疾病", "防控",
             "养生", "中医", "体检", "长寿"],
    "社会": ["事故", "犯罪", "诈骗", "案件", "法院", "判决", "维权", "投诉",
             "失踪", "救援", "灾害", "地震", "洪水", "火灾", "暴雪", "暴雨",
             "城管", "交通", "教育", "学校", "高考", "中考", "考研",
             "就业", "工资", "退休", "社保", "养老金"],
    "国际": ["美国", "日本", "韩国", "俄罗斯", "欧盟", "联合国", "总统", "首相",
             "制裁", "冲突", "战争", "谈判", "外交", "访问", "峰会", "G7",
             "北约", "中非", "中东", "乌克兰"],
}


def extract_keywords(title: str) -> list:
    """从标题中提取关键词，返回最多3个"""
    keywords = []
    for cat, words in KEYWORD_CATEGORIES.items():
        for w in words:
            if w in title and w not in keywords:
                keywords.append(w)
    # 补充：提取引号内内容作为关键词
    quote_match = re.findall(r'[\u300c\u300d\u300e\u300f""](.+?)[\u300c\u300d\u300e\u300f""]', title)
    for q in quote_match:
        if q not in keywords and len(q) <= 10:
            keywords.append(q)
    return keywords[:3]


def classify_cause(title: str, keywords: list) -> str:
    """根据关键词分析事件可能的原因/性质"""
    cause_patterns = [
        # 事故类
        (r"爆炸|起火|坍塌|车祸|坠毁|泄漏", "突发安全事故"),
        (r"地震|洪水|台风|暴雨|暴雪|干旱", "自然灾害"),
        # 政策类
        (r"发布|出台|规定|政策|法规|公告|通知|禁令|批准|实施", "政策法规变动"),
        # 成就类
        (r"突破|成功|夺冠|创纪录|首次|里程碑|上线|发布", "重大突破/成就"),
        # 争议类
        (r"争议|质疑|曝光|举报|投诉|回应|辟谣|澄清|道歉", "舆论争议事件"),
        (r"出轨|塌房|翻车|封杀|劣迹", "公众人物争议"),
        # 经济类
        (r"涨价|降价|暴跌|暴涨|崩盘|熔断|大涨|大跌", "市场剧烈波动"),
        (r"上市|融资|并购|IPO", "资本运作"),
        # 科技类
        (r"AI|大模型|发布|升级|突破|发布", "科技动态"),
        # 社会类
        (r"骗|诈|盗|抢|杀|伤|逃", "违法犯罪案件"),
        (r"失踪|寻人|救援|被困", "紧急救援事件"),
    ]

    for pattern, cause in cause_patterns:
        if re.search(pattern, title):
            return cause

    # 根据关键词推断
    if any(k in KEYWORD_CATEGORIES.get("科技", []) for k in keywords):
        return "科技领域动态"
    if any(k in KEYWORD_CATEGORIES.get("财经", []) for k in keywords):
        return "财经市场动态"
    if any(k in KEYWORD_CATEGORIES.get("娱乐", []) for k in keywords):
        return "娱乐行业动态"
    if any(k in KEYWORD_CATEGORIES.get("体育", []) for k in keywords):
        return "体育赛事动态"

    return "时事热点追踪"


def generate_summary(title: str) -> str:
    """
    为单条热点生成摘要信息
    返回格式: "关键词: A、B、C | 事件性质: XXX"
    """
    keywords = extract_keywords(title)
    cause = classify_cause(title, keywords)

    kw_str = "、".join(keywords) if keywords else "综合热点"
    return f"关键词: {kw_str} | 事件性质: {cause}"


def enrich_items_with_summary(items: list) -> list:
    """批量为热点列表添加摘要字段"""
    import json
    for item in items:
        keywords = extract_keywords(item.get("title", ""))
        cause = classify_cause(item.get("title", ""), keywords)
        kw_str = "、".join(keywords) if keywords else "综合热点"
        item["summary"] = f"关键词: {kw_str} | 事件性质: {cause}"
        item["keywords"] = json.dumps(keywords, ensure_ascii=False) if keywords else ""
    return items
