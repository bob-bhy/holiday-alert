#!/usr/bin/env python3
"""
Holiday Alert - 外贸节假日提醒工具
从 Nager.Date API 获取公共假日数据，格式化后推送到企业微信群机器人。
"""

import io
import json
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from collections import defaultdict


def ensure_utf8_stdout():
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


COUNTRIES = {
    # ⚡ 仓库所在地
    "HK": {"zh": "香港", "en": "Hong Kong", "region": "仓库（香港）"},
    # 中东
    "SA": {"zh": "沙特阿拉伯", "en": "Saudi Arabia", "region": "中东"},
    "IR": {"zh": "伊朗", "en": "Iran", "region": "中东"},
    "AE": {"zh": "阿联酋", "en": "UAE", "region": "中东"},
    "IL": {"zh": "以色列", "en": "Israel", "region": "中东"},
    "OM": {"zh": "阿曼", "en": "Oman", "region": "中东"},
    "QA": {"zh": "卡塔尔", "en": "Qatar", "region": "中东"},
    "PS": {"zh": "巴勒斯坦", "en": "Palestine", "region": "中东"},
    "JO": {"zh": "约旦", "en": "Jordan", "region": "中东"},
    "LB": {"zh": "黎巴嫩", "en": "Lebanon", "region": "中东"},
    "KW": {"zh": "科威特", "en": "Kuwait", "region": "中东"},
    "BH": {"zh": "巴林", "en": "Bahrain", "region": "中东"},
    "IQ": {"zh": "伊拉克", "en": "Iraq", "region": "中东"},
    "SY": {"zh": "叙利亚", "en": "Syria", "region": "中东"},
    "TR": {"zh": "土耳其", "en": "Turkey", "region": "中东"},
    # 欧洲
    "DE": {"zh": "德国", "en": "Germany", "region": "欧洲"},
    "FR": {"zh": "法国", "en": "France", "region": "欧洲"},
    "DK": {"zh": "丹麦", "en": "Denmark", "region": "欧洲"},
    "NL": {"zh": "荷兰", "en": "Netherlands", "region": "欧洲"},
    "BE": {"zh": "比利时", "en": "Belgium", "region": "欧洲"},
    "GB": {"zh": "英国", "en": "United Kingdom", "region": "欧洲"},
    "IE": {"zh": "爱尔兰", "en": "Ireland", "region": "欧洲"},
    "PT": {"zh": "葡萄牙", "en": "Portugal", "region": "欧洲"},
    "ES": {"zh": "西班牙", "en": "Spain", "region": "欧洲"},
    "CH": {"zh": "瑞士", "en": "Switzerland", "region": "欧洲"},
    "LU": {"zh": "卢森堡", "en": "Luxembourg", "region": "欧洲"},
    "IT": {"zh": "意大利", "en": "Italy", "region": "欧洲"},
    "AD": {"zh": "安道尔", "en": "Andorra", "region": "欧洲"},
    "VA": {"zh": "梵蒂冈", "en": "Vatican City", "region": "欧洲"},
    "SM": {"zh": "圣马力诺", "en": "San Marino", "region": "欧洲"},
    "MC": {"zh": "摩纳哥", "en": "Monaco", "region": "欧洲"},
    "SE": {"zh": "瑞典", "en": "Sweden", "region": "欧洲"},
    "NO": {"zh": "挪威", "en": "Norway", "region": "欧洲"},
    "FI": {"zh": "芬兰", "en": "Finland", "region": "欧洲"},
    "LT": {"zh": "立陶宛", "en": "Lithuania", "region": "欧洲"},
    "EE": {"zh": "爱沙尼亚", "en": "Estonia", "region": "欧洲"},
    "LV": {"zh": "拉脱维亚", "en": "Latvia", "region": "欧洲"},
    "IS": {"zh": "冰岛", "en": "Iceland", "region": "欧洲"},
    "CZ": {"zh": "捷克", "en": "Czech Republic", "region": "欧洲"},
    "AT": {"zh": "奥地利", "en": "Austria", "region": "欧洲"},
    "CY": {"zh": "塞浦路斯", "en": "Cyprus", "region": "欧洲"},
    "PL": {"zh": "波兰", "en": "Poland", "region": "欧洲"},
    "MT": {"zh": "马耳他", "en": "Malta", "region": "欧洲"},
    "SK": {"zh": "斯洛伐克", "en": "Slovakia", "region": "欧洲"},
    "HU": {"zh": "匈牙利", "en": "Hungary", "region": "欧洲"},
    "BG": {"zh": "保加利亚", "en": "Bulgaria", "region": "欧洲"},
    "RO": {"zh": "罗马尼亚", "en": "Romania", "region": "欧洲"},
    "GR": {"zh": "希腊", "en": "Greece", "region": "欧洲"},
    "MD": {"zh": "摩尔多瓦", "en": "Moldova", "region": "欧洲"},
    "AL": {"zh": "阿尔巴尼亚", "en": "Albania", "region": "欧洲"},
    "HR": {"zh": "克罗地亚", "en": "Croatia", "region": "欧洲"},
    "SI": {"zh": "斯洛文尼亚", "en": "Slovenia", "region": "欧洲"},
    "MK": {"zh": "北马其顿", "en": "North Macedonia", "region": "欧洲"},
    "BA": {"zh": "波黑", "en": "Bosnia and Herzegovina", "region": "欧洲"},
    "RS": {"zh": "塞尔维亚", "en": "Serbia", "region": "欧洲"},
    "UA": {"zh": "乌克兰", "en": "Ukraine", "region": "欧洲"},
    # 俄罗斯及周边
    "RU": {"zh": "俄罗斯", "en": "Russia", "region": "俄罗斯及周边"},
    "BY": {"zh": "白俄罗斯", "en": "Belarus", "region": "俄罗斯及周边"},
    # 中亚及高加索
    "KZ": {"zh": "哈萨克斯坦", "en": "Kazakhstan", "region": "中亚"},
    "AZ": {"zh": "阿塞拜疆", "en": "Azerbaijan", "region": "中亚"},
    "GE": {"zh": "格鲁吉亚", "en": "Georgia", "region": "中亚"},
    "AM": {"zh": "亚美尼亚", "en": "Armenia", "region": "中亚"},
    "KG": {"zh": "吉尔吉斯斯坦", "en": "Kyrgyzstan", "region": "中亚"},
    "TM": {"zh": "土库曼斯坦", "en": "Turkmenistan", "region": "中亚"},
    "UZ": {"zh": "乌兹别克斯坦", "en": "Uzbekistan", "region": "中亚"},
    "TJ": {"zh": "塔吉克斯坦", "en": "Tajikistan", "region": "中亚"},
}

