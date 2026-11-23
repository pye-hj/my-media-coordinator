#!/usr/bin/env python3
"""news-digest の表示機能「天気」：1地域のその日の予報を、時刻ごとの表にした HTML 断片を出力する。

使い方: python3 .claude/skills/news-digest/features/weather.py YYYY-MM-DD 地域名 [--step 時間]
  予報は気象庁の防災情報 JSON（キー不要）から取る。日本国内のみ。時刻は日本時間。
  地域名は市区町村名（「東京都千代田区」「札幌市」など）、気象庁の一次細分区域名（「東京地方」など）、
  都道府県名、または気象庁の地域コードで指定する。同名の市町村がある場合は都道府県名を前に付ける。
  --step は表の間隔（時間）。3 または 6。既定は 3。
  表は指定日以降で発表済みの最初の時刻から 24 時間分（日付をまたぐ列には日付を添える）。
終了コード: 0 成功 / 2 引数の誤り（地域を特定できない場合を含む） /
          3 予報を取得できなかった（取得できなかった旨の断片を出力する）
"""
import argparse
import datetime
import html
import json
import re
import sys
import urllib.request

BASE = "https://www.jma.go.jp/bosai"
AREA_URL = f"{BASE}/common/const/area.json"
FORECAST_URL = f"{BASE}/forecast/data/forecast/{{office}}.json"
HOURLY_URL = f"{BASE}/jmatile/data/wdist/VPFD/{{class10}}.json"
PAGE_URL = "https://www.jma.go.jp/bosai/forecast/#area_type=class10s&area_code={class10}"

JST = datetime.timezone(datetime.timedelta(hours=9))
ATTRIBUTION = '<a href="https://www.jma.go.jp/bosai/forecast/">気象庁</a>'


class AreaError(Exception):
    pass


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "news-digest-weather"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


# ---- 地域の特定 -------------------------------------------------------------

def _norm(s):
    return re.sub(r"\s+", "", s)


def _pref_ok(prefix, office_code, areas):
    """地域名の前に付いた都道府県などの文字列が、その区域の府県予報区と矛盾しないか。"""
    prefix = re.sub(r"[都道府県]$", "", prefix)
    if not prefix:
        return True
    office = areas["offices"][office_code]
    center = areas["centers"].get(office.get("parent", ""), {})
    return any(prefix in n for n in (office["name"], office.get("officeName", ""), center.get("name", "")))


def class10_of_class20(code, areas):
    c15 = areas["class20s"][code]["parent"]
    return areas["class15s"][c15]["parent"]


def resolve(query, areas):
    """地域名（またはコード）から一次細分区域（class10）のコードを返す。"""
    q = _norm(query)
    if q in areas["class20s"]:
        return class10_of_class20(q, areas)
    if q in areas["class10s"]:
        return q
    if q in areas["offices"]:
        return areas["offices"][q]["children"][0]

    # 市区町村（class20）。「横浜市北部」のような分割区域は「横浜市」として扱う。
    found = {}
    for code, a in areas["class20s"].items():
        name = a["name"]
        base = re.sub(r"(北部|南部|東部|西部|中部)$", "", name)
        for n in {name, base}:
            i = q.find(n)
            if i < 0 or len(n) < 2:
                continue
            c10 = class10_of_class20(code, areas)
            office = areas["class10s"][c10]["parent"]
            if _pref_ok(q[:i], office, areas):
                found.setdefault(len(n), {})[c10] = name
    if found:
        best = found[max(found)]
        if len(best) == 1:
            return next(iter(best))
        offices = {areas["class10s"][c]["parent"] for c in best}
        if len(offices) == 1:  # 「仙台市東部・西部」のように同じ府県内で分かれる場合は代表の区域
            order = areas["offices"][offices.pop()]["children"]
            return min(best, key=lambda c: order.index(c) if c in order else len(order))
        cands = "、".join(
            f"{n}（{areas['offices'][areas['class10s'][c]['parent']]['name']}）" for c, n in best.items()
        )
        raise AreaError(f"「{query}」に当たる地域が複数ある: {cands}。都道府県名を前に付けて指定する")

    # 一次細分区域・府県予報区（都道府県）
    for key, pick in (("class10s", lambda c, a: c), ("offices", lambda c, a: a["children"][0])):
        for code, a in areas[key].items():
            name = a["name"]
            if q == name or q == re.sub(r"[都道府県]$", "", name) or re.sub(r"[都道府県]$", "", q) == name:
                return pick(code, a)
    raise AreaError(f"「{query}」に当たる地域が見つからない（気象庁の予報は日本国内のみ）")


