#!/usr/bin/env python3
"""news-digest の表示機能「月齢」：その日の月齢と月相を、HTML 断片にして出力する。

使い方: python3 .claude/skills/news-digest/features/moon.py YYYY-MM-DD
  外部 API は使わず、基準の新月からの経過日数で計算する（標準ライブラリのみ）。
  日本時間のその日の正午の月齢を求める。平均の朔望月による近似で、実際の月相とは±約0.5日ずれうる。
終了コード: 0 成功 / 2 引数の誤り
"""
import argparse
import datetime
import sys

SYNODIC = 29.530588853  # 朔望月（日）
EPOCH = datetime.datetime(2000, 1, 6, 18, 14, tzinfo=datetime.timezone.utc)  # 基準の新月
JST = datetime.timezone(datetime.timedelta(hours=9))

# 月齢を 8 等分した区分（新月・満月は前後 1/16 周期を含む）
PHASES = [
    ("🌑", "新月"),
    ("🌒", "三日月"),
    ("🌓", "上弦の月"),
    ("🌔", "満ちていく月"),
    ("🌕", "満月"),
    ("🌖", "欠けていく月"),
    ("🌗", "下弦の月"),
    ("🌘", "有明の月"),
]


def moon_age(date):
    """date（その日の日本時間の正午）の月齢を日数で返す。"""
    t = datetime.datetime(date.year, date.month, date.day, 12, tzinfo=JST)
    return ((t - EPOCH).total_seconds() / 86400) % SYNODIC


def phase(age):
    return PHASES[int((age / SYNODIC * 8 + 0.5) % 8)]


def render(date):
    age = moon_age(date)
    icon, name = phase(age)
    to_new = SYNODIC - age
    to_full = (SYNODIC / 2 - age) % SYNODIC
    return f"""<section class="feature moon">
    <h2>月齢</h2>
    <p class="summary"><span role="img" aria-label="{name}">{icon}</span> 月齢 {age:.1f}　{name}</p>
    <p class="detail">次の満月まで 約{to_full:.0f}日 / 次の新月まで 約{to_new:.0f}日</p>
  </section>"""


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("date")
    a = p.parse_args()
    try:
        date = datetime.date.fromisoformat(a.date)
    except ValueError:
        p.error("date は YYYY-MM-DD で指定する")
    print(render(date))
    return 0


if __name__ == "__main__":
    sys.exit(main())