# 英文节日名 → 中文翻译（key 全部小写匹配）
HOLIDAY_ZH = {
    # 通用
    "new year's day": "元旦",
    "new year": "元旦",
    "labour day": "劳动节",
    "labor day": "劳动节",
    "international workers' day": "国际劳动节",
    "may day": "五一劳动节",
    "children's day": "儿童节",
    "women's day": "妇女节",
    # 基督教
    "good friday": "耶稣受难日",
    "holy saturday": "圣周六",
    "easter sunday": "复活节",
    "easter monday": "复活节星期一",
    "easter": "复活节",
    "ascension day": "耶稣升天日",
    "whit sunday": "圣灵降临节",
    "whit monday": "圣灵降临节翌日",
    "pentecost": "五旬节",
    "pentecost monday": "五旬节翌日",
    "corpus christi": "基督圣体节",
    "assumption of mary": "圣母升天节",
    "assumption day": "圣母升天节",
    "all saints' day": "万圣节",
    "all saints day": "万圣节",
    "all souls' day": "万灵节",
    "christmas day": "圣诞节",
    "christmas eve": "平安夜",
    "christmas": "圣诞节",
    "second day of christmas": "圣诞节翌日",
    "st. stephen's day": "圣斯蒂芬日",
    "stephen's day": "圣斯蒂芬日",
    "boxing day": "节礼日",
    "epiphany": "主显节",
    "maundy thursday": "濯足星期四",
    "palm sunday": "棕枝主日",
    "reformation day": "宗教改革日",
    "immaculate conception": "圣母无原罪日",
    # 伊斯兰教
    "eid al-fitr": "开斋节",
    "eid al-adha": "宰牲节/古尔邦节",
    "islamic new year": "伊斯兰新年",
    "mawlid": "圣纪节",
    "prophet's birthday": "圣纪节",
    "isra and mi'raj": "夜行登霄节",
    "laylat al-qadr": "盖德尔夜",
    "ramadan": "斋月",
    "day of arafah": "阿拉法日",
    "day of arafat": "阿拉法日",
    # 各国国庆/独立日
    "national day": "国庆节",
    "independence day": "独立日",
    "republic day": "共和国日",
    "constitution day": "宪法日",
    "liberation day": "解放日",
    "unification day": "统一日",
    "reunification day": "统一日",
    "sovereignty day": "主权日",
    "statehood day": "建国日",
    "victory day": "胜利日",
    "revolution day": "革命日",
    "freedom day": "自由日",
    "democracy day": "民主日",
    "memorial day": "纪念日",
    "remembrance day": "阵亡将士纪念日",
    "armistice day": "停战日",
    "veterans day": "退伍军人节",
    "thanksgiving day": "感恩节",
    "thanksgiving": "感恩节",
    # 德国
    "german unity day": "德国统一日",
    "day of german unity": "德国统一日",
    # 法国
    "bastille day": "法国国庆日（巴士底日）",
    # 英国/爱尔兰
    "spring bank holiday": "春季银行假日",
    "summer bank holiday": "夏季银行假日",
    "early may bank holiday": "五月初银行假日",
    "late may bank holiday": "五月末银行假日",
    "august bank holiday": "八月银行假日",
    "bank holiday": "银行假日",
    "june holiday": "六月公众假期",
    "october holiday": "十月公众假期",
    "st. patrick's day": "圣帕特里克节",
    # 北欧
    "midsummer's day": "仲夏节",
    "midsummer day": "仲夏节",
    "midsummer eve": "仲夏夜",
    "midsummer's eve": "仲夏夜",
    # 南欧
    "azores day": "亚速尔群岛日",
    "portugal day": "葡萄牙国庆日",
    "day of portugal": "葡萄牙国庆日",
    "assumption of our lady": "圣母升天节",
    "republic proclamation day": "共和国宣言日",
    "restoration of independence": "光复独立日",
    "feast of the immaculate conception": "圣母无原罪日",
    "saint joseph's day": "圣若瑟日",
    "national unity day": "民族团结日",
    # 意大利
    "feast of the republic": "意大利共和国日",
    # 俄罗斯
    "russia day": "俄罗斯日",
    "defender of the fatherland day": "祖国保卫者日",
    "unity day": "民族团结日",
    "spring and labour day": "春天与劳动节",
    # 土耳其
    "national sovereignty and children's day": "国家主权与儿童节",
    "commemoration of atatürk, youth and sports day": "阿塔图尔克纪念暨青年体育日",
    "democracy and national unity day": "民主与民族团结日",
    # 以色列
    "yom kippur": "赎罪日",
    "rosh hashana": "犹太新年",
    "rosh hashanah": "犹太新年",
    "sukkot": "住棚节",
    "simchat torah": "诵经节",
    "passover": "逾越节",
    "pesach": "逾越节",
    "shavuot": "五旬节",
    "yom ha'atzmaut": "以色列独立日",
    "yom hazikaron": "阵亡将士纪念日",
    "purim": "普珥节",
    "hanukkah": "光明节",
    # 中亚
    "nauryz": "纳吾鲁孜节",
    "nowruz": "纳吾鲁孜节",
    "navruz": "纳吾鲁孜节",
    # 香港
    "lunar new year": "农历新年",
    "chinese new year": "农历新年",
    "ching ming festival": "清明节",
    "tuen ng festival": "端午节",
    "dragon boat festival": "端午节",
    "mid-autumn festival": "中秋节",
    "chung yeung festival": "重阳节",
    "hksar establishment day": "香港特区成立纪念日",
    "national day": "国庆节",
    "the birthday of the buddha": "佛诞",
}

