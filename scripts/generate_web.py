#!/usr/bin/env python3
"""
生成外贸节假日日历网页（当月视图，Claude 极简风格）
输出自包含 HTML 文件，数据内嵌为 JSON。
"""

import io, json, sys, os, calendar, urllib.request
from datetime import datetime, timedelta, date
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ─── 复用 holiday_alert.py 的国家列表与翻译 ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from holiday_alert import COUNTRIES, HOLIDAY_ZH, translate_holiday, fetch_nager_holidays, find_holiday_clusters

# ─── 伊斯兰历主要假日（2026 年估算，±1-2 天） ───
ISLAMIC_HOLIDAYS_2026 = [
    # 开斋节 Eid al-Fitr ≈ 2026-03-20 (已过)
    # 宰牲节 Eid al-Adha ≈ 2026-05-26 (已过)
    # 伊斯兰新年 Islamic New Year ≈ 2026-06-17
    {"name_zh": "伊斯兰新年", "name_en": "Islamic New Year", "date": "2026-06-17",
     "countries": {
         "SA": 1, "AE": 1, "QA": 1, "OM": 1, "BH": 1, "KW": 1,
         "JO": 1, "LB": 1, "IQ": 1, "SY": 1, "PS": 1, "IR": 1,
     }},
    # 先知诞辰 Mawlid ≈ 2026-08-26 (不在6月)
]

# ─── 香港 2026 年假日 ───
HK_HOLIDAYS_2026 = [
    {"date": "2026-01-01", "name_zh": "元旦", "name_en": "New Year's Day"},
    {"date": "2026-02-17", "name_zh": "农历新年", "name_en": "Lunar New Year"},
    {"date": "2026-02-18", "name_zh": "农历年初二", "name_en": "Lunar New Year"},
    {"date": "2026-02-19", "name_zh": "农历年初三", "name_en": "Lunar New Year"},
    {"date": "2026-04-03", "name_zh": "耶稣受难日", "name_en": "Good Friday"},
    {"date": "2026-04-04", "name_zh": "耶稣受难日翌日", "name_en": "Day after Good Friday"},
    {"date": "2026-04-06", "name_zh": "复活节星期一", "name_en": "Easter Monday"},
    {"date": "2026-04-05", "name_zh": "清明节", "name_en": "Ching Ming Festival"},
    {"date": "2026-05-01", "name_zh": "劳动节", "name_en": "Labour Day"},
    {"date": "2026-05-24", "name_zh": "佛诞", "name_en": "Birthday of the Buddha"},
    {"date": "2026-06-19", "name_zh": "端午节", "name_en": "Tuen Ng Festival"},
    {"date": "2026-07-01", "name_zh": "香港特区成立纪念日", "name_en": "HKSAR Establishment Day"},
    {"date": "2026-10-01", "name_zh": "国庆节", "name_en": "National Day"},
    {"date": "2026-10-07", "name_zh": "中秋节翌日", "name_en": "Day after Mid-Autumn Festival"},
    {"date": "2026-10-19", "name_zh": "重阳节", "name_en": "Chung Yeung Festival"},
    {"date": "2026-12-25", "name_zh": "圣诞节", "name_en": "Christmas Day"},
    {"date": "2026-12-26", "name_zh": "圣诞节翌日", "name_en": "Boxing Day"},
]

# ─── 以色列 2026 年假日 ───
IL_HOLIDAYS_2026 = [
    {"date": "2026-03-17", "name_zh": "普珥节", "name_en": "Purim"},
    {"date": "2026-04-02", "name_zh": "逾越节", "name_en": "Passover"},
    {"date": "2026-04-08", "name_zh": "逾越节末日", "name_en": "Last Day of Passover"},
    {"date": "2026-04-15", "name_zh": "阵亡将士纪念日", "name_en": "Yom Hazikaron"},
    {"date": "2026-04-16", "name_zh": "以色列独立日", "name_en": "Yom Ha'atzmaut"},
    {"date": "2026-05-22", "name_zh": "五旬节", "name_en": "Shavuot"},
    {"date": "2026-09-22", "name_zh": "犹太新年", "name_en": "Rosh Hashanah"},
    {"date": "2026-09-23", "name_zh": "犹太新年次日", "name_en": "Rosh Hashanah II"},
    {"date": "2026-10-01", "name_zh": "赎罪日", "name_en": "Yom Kippur"},
    {"date": "2026-10-06", "name_zh": "住棚节", "name_en": "Sukkot"},
    {"date": "2026-10-13", "name_zh": "诵经节", "name_en": "Simchat Torah"},
]