# ---- アイコン ---------------------------------------------------------------

def icon_for(text, is_day=True):
    """気象庁の天気の文言から (アイコン, 説明) を返す。"""
    t = text.replace("　", " ").strip()
    head = t.split(" ")[0]
    if "雷" in head:
        ic = "⛈️"
    elif "雪" in head and "雨" in head:
        ic = "🌨️"
    elif "雪" in head:
        ic = "❄️" if "大雪" in t or "暴風雪" in t else "🌨️"
    elif "雨" in head:
        ic = "☔" if "激しく" in t or "強く" in t or "大雨" in t or "暴風雨" in t else "🌧️"
    elif "晴" in head:
        if "雨" in t or "雪" in t:
            ic = "🌦️" if is_day else "🌧️"
        elif "くもり" in t or "曇" in t:
            ic = "🌤️" if is_day else "☁️"
        else:
            ic = "☀️" if is_day else "🌙"
    elif "くもり" in head or "曇" in head:
        if "雨" in t or "雪" in t:
            ic = "🌧️" if "雨" in t else "🌨️"
        elif "晴" in t:
            ic = "⛅" if is_day else "☁️"
        else:
            ic = "☁️"
    elif "霧" in head:
        ic = "🌫️"
    else:
        ic = "❔"
    return ic, t


# ---- 表示 -------------------------------------------------------------------

def fmt_temp(t):
    return "–" if t in (None, "") else f"{round(float(t))}℃"


def fmt_pct(p):
    return "–" if p in (None, "") else f"{p}%"


def parse_time(s):
    return datetime.datetime.fromisoformat(s).astimezone(JST)