def translate_holiday(name_en):
    """根据英文节日名翻译中文，找不到返回 None"""
    if not name_en:
        return None
    key = name_en.strip().lower()
    if key in HOLIDAY_ZH:
        return HOLIDAY_ZH[key]
    # 模糊匹配：英文名包含关键词
    for en, zh in HOLIDAY_ZH.items():
        if en in key or key in en:
            return zh
    return None

WEEKDAY_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

REGION_ORDER = ["仓库（香港）", "中东", "欧洲", "中亚", "俄罗斯及周边"]

REGION_EMOJI = {
    "仓库（香港）": "📦",
    "中东": "🕌",
    "欧洲": "🏰",
    "中亚": "🏔️",
    "俄罗斯及周边": "❄️",
}


def fetch_nager_holidays(country_code, year):
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HolidayAlert/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8")), True
    except Exception:
        pass
    return [], False


def find_holiday_clusters(year_data):
    """将一个国家全年的假日按连续日期分组，返回 {date_str: cluster_info}"""
    all_dates = sorted(set(h["date"] for h in year_data))
    if not all_dates:
        return {}

    clusters = []
    current = [all_dates[0]]
    for i in range(1, len(all_dates)):
        prev = datetime.strptime(all_dates[i - 1], "%Y-%m-%d").date()
        curr = datetime.strptime(all_dates[i], "%Y-%m-%d").date()
        if (curr - prev).days == 1:
            current.append(all_dates[i])
        else:
            clusters.append(current)
            current = [all_dates[i]]
    clusters.append(current)

    date_to_cluster = {}
    for cluster in clusters:
        info = {
            "days": len(cluster),
            "start": cluster[0],
            "end": cluster[-1],
        }
        for d in cluster:
            date_to_cluster[d] = info
    return date_to_cluster