def fetch_month_holidays(year, month):
    """获取指定月份所有国家的假日数据"""
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    # {date_str: [{country_code, country_zh, region, name_zh, name_en, span_days, span_start, span_end}]}
    holidays = defaultdict(list)
    unsupported = []

    # 1) Nager.Date API
    for code, info in COUNTRIES.items():
        data, ok = fetch_nager_holidays(code, year)
        if not ok:
            unsupported.append(code)
            continue
        clusters = find_holiday_clusters(data)
        for h in data:
            h_date = datetime.strptime(h["date"], "%Y-%m-%d").date()
            if month_start <= h_date <= month_end:
                cl = clusters.get(h["date"], {"days": 1, "start": h["date"], "end": h["date"]})
                name_en = h.get("name", "")
                zh = translate_holiday(name_en)
                holidays[h["date"]].append({
                    "cc": code, "zh": info["zh"], "en": info["en"], "region": info["region"],
                    "name_zh": zh or h.get("localName", name_en),
                    "name_en": name_en,
                    "span": cl["days"], "span_s": cl["start"], "span_e": cl["end"],
                })

    # 2) 香港
    if "HK" in unsupported:
        for h in HK_HOLIDAYS_2026:
            d = datetime.strptime(h["date"], "%Y-%m-%d").date()
            if month_start <= d <= month_end:
                holidays[h["date"]].append({
                    "cc": "HK", "zh": "香港", "en": "Hong Kong", "region": "仓库（香港）",
                    "name_zh": h["name_zh"], "name_en": h["name_en"],
                    "span": 1, "span_s": h["date"], "span_e": h["date"],
                })

    # 3) 以色列
    if "IL" in unsupported:
        for h in IL_HOLIDAYS_2026:
            d = datetime.strptime(h["date"], "%Y-%m-%d").date()
            if month_start <= d <= month_end:
                holidays[h["date"]].append({
                    "cc": "IL", "zh": "以色列", "en": "Israel", "region": "中东",
                    "name_zh": h["name_zh"], "name_en": h["name_en"],
                    "span": 1, "span_s": h["date"], "span_e": h["date"],
                })

    # 4) 伊斯兰假日
    for ih in ISLAMIC_HOLIDAYS_2026:
        d = datetime.strptime(ih["date"], "%Y-%m-%d").date()
        if month_start <= d <= month_end:
            for cc, days in ih["countries"].items():
                if cc in COUNTRIES:
                    info = COUNTRIES[cc]
                    end_d = d + timedelta(days=days - 1)
                    for offset in range(days):
                        dd = d + timedelta(days=offset)
                        if month_start <= dd <= month_end:
                            holidays[dd.strftime("%Y-%m-%d")].append({
                                "cc": cc, "zh": info["zh"], "en": info["en"], "region": info["region"],
                                "name_zh": ih["name_zh"], "name_en": ih["name_en"],
                                "span": days, "span_s": ih["date"],
                                "span_e": end_d.strftime("%Y-%m-%d"),
                            })

    return dict(holidays)