def build(date, class10, areas, step):
    office = areas["class10s"][class10]["parent"]
    hourly = get_json(HOURLY_URL.format(class10=class10))
    forecast = get_json(FORECAST_URL.format(office=office))[0]
    day = datetime.date.fromisoformat(date)

    # 日ごとの天気（府県天気予報）と 6 時間ごとの降水確率
    ts_weather, ts_pop = forecast["timeSeries"][0], forecast["timeSeries"][1]
    w_area = next(a for a in ts_weather["areas"] if a["area"]["code"] == class10)
    p_area = next(a for a in ts_pop["areas"] if a["area"]["code"] == class10)
    day_text = None
    for t, w in zip(ts_weather["timeDefines"], w_area["weathers"]):
        if parse_time(t).date() == day:
            day_text = w
    pops = []  # (開始時刻, 値)
    for t, p in zip(ts_pop["timeDefines"], p_area["pops"]):
        pops.append((parse_time(t), p))

    def pop_at(dt):
        for start, p in pops:
            if start <= dt < start + datetime.timedelta(hours=6):
                return p
        return None

    # 3 時間ごとの天気と気温（地域時系列予報）
    at = hourly["areaTimeSeries"]
    pt = hourly["pointTimeSeries"]
    weather_at = {parse_time(t["dateTime"]): w for t, w in zip(at["timeDefines"], at["weather"])}
    temp_at = {parse_time(t["dateTime"]): v for t, v in zip(pt["timeDefines"], pt["temperature"])}
    tmax = tmin = None
    for t, mx, mn in zip(pt["timeDefines"], pt["maxTemperature"], pt["minTemperature"]):
        if parse_time(t["dateTime"]).date() == day:
            tmax = mx if mx != "" else tmax
            tmin = mn if mn != "" else tmin

    # 発表時刻より前の最低・最高（例：5時発表の当日の最低）は気象庁も出さないので「–」のままにする。
    # 府県天気予報の気温欄にはこの場合も仮の値（最高と同じ値）が入るため、補完に使わない。

    day_pops = [int(p) for start, p in pops if start.date() == day and p != ""]
    if day_text is None and not any(dt.date() == day for dt in weather_at):
        raise ValueError(f"{date} の予報が発表されていない")

    if day_text is not None:
        day_icon, day_desc = icon_for(day_text)
    else:  # 日ごとの予報が無い場合は時系列の最頻値で代える
        texts = [w for dt, w in weather_at.items() if dt.date() == day]
        day_icon, day_desc = icon_for(max(set(texts), key=texts.count))
    summary = (
        f"{day_icon} {html.escape(day_desc)}　最高 {fmt_temp(tmax)}"
        f" / 最低 {fmt_temp(tmin)}"
        f" / 降水確率 最大 {fmt_pct(max(day_pops) if day_pops else None)}"
    )

    # 表は発表済みの最初の時刻から 24 時間分（発表前の時間帯は予報が無いため、日付の 0 時固定にしない）
    day_start = datetime.datetime(day.year, day.month, day.day, tzinfo=JST)
    slots = sorted(dt for dt in weather_at if dt >= day_start and dt.hour % step == 0)
    if not slots:
        raise ValueError(f"{date} 以降の時系列予報が無い")
    start = slots[0]

    hours, icons, temps, pop_cells = [], [], [], []
    prev_date = day
    for k in range(24 // step):
        dt = start + datetime.timedelta(hours=k * step)
        w = weather_at.get(dt)
        if w is None:
            ic, desc = "–", "予報なし"
        else:
            ic, desc = icon_for(w, 6 <= dt.hour < 18)
        pop = pop_at(dt)
        label = f"{dt.day}日 {dt.hour}" if dt.date() != prev_date else f"{dt.hour}"
        prev_date = dt.date()
        hours.append(f'<th scope="col">{label}</th>')
        icons.append(f'<td class="icon" title="{html.escape(desc)}"><span role="img" aria-label="{html.escape(desc)}">{ic}</span></td>')
        temps.append(f"<td>{fmt_temp(temp_at.get(dt))}</td>")
        cls = ' class="wet"' if pop not in (None, "") and int(pop) >= 50 else ""
        pop_cells.append(f"<td{cls}>{fmt_pct(pop)}</td>")

    report = parse_time(hourly["reportDateTime"])
    area_name = areas["class10s"][class10]["name"]
    office_name = areas["offices"][office]["name"]
    if office_name != area_name:
        area_name = f"{office_name} {area_name}"
    point = pt.get("pointNameJP", "")
    link = PAGE_URL.format(class10=class10)
    return summary, hours, icons, temps, pop_cells, report, area_name, point, link


def render(name, summary, hours, icons, temps, pops, report, area_name, point, link):
    where = html.escape(area_name) + (f"（気温は{html.escape(point)}）" if point else "")
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
    <p class="note"><a href="{link}">{where}</a>の予報。{report.month}月{report.day}日{report.hour}時 発表。データ: {ATTRIBUTION}</p>
  </section>"""


def render_error(name):
    return f"""<section class="feature weather">
    <h2>天気 — {html.escape(name)}</h2>
    <p class="note">予報を取得できませんでした。データ: {ATTRIBUTION}</p>
  </section>"""


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("date")
    p.add_argument("name")
    p.add_argument("--step", type=int, default=3)
    a = p.parse_args()
    try:
        datetime.date.fromisoformat(a.date)
    except ValueError:
        p.error("date は YYYY-MM-DD で指定する")
    if a.step not in (3, 6):
        p.error("--step は 3 または 6")

    try:
        areas = get_json(AREA_URL)
    except Exception as e:
        print(render_error(a.name))
        print(f"error: 予報を取得できませんでした: {e}", file=sys.stderr)
        return 3
    try:
        class10 = resolve(a.name, areas)
    except AreaError as e:
        p.error(str(e))

    try:
        out = render(a.name, *build(a.date, class10, areas, a.step))
    except Exception as e:  # ネットワーク・API・応答形式の失敗はまとめて扱う
        print(render_error(a.name))
        print(f"error: 予報を取得できませんでした: {e}", file=sys.stderr)
        return 3
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