def fetch_all_holidays(days_ahead=3):
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead - 1)
    year = today.year

    holidays_by_date = defaultdict(list)
    unsupported_countries = []

    for code, info in COUNTRIES.items():
        data, ok = fetch_nager_holidays(code, year)
        if not ok:
            unsupported_countries.append(code)
            continue

        clusters = find_holiday_clusters(data)

        for h in data:
            h_date = datetime.strptime(h["date"], "%Y-%m-%d").date()
            if today <= h_date <= end_date:
                cluster = clusters.get(h["date"], {"days": 1, "start": h["date"], "end": h["date"]})
                holidays_by_date[h["date"]].append({
                    "country_code": code,
                    "country_zh": info["zh"],
                    "country_en": info["en"],
                    "region": info["region"],
                    "name": h.get("localName") or h.get("name", ""),
                    "name_en": h.get("name", ""),
                    "date": h["date"],
                    "span_days": cluster["days"],
                    "span_start": cluster["start"],
                    "span_end": cluster["end"],
                })

        if end_date.year > year:
            data2, ok2 = fetch_nager_holidays(code, end_date.year)
            if ok2:
                clusters2 = find_holiday_clusters(data2)
                for h in data2:
                    h_date = datetime.strptime(h["date"], "%Y-%m-%d").date()
                    if today <= h_date <= end_date:
                        cluster = clusters2.get(h["date"], {"days": 1, "start": h["date"], "end": h["date"]})
                        holidays_by_date[h["date"]].append({
                            "country_code": code,
                            "country_zh": info["zh"],
                            "country_en": info["en"],
                            "region": info["region"],
                            "name": h.get("localName") or h.get("name", ""),
                            "name_en": h.get("name", ""),
                            "date": h["date"],
                            "span_days": cluster["days"],
                            "span_start": cluster["start"],
                            "span_end": cluster["end"],
                        })

    return dict(holidays_by_date), unsupported_countries


def dedupe_by_country_date(day_holidays):
    """同一国家同一天可能有多个假日条目，合并显示"""
    seen = {}
    for h in day_holidays:
        key = h["country_code"]
        if key not in seen:
            seen[key] = h
        else:
            existing = seen[key]
            if h["name"] != existing["name"]:
                existing["name"] = existing["name"] + " / " + h["name"]
                existing["name_en"] = existing["name_en"] + " / " + h["name_en"]
    return list(seen.values())