def generate_html(year, month, holidays):
    """生成自包含 HTML"""
    today = date.today()
    month_name_zh = f"{year}年{month}月"
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(year, month)

    # 统计每天放假国家数
    day_counts = {}
    for d_str, entries in holidays.items():
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
        if d.month == month:
            seen = set()
            for e in entries:
                seen.add(e["cc"])
            day_counts[d.day] = len(seen)

    # 按日期聚合去重
    day_data = {}
    for d_str, entries in holidays.items():
        d = datetime.strptime(d_str, "%Y-%m-%d").date()
        if d.month == month:
            seen = {}
            for e in entries:
                key = e["cc"]
                if key not in seen:
                    seen[key] = e
                else:
                    # 合并同国同日多个假日
                    if e["name_zh"] not in seen[key]["name_zh"]:
                        seen[key]["name_zh"] += " / " + e["name_zh"]
                        seen[key]["name_en"] += " / " + e["name_en"]
            day_data[d.day] = list(seen.values())

    holidays_json = json.dumps(day_data, ensure_ascii=False)

    # prev/next month
    if month == 1:
        prev_y, prev_m = year - 1, 12
    else:
        prev_y, prev_m = year, month - 1
    if month == 12:
        next_y, next_m = year + 1, 1
    else:
        next_y, next_m = year, month + 1

    WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]

    # Build calendar grid HTML
    grid_html = ""
    for w in weeks:
        for i, day in enumerate(w):
            if day == 0:
                grid_html += '<div class="cell empty"></div>\n'
            else:
                count = day_counts.get(day, 0)
                is_today = (today.year == year and today.month == month and today.day == day)
                is_weekend = i >= 5

                classes = ["cell"]
                if is_today:
                    classes.append("today")
                if is_weekend:
                    classes.append("weekend")
                if count > 0:
                    classes.append("has-holiday")
                    if count >= 10:
                        classes.append("hot")
                    elif count >= 4:
                        classes.append("warm")
                    else:
                        classes.append("mild")

                # Check if HK has holiday
                hk_flag = ""
                if day in day_data:
                    for e in day_data[day]:
                        if e["cc"] == "HK":
                            hk_flag = '<span class="hk-dot" title="香港仓库休息">📦</span>'
                            break

                badge = f'<span class="badge">{count}国</span>' if count > 0 else ""
                grid_html += f'<div class="{" ".join(classes)}" data-day="{day}" onclick="showDay({day})">'
                grid_html += f'<span class="day-num">{day}</span>{hk_flag}{badge}</div>\n'

    # Build quick preview (today + 3 days)
    preview_html = ""
    for offset in range(3):
        d = today + timedelta(days=offset)
        if d.month != month:
            continue
        wd = ["周一","周二","周三","周四","周五","周六","周日"][d.weekday()]
        entries = day_data.get(d.day, [])
        if entries:
            # Group by holiday name
            by_name = defaultdict(list)
            for e in entries:
                by_name[e["name_en"]].append(e)
            details = ""
            for name_en, group in by_name.items():
                zh_name = group[0]["name_zh"]
                countries = "、".join(e["zh"] for e in sorted(group, key=lambda x: x["zh"]))
                details += f'<div class="preview-holiday"><span class="ph-name">{zh_name} / {name_en}</span>'
                details += f'<span class="ph-countries">{countries}</span></div>'
            cls = "preview-day has-h"
            label = f'🔴 {len(set(e["cc"] for e in entries))}国放假'
        else:
            details = ""
            cls = "preview-day"
            label = '✅ 无节假日'
        today_tag = ' <span class="tag-today">今天</span>' if offset == 0 else ""
        preview_html += f'''<div class="{cls}">
            <div class="pd-header"><strong>{d.strftime("%m/%d")} {wd}</strong>{today_tag}<span class="pd-label">{label}</span></div>
            {details}</div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>外贸节假日日历 — {month_name_zh}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  background: #F7F6F3; color: #1A1A1A; line-height: 1.5;
  min-height: 100vh;
}}
.container {{ max-width: 800px; margin: 0 auto; padding: 24px 16px; }}

/* ── Header ── */
.header {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #E8E5E0;
}}
.header h1 {{ font-size: 20px; font-weight: 600; letter-spacing: -0.3px; }}
.header h1 small {{ font-weight: 400; color: #8B8680; font-size: 14px; margin-left: 8px; }}
.nav {{ display: flex; gap: 8px; }}
.nav button {{
  background: #FFF; border: 1px solid #E8E5E0; border-radius: 8px;
  padding: 6px 14px; font-size: 13px; cursor: pointer; color: #5A534B;
  transition: all .15s;
}}
.nav button:hover {{ background: #F0EFEB; border-color: #D5D0C8; }}

/* ── Filters ── */
.filters {{
  display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap;
}}
.filters button {{
  padding: 5px 14px; border-radius: 20px; font-size: 12px;
  border: 1px solid #E8E5E0; background: #FFF; cursor: pointer;
  transition: all .15s; color: #5A534B;
}}
.filters button.active {{ background: #1A1A1A; color: #FFF; border-color: #1A1A1A; }}
.filters button:hover:not(.active) {{ background: #F0EFEB; }}
.filter-hk.active {{ background: #DC2626; border-color: #DC2626; }}
.filter-mideast.active {{ background: #B45309; border-color: #B45309; }}
.filter-europe.active {{ background: #1D4ED8; border-color: #1D4ED8; }}
.filter-ca.active {{ background: #059669; border-color: #059669; }}
.filter-ru.active {{ background: #6D28D9; border-color: #6D28D9; }}

/* ── Calendar Grid ── */
.cal-header {{
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; margin-bottom: 2px;
}}
.cal-header span {{
  text-align: center; font-size: 12px; color: #8B8680; padding: 8px 0;
  font-weight: 500;
}}
.cal-grid {{
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;
}}
.cell {{
  background: #FFF; border-radius: 8px; min-height: 72px;
  padding: 8px; position: relative; cursor: default;
  transition: all .15s; border: 2px solid transparent;
}}
.cell.empty {{ background: transparent; }}
.cell.has-holiday {{ cursor: pointer; }}
.cell.has-holiday:hover {{ transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
.cell.mild {{ background: #FEF9EF; }}
.cell.warm {{ background: #FDEDC8; }}
.cell.hot {{ background: #FBDBA7; }}
.cell.today {{ border-color: #1A1A1A; }}
.cell.weekend .day-num {{ color: #B45309; }}
.day-num {{ font-size: 14px; font-weight: 600; }}
.badge {{
  position: absolute; bottom: 6px; right: 6px;
  font-size: 10px; color: #8B8680; font-weight: 500;
}}
.cell.hot .badge {{ color: #92400E; font-weight: 600; }}
.hk-dot {{ position: absolute; top: 6px; right: 8px; font-size: 12px; }}

/* ── Quick Preview ── */
.preview {{ margin-top: 28px; }}
.preview h2 {{
  font-size: 14px; font-weight: 600; color: #8B8680; text-transform: uppercase;
  letter-spacing: 0.5px; margin-bottom: 12px;
}}
.preview-day {{
  background: #FFF; border-radius: 10px; padding: 14px 16px; margin-bottom: 8px;
  border-left: 3px solid #E8E5E0;
}}
.preview-day.has-h {{ border-left-color: #D97706; }}
.pd-header {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
.pd-label {{ font-size: 12px; color: #8B8680; margin-left: auto; }}
.tag-today {{
  font-size: 10px; background: #1A1A1A; color: #FFF; padding: 1px 8px;
  border-radius: 10px;
}}
.preview-holiday {{ margin-top: 8px; padding-left: 2px; }}
.ph-name {{ display: block; font-size: 13px; font-weight: 600; color: #B45309; }}
.ph-countries {{ display: block; font-size: 12px; color: #5A534B; margin-top: 2px; }}

/* ── Day Detail Modal ── */
.overlay {{
  display: none; position: fixed; inset: 0; background: rgba(0,0,0,.3);
  z-index: 100; justify-content: center; align-items: center;
  backdrop-filter: blur(2px);
}}
.overlay.show {{ display: flex; }}
.modal {{
  background: #FFF; border-radius: 14px; padding: 24px;
  max-width: 520px; width: 90%; max-height: 80vh; overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0,0,0,.12);
}}
.modal-header {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #E8E5E0;
}}
.modal-header h3 {{ font-size: 16px; }}
.modal-close {{
  width: 28px; height: 28px; border: none; background: #F0EFEB;
  border-radius: 50%; cursor: pointer; font-size: 14px; color: #5A534B;
}}
.modal-close:hover {{ background: #E8E5E0; }}
.modal-region {{ margin-bottom: 14px; }}
.modal-region-title {{
  font-size: 12px; font-weight: 600; color: #8B8680; text-transform: uppercase;
  letter-spacing: 0.5px; margin-bottom: 6px;
}}
.modal-entry {{
  padding: 8px 0; border-bottom: 1px solid #F5F3EF;
}}
.modal-entry:last-child {{ border-bottom: none; }}
.me-country {{ font-weight: 600; font-size: 14px; }}
.me-holiday {{ font-size: 13px; color: #5A534B; }}
.me-span {{ font-size: 11px; color: #B45309; margin-top: 2px; }}
.me-hk {{ color: #DC2626; font-weight: 600; font-size: 12px; margin-top: 4px; }}
.no-holidays {{ color: #8B8680; text-align: center; padding: 24px; font-size: 14px; }}

/* ── Footer ── */
.footer {{
  margin-top: 32px; padding-top: 16px; border-top: 1px solid #E8E5E0;
  text-align: center; font-size: 11px; color: #B5AFA7;
}}

/* ── legend ── */
.legend {{
  display: flex; gap: 16px; justify-content: center; margin: 16px 0 0;
  font-size: 11px; color: #8B8680;
}}
.legend span {{ display: flex; align-items: center; gap: 4px; }}
.legend-dot {{
  width: 12px; height: 12px; border-radius: 3px; display: inline-block;
}}

@media (max-width: 600px) {{
  .cell {{ min-height: 56px; padding: 4px; }}
  .day-num {{ font-size: 12px; }}
  .badge {{ font-size: 9px; bottom: 3px; right: 4px; }}
}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📅 外贸节假日日历<small>{month_name_zh}</small></h1>
    <div class="nav">
      <button onclick="location.search='?y={prev_y}&m={prev_m}'" title="上月">←</button>
      <button onclick="location.search='?y={next_y}&m={next_m}'" title="下月">→</button>
    </div>
  </div>

  <div class="filters">
    <button class="active" onclick="filterRegion(this,'all')">全部</button>
    <button class="filter-hk" onclick="filterRegion(this,'仓库（香港）')">📦 香港仓库</button>
    <button class="filter-mideast" onclick="filterRegion(this,'中东')">🕌 中东</button>
    <button class="filter-europe" onclick="filterRegion(this,'欧洲')">🏰 欧洲</button>
    <button class="filter-ca" onclick="filterRegion(this,'中亚')">🏔️ 中亚</button>
    <button class="filter-ru" onclick="filterRegion(this,'俄罗斯及周边')">❄️ 俄罗斯</button>
  </div>

  <div class="cal-header">
    {"".join(f'<span>{d}</span>' for d in WEEKDAYS)}
  </div>
  <div class="cal-grid">
    {grid_html}
  </div>

  <div class="legend">
    <span><span class="legend-dot" style="background:#FFF;border:1px solid #E8E5E0"></span> 无假日</span>
    <span><span class="legend-dot" style="background:#FEF9EF"></span> 1-3国</span>
    <span><span class="legend-dot" style="background:#FDEDC8"></span> 4-9国</span>
    <span><span class="legend-dot" style="background:#FBDBA7"></span> 10国+</span>
    <span style="border:2px solid #1A1A1A;border-radius:4px;width:12px;height:12px"></span> 今天</span>
  </div>

  <div class="preview">
    <h2>📌 今日 & 未来3天</h2>
    {preview_html}
  </div>

  <div class="footer">
    覆盖 {len(COUNTRIES)} 个国家/地区 · 数据更新于 {datetime.now().strftime("%Y-%m-%d %H:%M")} · 伊斯兰假日日期为估算（±1-2天）
  </div>
</div>

<!-- Day Detail Modal -->
<div class="overlay" id="overlay" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <div class="modal-header">
      <h3 id="modal-title"></h3>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div id="modal-body"></div>
  </div>
</div>

<script>
const DATA = {holidays_json};
const REGION_ORDER = ["仓库（香港）","中东","欧洲","中亚","俄罗斯及周边"];
const WEEKDAYS = ["周日","周一","周二","周三","周四","周五","周六"];
let currentFilter = "all";

function filterRegion(btn, region) {{
  document.querySelectorAll('.filters button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  currentFilter = region;
  // Update badge counts
  document.querySelectorAll('.cell[data-day]').forEach(cell => {{
    const day = cell.dataset.day;
    const entries = DATA[day] || [];
    const filtered = region === "all" ? entries : entries.filter(e => e.region === region);
    const count = new Set(filtered.map(e => e.cc)).size;
    const badge = cell.querySelector('.badge');
    // Update visual
    cell.classList.remove('mild','warm','hot','has-holiday');
    if (count > 0) {{
      cell.classList.add('has-holiday');
      if (count >= 10) cell.classList.add('hot');
      else if (count >= 4) cell.classList.add('warm');
      else cell.classList.add('mild');
    }}
    if (badge) badge.textContent = count > 0 ? count + '国' : '';
    if (!badge && count > 0) {{
      const b = document.createElement('span');
      b.className = 'badge'; b.textContent = count + '国';
      cell.appendChild(b);
    }}
  }});
}}

function showDay(day) {{
  const entries = DATA[day] || [];
  const filtered = currentFilter === "all" ? entries : entries.filter(e => e.region === currentFilter);
  const d = new Date({year}, {month - 1}, day);
  const wd = WEEKDAYS[d.getDay()];
  document.getElementById('modal-title').textContent =
    `{year}-${{String({month}).padStart(2,'0')}}-${{String(day).padStart(2,'0')}} ${{wd}}`;

  const body = document.getElementById('modal-body');
  if (filtered.length === 0) {{
    body.innerHTML = '<div class="no-holidays">✅ 该日无节假日</div>';
  }} else {{
    // Group by region
    const byRegion = {{}};
    filtered.forEach(e => {{
      if (!byRegion[e.region]) byRegion[e.region] = [];
      byRegion[e.region].push(e);
    }});
    let html = '';
    REGION_ORDER.forEach(r => {{
      if (!byRegion[r]) return;
      const emoji = {{"仓库（香港）":"📦","中东":"🕌","欧洲":"🏰","中亚":"🏔️","俄罗斯及周边":"❄️"}}[r]||"";
      html += `<div class="modal-region"><div class="modal-region-title">${{emoji}} ${{r}}</div>`;
      byRegion[r].forEach(e => {{
        let spanText = e.span > 1
          ? `连休${{e.span}}天（${{e.span_s.slice(5).replace('-','/')}} - ${{e.span_e.slice(5).replace('-','/')}}）`
          : '放假1天';
        html += `<div class="modal-entry">
          <div class="me-country">${{e.zh}}</div>
          <div class="me-holiday">${{e.name_zh}} / ${{e.name_en}}</div>
          <div class="me-span">${{spanText}}</div>
          ${{e.cc === 'HK' ? '<div class="me-hk">⚠️ 香港仓库休息，注意发货安排</div>' : ''}}
        </div>`;
      }});
      html += '</div>';
    }});
    body.innerHTML = html;
  }}
  document.getElementById('overlay').classList.add('show');
}}

function closeModal() {{
  document.getElementById('overlay').classList.remove('show');
}}
document.addEventListener('keydown', e => {{ if(e.key==='Escape') closeModal(); }});
</script>
</body>
</html>'''
    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description="生成节假日日历网页")
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--month", type=int, default=datetime.now().month)
    parser.add_argument("--output", default=os.path.join(SCRIPT_DIR, "..", "docs", "index.html"))
    args = parser.parse_args()

    print(f"📅 正在生成 {args.year}年{args.month}月 节假日日历...", file=sys.stderr)
    holidays = fetch_month_holidays(args.year, args.month)

    total_entries = sum(len(v) for v in holidays.values())
    print(f"✅ 获取到 {len(holidays)} 天有假日，共 {total_entries} 条记录", file=sys.stderr)

    html = generate_html(args.year, args.month, holidays)

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🌐 网页已生成: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
