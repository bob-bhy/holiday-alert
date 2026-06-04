---
name: holiday-alert
description: >
  外贸节假日提醒 — 每天自动扫描未来3天内66个国家（中东、欧洲、中亚、俄罗斯及周边）的公共假日，
  格式化为清爽的中文摘要，推送到企业微信群。支持定时自动推送和手动查询两种模式。
  当用户提到"节假日提醒"、"假日推送"、"holiday alert"、"哪些国家放假"、"客户那边放假吗"、
  "查一下节假日"、"开斋节/圣诞节/国庆放假"等与外贸目标市场假日相关的话题时触发。
  也在定时任务每天10:00自动触发。
---

# Holiday Alert — 外贸节假日提醒

## 工作原理

1. **Python 脚本**调用 [Nager.Date API](https://date.nager.at) 获取已支持国家的假日数据
2. 对 API **未覆盖**的国家（主要是中东、部分中亚），用 **WebSearch** 实时补充
3. 汇总后格式化为清爽的企微 Markdown 消息，推送到群机器人

## 覆盖范围（66国）

| 区域 | 国家 |
|------|------|
| 中东 | 沙特、伊朗、阿联酋、以色列、阿曼、卡塔尔、巴勒斯坦、约旦、黎巴嫩、科威特、巴林、伊拉克、叙利亚、土耳其 |
| 欧洲 | 德法英意西葡荷比丹瑞士瑞典挪威芬兰冰岛爱尔兰卢森堡奥地利捷克波兰匈牙利斯洛伐克希腊罗马尼亚保加利亚塞尔维亚克罗地亚斯洛文尼亚波黑马其顿阿尔巴尼亚摩尔多瓦乌克兰拉脱维亚立陶宛爱沙尼亚塞浦路斯马耳他安道尔梵蒂冈圣马力诺摩纳哥 |
| 中亚 | 哈萨克斯坦、阿塞拜疆、格鲁吉亚、亚美尼亚、吉尔吉斯斯坦、土库曼斯坦、乌兹别克斯坦、塔吉克斯坦 |
| 俄罗斯及周边 | 俄罗斯、白俄罗斯 |

## 执行步骤

每次触发时按以下顺序执行：

### Step 1：运行脚本获取 API 数据

```bash
python "SKILL_DIR/scripts/holiday_alert.py" --fetch-only --days 3
```

脚本输出 JSON，包含：
- `holidays`：按日期分组的假日列表（来自 Nager.Date API 的国家）
- `unsupported_countries`：API 未覆盖的国家代码列表
- `unsupported_names`：对应的中文名

### Step 2：补充未覆盖国家

对 `unsupported_countries` 中的每个国家，用 WebSearch 搜索：
- 搜索词：`{国家英文名} public holidays {年份}` 或 `{国家英文名} holidays {月份} {年份}`
- 只需要检查**未来3天**内是否有假日
- 如果有，构造补充数据：

```json
[
  {
    "country_code": "SA",
    "country_zh": "沙特阿拉伯",
    "country_en": "Saudi Arabia",
    "region": "中东",
    "name": "开斋节",
    "name_en": "Eid al-Fitr",
    "date": "2026-03-20"
  }
]
```

将补充数据写入临时文件 `extra_holidays.json`。

### Step 3：生成消息并推送

如果有补充数据：
```bash
python "SKILL_DIR/scripts/holiday_alert.py" --extra-holidays extra_holidays.json
```

如果没有补充数据（所有未覆盖国家未来3天无假日）：
```bash
python "SKILL_DIR/scripts/holiday_alert.py"
```

脚本会自动从 `scripts/config.json` 读取 webhook URL 并推送。
如果 webhook 未配置，仅输出消息内容到控制台。

### Step 4：汇报结果

向用户简要汇报：
- 推送是否成功
- 共发现多少条假日
- 如果有推送失败，给出原因

## 配置

企微 webhook URL 存储在 `SKILL_DIR/scripts/config.json`：

```json
{
    "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
}
```

用户提供 webhook 地址后，更新此文件即可。

## 消息格式示例

```
📅 **外贸节假日提醒**
2026-05-27（周三）至 2026-05-29（周五）

**2026-05-27 周三**  🔴 3个国家/地区放假
> 🕌 **中东**
> · 沙特阿拉伯 — عيد الأضحى（Eid al-Adha）
> · 阿联酋 — عيد الأضحى（Eid al-Adha）
> 🏰 **欧洲**
> · 德国 — Christi Himmelfahrt（Ascension Day）

**2026-05-28 周四**  ✅ 无节假日

**2026-05-29 周五**  ✅ 无节假日

────────────────────
⚠️ 未来3天共 **3** 条假日，注意跟单节奏
🔍 覆盖66国 · 10:00更新
```

## 定时推送设置

使用 `/schedule` 创建每天10:00的定时任务：
- Cron: `0 10 * * *`（北京时间）
- 任务：执行本 skill 的完整流程（Step 1-4）

## 手动触发

用户随时可以说"查一下节假日"或"哪些国家放假"来手动触发。
手动触发时同样执行完整流程，结果既推送到企微也在对话中展示。