def fmt_span(h):
    """格式化假期天数信息"""
    days = h.get("span_days", 1)
    if days <= 1:
        return "放假1天"
    start = h.get("span_start", "")
    end = h.get("span_end", "")
    try:
        s = datetime.strptime(start, "%Y-%m-%d").strftime("%-m/%-d")
    except ValueError:
        s = datetime.strptime(start, "%Y-%m-%d").strftime("%m/%d").lstrip("0").replace("/0", "/")
    try:
        e = datetime.strptime(end, "%Y-%m-%d").strftime("%-m/%-d")
    except ValueError:
        e = datetime.strptime(end, "%Y-%m-%d").strftime("%m/%d").lstrip("0").replace("/0", "/")
    return f"连休{days}天（{s}-{e}）"


def format_wecom_message(holidays_by_date, unsupported_countries, extra_holidays=None, days_ahead=3):
    today = datetime.now().date()
    end_date = today + timedelta(days=days_ahead - 1)

    if extra_holidays:
        for h in extra_holidays:
            holidays_by_date.setdefault(h["date"], []).append(h)

    today_str = today.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    today_wd = WEEKDAY_ZH[today.weekday()]
    end_wd = WEEKDAY_ZH[end_date.weekday()]

    lines = []
    lines.append("📅 **外贸节假日提醒**")
    lines.append(f"{today_str}（{today_wd}）至 {end_str}（{end_wd}）")
    lines.append("")

    has_any = False
    total_count = 0
    hk_alert = False

    for i in range(days_ahead):
        check_date = today + timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        weekday = WEEKDAY_ZH[check_date.weekday()]
        raw_holidays = holidays_by_date.get(date_str, [])
        day_holidays = dedupe_by_country_date(raw_holidays)

        if not day_holidays:
            lines.append(f"**{date_str} {weekday}**  ✅ 无节假日")
            lines.append("")
            continue

        has_any = True
        total_count += len(day_holidays)
        lines.append(f"**{date_str} {weekday}**  🔴 {len(day_holidays)}个国家/地区放假")

        by_region = defaultdict(list)
        for h in day_holidays:
            by_region[h["region"]].append(h)
            if h["country_code"] == "HK":
                hk_alert = True

        for region in REGION_ORDER:
            if region not in by_region:
                continue
            emoji = REGION_EMOJI.get(region, "")
            lines.append(f"> {emoji} **{region}**")

            by_holiday = defaultdict(list)
            for h in by_region[region]:
                key = h.get("name_en") or h.get("name", "")
                by_holiday[key].append(h)

            def holiday_display_name(entries):
                name_en = entries[0].get("name_en", "")
                names_local = sorted(set(e["name"] for e in entries))
                main_local = names_local[0]
                zh = translate_holiday(name_en)
                if zh:
                    # 有中文翻译：中文名 / English Name
                    return f"{zh} / {name_en}"
                elif main_local and name_en and main_local != name_en:
                    # 无中文翻译但有当地语名：当地语名 / English Name
                    return f"{main_local} / {name_en}"
                else:
                    return name_en or main_local

            for holiday_key, entries in by_holiday.items():
                holiday_name = holiday_display_name(entries)
                by_span = defaultdict(list)
                for e in entries:
                    by_span[fmt_span(e)].append(e)

                if len(by_span) == 1:
                    span_info = list(by_span.keys())[0]
                    countries = "、".join(f"**{e['country_zh']}**" for e in sorted(entries, key=lambda x: x["country_zh"]))
                    is_long = any(e.get("span_days", 1) > 1 for e in entries)
                    color = "warning" if is_long else "comment"
                    lines.append(f"> {holiday_name}")
                    lines.append(f"> {countries}")
                    lines.append(f"> <font color=\"{color}\">⏱ {span_info}</font>")
                else:
                    lines.append(f"> {holiday_name}")
                    for span_info, span_entries in sorted(by_span.items(), key=lambda x: -x[1][0].get("span_days", 1)):
                        countries = "、".join(f"**{e['country_zh']}**" for e in sorted(span_entries, key=lambda x: x["country_zh"]))
                        is_long = any(e.get("span_days", 1) > 1 for e in span_entries)
                        color = "warning" if is_long else "comment"
                        lines.append(f"> {countries} — <font color=\"{color}\">{span_info}</font>")

                has_hk = any(e["country_code"] == "HK" for e in entries)
                if has_hk:
                    lines.append(f"> <font color=\"warning\">⚠️ 香港仓库休息，注意发货安排！</font>")
        lines.append("")

    lines.append("─" * 20)
    if hk_alert:
        lines.append("<font color=\"warning\">📦 香港仓库有假期，请提前备货或调整发货计划！</font>")
    if has_any:
        lines.append(f"⚠️ 未来{days_ahead}天共 **{total_count}** 条假日，注意跟单节奏")
    else:
        lines.append("🎉 未来三天各市场正常工作，放心跟进！")

    now_str = datetime.now().strftime("%H:%M")
    lines.append(f"🔍 覆盖{len(COUNTRIES)}国 · {now_str}更新")

    return "\n".join(lines)


