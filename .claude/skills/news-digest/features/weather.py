#!/usr/bin/env python3
"""news-digest の表示機能「天気」：1地域のその日の予報を、時刻ごとの表にした HTML 断片を出力する。

使い方: python3 .claude/skills/news-digest/features/weather.py YYYY-MM-DD 緯度 経度 地域名 [--step 時間]
  予報は Open-Meteo（キー不要）から取る。時刻はその地域の現地時刻。
  --step は表の間隔（時間）。既定は 3（0, 3, ..., 21 時）。24 の約数のみ。
終了コード: 0 成功 / 2 引数の誤り / 3 予報を取得できなかった（取得できなかった旨の断片を出力する）
"""
import argparse
import datetime
import html
import json
import sys
import urllib.parse
import urllib.request

API = "https://api.open-meteo.com/v1/forecast"

# WMO weather code → (昼のアイコン, 夜のアイコン, 説明)
CODES = {
    0: ("☀️", "🌙", "快晴"),
    1: ("🌤️", "🌙", "晴れ"),
    2: ("⛅", "☁️", "晴れ時々曇り"),
    3: ("☁️", "☁️", "曇り"),
    45: ("🌫️", "🌫️", "霧"),
    48: ("🌫️", "🌫️", "着氷性の霧"),
    51: ("🌦️", "🌧️", "弱い霧雨"),
    53: ("🌦️", "🌧️", "霧雨"),
    55: ("🌧️", "🌧️", "強い霧雨"),
    56: ("🌧️", "🌧️", "着氷性の霧雨"),
    57: ("🌧️", "🌧️", "強い着氷性の霧雨"),
    61: ("🌧️", "🌧️", "弱い雨"),
    63: ("🌧️", "🌧️", "雨"),
    65: ("☔", "☔", "強い雨"),
    66: ("🌧️", "🌧️", "着氷性の雨"),
    67: ("☔", "☔", "強い着氷性の雨"),
    71: ("🌨️", "🌨️", "弱い雪"),
    73: ("🌨️", "🌨️", "雪"),
    75: ("❄️", "❄️", "強い雪"),
    77: ("🌨️", "🌨️", "霧雪"),
    80: ("🌦️", "🌧️", "にわか雨"),
    81: ("🌧️", "🌧️", "強いにわか雨"),
    82: ("☔", "☔", "激しいにわか雨"),
    85: ("🌨️", "🌨️", "にわか雪"),
    86: ("❄️", "❄️", "強いにわか雪"),
    95: ("⛈️", "⛈️", "雷雨"),
    96: ("⛈️", "⛈️", "ひょうを伴う雷雨"),
    99: ("⛈️", "⛈️", "強いひょうを伴う雷雨"),
}

ATTRIBUTION = '<a href="https://open-meteo.com/">Open-Meteo</a>'


def icon(code, is_day=True):
    day, night, desc = CODES.get(code, ("❔", "❔", "不明"))
    return (day if is_day else night), desc


def fmt_temp(t):
    return "–" if t is None else f"{round(t)}℃"


def fmt_pct(p):
    return "–" if p is None else f"{p}%"


def fetch(date, lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "weather_code,temperature_2m,precipitation_probability,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "start_date": date,
        "end_date": date,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "news-digest-weather"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def render(data, name, step):
    h = data["hourly"]
    d = data["daily"]
    offset = datetime.timedelta(seconds=data.get("utc_offset_seconds", 0))
    now = datetime.datetime.now(datetime.timezone(offset))

    day_icon, day_desc = icon(d["weather_code"][0])
    summary = (
        f"{day_icon} {day_desc}　最高 {fmt_temp(d['temperature_2m_max'][0])}"
        f" / 最低 {fmt_temp(d['temperature_2m_min'][0])}"
        f" / 降水確率 最大 {fmt_pct(d['precipitation_probability_max'][0])}"
    )

    hours, icons, temps, pops = [], [], [], []
    for i, t in enumerate(h["time"]):
        hour = int(t[11:13])
        if hour % step:
            continue
        ic, desc = icon(h["weather_code"][i], bool(h["is_day"][i]))
        pop = h["precipitation_probability"][i]
        hours.append(f"<th scope=\"col\">{hour}</th>")
        icons.append(f'<td class="icon" title="{desc}"><span role="img" aria-label="{desc}">{ic}</span></td>')
        temps.append(f"<td>{fmt_temp(h['temperature_2m'][i])}</td>")
        cls = ' class="wet"' if pop is not None and pop >= 50 else ""
        pops.append(f"<td{cls}>{fmt_pct(pop)}</td>")

    return f"""<section class="feature weather">
    <h2>天気 — {html.escape(name)}</h2>
    <p class="summary">{summary}</p>
    <div class="scroll">
      <table>
        <tr><th scope="row">時刻</th>{''.join(hours)}</tr>
        <tr><th scope="row">天気</th>{''.join(icons)}</tr>
        <tr><th scope="row">気温</th>{''.join(temps)}</tr>
        <tr><th scope="row">降水</th>{''.join(pops)}</tr>
      </table>
    </div>
    <p class="note">{now:%H:%M}（現地時刻）時点の予報。データ: {ATTRIBUTION}</p>
  </section>"""


def render_error(name):
    return f"""<section class="feature weather">
    <h2>天気 — {html.escape(name)}</h2>
    <p class="note">予報を取得できませんでした。データ: {ATTRIBUTION}</p>
  </section>"""


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("date")
    p.add_argument("lat", type=float)
    p.add_argument("lon", type=float)
    p.add_argument("name")
    p.add_argument("--step", type=int, default=3)
    a = p.parse_args()
    try:
        datetime.date.fromisoformat(a.date)
    except ValueError:
        p.error("date は YYYY-MM-DD で指定する")
    if not (-90 <= a.lat <= 90 and -180 <= a.lon <= 180):
        p.error("緯度・経度の範囲が不正")
    if a.step < 1 or 24 % a.step:
        p.error("--step は 24 の約数（1, 2, 3, 4, 6, 8, 12, 24）")

    try:
        data = fetch(a.date, a.lat, a.lon)
        out = render(data, a.name, a.step)
    except Exception as e:  # ネットワーク・API・応答形式の失敗はまとめて扱う
        print(render_error(a.name))
        print(f"error: 予報を取得できませんでした: {e}", file=sys.stderr)
        return 3
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