WEB_URL = "https://bob-bhy.github.io/holiday-alert/"


def _wecom_post(webhook_url, payload_dict):
    data = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("errcode") == 0, result
    except Exception as e:
        return False, str(e)


def post_to_wecom(webhook_url, message):
    # 1) 发送 markdown 节假日内容
    ok, res = _wecom_post(webhook_url, {
        "msgtype": "markdown",
        "markdown": {"content": message}
    })
    if ok:
        print("✅ 节假日消息推送成功", file=sys.stderr)
    else:
        print(f"❌ 节假日消息推送失败: {res}", file=sys.stderr)
        return False

    # 2) 发送 news 卡片（本月完整日历）
    today = datetime.now()
    month_zh = f"{today.year}年{today.month}月"
    ok2, res2 = _wecom_post(webhook_url, {
        "msgtype": "news",
        "news": {
            "articles": [{
                "title": f"📊 {month_zh} 完整节假日日历",
                "description": f"覆盖{len(COUNTRIES)}国 · 当月日历视图 · 点击日期查看详情 · 支持地区筛选",
                "url": WEB_URL,
                "picurl": ""
            }]
        }
    })
    if ok2:
        print("✅ 日历卡片推送成功", file=sys.stderr)
    else:
        print(f"⚠️ 日历卡片推送失败: {res2}", file=sys.stderr)

    return True


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {}


def main():
    ensure_utf8_stdout()
    import argparse
    parser = argparse.ArgumentParser(description="外贸节假日提醒工具")
    parser.add_argument("--webhook", help="企微 webhook URL（也可写入 config.json）")
    parser.add_argument("--days", type=int, default=3, help="向前查看天数，默认3")
    parser.add_argument("--fetch-only", action="store_true", help="仅获取数据，输出 JSON")
    parser.add_argument("--format-only", action="store_true", help="仅格式化消息，不推送")
    parser.add_argument("--extra-holidays", help="补充假日 JSON 文件路径")
    parser.add_argument("--post-message", help="直接推送指定消息文本")
    args = parser.parse_args()

    config = load_config()
    webhook = args.webhook or config.get("webhook_url", "")

    if args.post_message:
        if not webhook:
            print("❌ 需要 webhook URL（--webhook 或 config.json）", file=sys.stderr)
            sys.exit(1)
        post_to_wecom(webhook, args.post_message)
        return

    print(f"🔄 正在获取未来{args.days}天节假日数据...", file=sys.stderr)
    holidays_by_date, unsupported = fetch_all_holidays(args.days)

    if args.fetch_only:
        output = {
            "holidays": {k: v for k, v in sorted(holidays_by_date.items())},
            "unsupported_countries": unsupported,
            "unsupported_names": [COUNTRIES[c]["zh"] for c in unsupported],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    extra = None
    if args.extra_holidays:
        with open(args.extra_holidays, "r", encoding="utf-8-sig") as f:
            extra = json.load(f)

    message = format_wecom_message(holidays_by_date, unsupported, extra, args.days)

    if args.format_only or not webhook:
        if not webhook and not args.format_only:
            print("⚠️ 未配置 webhook，仅输出消息：", file=sys.stderr)
        print(message)
        return

    print("📤 推送到企业微信...", file=sys.stderr)
    post_to_wecom(webhook, message)


if __name__ == "__main__":
    main()
