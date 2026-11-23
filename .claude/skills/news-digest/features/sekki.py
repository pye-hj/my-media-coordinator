#!/usr/bin/env python3
"""news-digest の表示機能「二十四節気」：その日の二十四節気と七十二候を、HTML 断片にして出力する。

使い方: python3 .claude/skills/news-digest/features/sekki.py YYYY-MM-DD
  外部 API は使わず、太陽の視黄経（Meeus『Astronomical Algorithms』25章の低精度式、誤差 0.01° 程度）から計算する。
  黄経が 15° の倍数を通る日が二十四節気の節入り、5° の倍数を通る日が七十二候の始まり（日本時間の日付）。
  七十二候は本朝七十二候（略本暦）による。
  断片の {{essay}} は、ダイジェストを書くときに季節の短い文章で置き換える（features/sekki.md）。
終了コード: 0 成功 / 2 引数の誤り
"""
import argparse
import datetime
import math
import sys

JST = datetime.timezone(datetime.timedelta(hours=9))
J2000 = datetime.datetime(2000, 1, 1, 12, tzinfo=datetime.timezone.utc)
DELTA_T = 69.0  # TT − UT（秒）。節入りの日付を決めるには十分な精度

# 立春（黄経 315°）から順に
SEKKI = [
    ("立春", "りっしゅん"), ("雨水", "うすい"), ("啓蟄", "けいちつ"), ("春分", "しゅんぶん"),
    ("清明", "せいめい"), ("穀雨", "こくう"), ("立夏", "りっか"), ("小満", "しょうまん"),
    ("芒種", "ぼうしゅ"), ("夏至", "げし"), ("小暑", "しょうしょ"), ("大暑", "たいしょ"),
    ("立秋", "りっしゅう"), ("処暑", "しょしょ"), ("白露", "はくろ"), ("秋分", "しゅうぶん"),
    ("寒露", "かんろ"), ("霜降", "そうこう"), ("立冬", "りっとう"), ("小雪", "しょうせつ"),
    ("大雪", "たいせつ"), ("冬至", "とうじ"), ("小寒", "しょうかん"), ("大寒", "だいかん"),
]

# 本朝七十二候（略本暦）。立春の初候から順に（名前、読み、意味）
KOU = [
    ("東風解凍", "はるかぜこおりをとく", "春の風が川や湖の氷を解かし始める"),
    ("黄鶯睍睆", "うぐいすなく", "鶯が山里で鳴き始める"),
    ("魚上氷", "うおこおりをいずる", "割れた氷の間から魚が跳ねる"),
    ("土脉潤起", "つちのしょううるおいおこる", "雨が降って土が湿り気を含む"),
    ("霞始靆", "かすみはじめてたなびく", "霞がたなびき始める"),
    ("草木萌動", "そうもくめばえいずる", "草木が芽吹き始める"),
    ("蟄虫啓戸", "すごもりむしとをひらく", "冬ごもりの虫が出てくる"),
    ("桃始笑", "ももはじめてさく", "桃の花が咲き始める"),
    ("菜虫化蝶", "なむしちょうとなる", "青虫が羽化して紋白蝶になる"),
    ("雀始巣", "すずめはじめてすくう", "雀が巣を作り始める"),
    ("桜始開", "さくらはじめてひらく", "桜の花が咲き始める"),
    ("雷乃発声", "かみなりすなわちこえをはっす", "遠くで雷の音がし始める"),
    ("玄鳥至", "つばめきたる", "燕が南からやってくる"),
    ("鴻雁北", "こうがんかえる", "雁が北へ渡っていく"),
    ("虹始見", "にじはじめてあらわる", "雨の後に虹が出始める"),
    ("葭始生", "あしはじめてしょうず", "葦が芽を吹き始める"),
    ("霜止出苗", "しもやんでなえいずる", "霜が終わり稲の苗が育つ"),
    ("牡丹華", "ぼたんはなさく", "牡丹の花が咲く"),
    ("蛙始鳴", "かわずはじめてなく", "蛙が鳴き始める"),
    ("蚯蚓出", "みみずいずる", "蚯蚓が地上に這い出る"),
    ("竹笋生", "たけのこしょうず", "筍が生えてくる"),
    ("蚕起食桑", "かいこおきてくわをはむ", "蚕が桑を盛んに食べ始める"),
    ("紅花栄", "べにばなさかう", "紅花が盛んに咲く"),
    ("麦秋至", "むぎのときいたる", "麦が熟し麦秋となる"),
    ("螳螂生", "かまきりしょうず", "螳螂が生まれ出る"),
    ("腐草為螢", "くされたるくさほたるとなる", "草の陰で蛍が光を放ち始める"),
    ("梅子黄", "うめのみきばむ", "梅の実が黄ばんで熟す"),
    ("乃東枯", "なつかれくさかるる", "夏枯草（うつぼぐさ）が枯れる"),
    ("菖蒲華", "あやめはなさく", "あやめの花が咲く"),
    ("半夏生", "はんげしょうず", "烏柄杓（からすびしゃく）が生える"),
    ("温風至", "あつかぜいたる", "暖かい風が吹いてくる"),
    ("蓮始開", "はすはじめてひらく", "蓮の花が開き始める"),
    ("鷹乃学習", "たかすなわちわざをならう", "鷹の幼鳥が飛ぶことを覚える"),
    ("桐始結花", "きりはじめてはなをむすぶ", "桐の実がなり始める"),
    ("土潤溽暑", "つちうるおうてむしあつし", "土が湿って蒸し暑くなる"),
    ("大雨時行", "たいうときどきふる", "時として大雨が降る"),
    ("涼風至", "すずかぜいたる", "涼しい風が立ち始める"),
    ("寒蝉鳴", "ひぐらしなく", "蜩が鳴き始める"),
    ("蒙霧升降", "ふかききりまとう", "深い霧が立ち込める"),
    ("綿柎開", "わたのはなしべひらく", "綿を包む萼（がく）が開く"),
    ("天地始粛", "てんちはじめてさむし", "ようやく暑さが鎮まる"),
    ("禾乃登", "こくものすなわちみのる", "稲が実る"),
    ("草露白", "くさのつゆしろし", "草に降りた露が白く光る"),
    ("鶺鴒鳴", "せきれいなく", "鶺鴒が鳴き始める"),
    ("玄鳥去", "つばめさる", "燕が南へ帰っていく"),
    ("雷乃収声", "かみなりすなわちこえをおさむ", "雷が鳴り響かなくなる"),
    ("蟄虫坏戸", "むしかくれてとをふさぐ", "虫が土中に掘った穴をふさぐ"),
    ("水始涸", "みずはじめてかるる", "田畑の水を干し始める"),
    ("鴻雁来", "こうがんきたる", "雁が飛来し始める"),
    ("菊花開", "きくのはなひらく", "菊の花が咲く"),
    ("蟋蟀在戸", "きりぎりすとにあり", "蟋蟀が戸の辺りで鳴く"),
    ("霜始降", "しもはじめてふる", "霜が降り始める"),
    ("霎時施", "こさめときどきふる", "小雨がしとしと降る"),
    ("楓蔦黄", "もみじつたきばむ", "もみじや蔦が黄葉する"),
    ("山茶始開", "つばきはじめてひらく", "山茶花が咲き始める"),
    ("地始凍", "ちはじめてこおる", "大地が凍り始める"),
    ("金盞香", "きんせんかさく", "水仙の花が咲く"),
    ("虹蔵不見", "にじかくれてみえず", "虹を見かけなくなる"),
    ("朔風払葉", "きたかぜこのはをはらう", "北風が木の葉を払い除ける"),
    ("橘始黄", "たちばなはじめてきばむ", "橘の実が黄色くなり始める"),
    ("閉塞成冬", "そらさむくふゆとなる", "天地の気が塞がって冬となる"),
    ("熊蟄穴", "くまあなにこもる", "熊が冬眠のために穴に隠れる"),
    ("鱖魚群", "さけのうおむらがる", "鮭が群がり川を上る"),
    ("乃東生", "なつかれくさしょうず", "夏枯草が芽を出す"),
    ("麋角解", "さわしかつのおつる", "大鹿が角を落とす"),
    ("雪下出麦", "ゆきわたりてむぎのびる", "雪の下で麦が芽を出す"),
    ("芹乃栄", "せりすなわちさかう", "芹がよく生育する"),
    ("水泉動", "しみずあたたかをふくむ", "地中で凍った泉が動き始める"),
    ("雉始雊", "きじはじめてなく", "雄の雉が鳴き始める"),
    ("款冬華", "ふきのはなさく", "蕗の薹（ふきのとう）が蕾を出す"),
    ("水沢腹堅", "さわみずこおりつめる", "沢に氷が厚く張りつめる"),
    ("鶏始乳", "にわとりはじめてとやにつく", "鶏が卵を産み始める"),
]
KOU_ORDER = ["初候", "次候", "末候"]
# 立春・立夏・立秋・立冬から6つずつ（class 名、表示）
SEASONS = [("spring", "春"), ("summer", "夏"), ("autumn", "秋"), ("winter", "冬")]


def solar_longitude(t):
    """時刻 t（aware datetime）の太陽の視黄経（度、0〜360）。"""
    jc = ((t - J2000).total_seconds() + DELTA_T) / 86400 / 36525
    l0 = 280.46646 + 36000.76983 * jc + 0.0003032 * jc * jc
    m = math.radians(357.52911 + 35999.05029 * jc - 0.0001537 * jc * jc)
    c = ((1.914602 - 0.004817 * jc - 0.000014 * jc * jc) * math.sin(m)
         + (0.019993 - 0.000101 * jc) * math.sin(2 * m)
         + 0.000289 * math.sin(3 * m))
    omega = math.radians(125.04 - 1934.136 * jc)
    return (l0 + c - 0.00569 - 0.00478 * math.sin(omega)) % 360


def crossing(deg, lo, hi):
    """lo〜hi の間で太陽の視黄経が deg を通る時刻（二分法）。"""
    def f(t):
        return (solar_longitude(t) - deg + 180) % 360 - 180
    for _ in range(50):
        mid = lo + (hi - lo) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return lo


def start_date(deg, around):
    """黄経 deg を around の前後 8 日以内で通る日（日本時間の日付）。"""
    span = datetime.timedelta(days=8)
    return crossing(deg, around - span, around + span).astimezone(JST).date()


def md(d):
    return f"{d.month}月{d.day}日"


def info(date):
    end_of_day = datetime.datetime(date.year, date.month, date.day, tzinfo=JST) + datetime.timedelta(days=1)
    k = int(solar_longitude(end_of_day) // 5)  # 今の候（黄経 0° の春分の初候が 0）
    kou_start = start_date(k * 5, end_of_day - datetime.timedelta(days=3))
    kou_next = start_date((k + 1) * 5 % 360, end_of_day + datetime.timedelta(days=3))
    s = k // 3
    sub = k % 3
    sekki_start = start_date(s * 15, end_of_day - datetime.timedelta(days=5 * sub + 3))
    sekki_next = start_date((s + 1) * 15 % 360, end_of_day + datetime.timedelta(days=5 * (2 - sub) + 3))
    si = (s + 3) % 24  # 立春起点の番号
    return {
        "index": si,
        "sekki": SEKKI[si], "next_sekki": SEKKI[(si + 1) % 24],
        "kou": KOU[si * 3 + sub], "next_kou": KOU[(si * 3 + sub + 1) % 72], "kou_order": KOU_ORDER[sub],
        "sekki_start": sekki_start, "sekki_next": sekki_next,
        "kou_start": kou_start, "kou_next": kou_next,
    }


def render(date):
    i = info(date)
    name, yomi = i["sekki"]
    kname, kyomi, kmean = i["kou"]
    today = '<span class="today">今日から</span>'
    sekki_mark = today if i["sekki_start"] == date else ""
    kou_mark = today if i["kou_start"] == date and not sekki_mark else ""
    last = i["sekki_next"] - datetime.timedelta(days=1)
    to_kou = (i["kou_next"] - date).days
    to_sekki = (i["sekki_next"] - date).days
    if i["kou_next"] == i["sekki_next"]:
        detail = f"次の節気「{i['next_sekki'][0]}」まで あと{to_sekki}日"
    else:
        detail = f"次の候「{i['next_kou'][0]}」まで あと{to_kou}日 / 次の節気「{i['next_sekki'][0]}」まで あと{to_sekki}日"
    season = SEASONS[i["index"] // 6]
    return f"""<section class="feature sekki {season[0]}">
    <h2>二十四節気</h2>
    <p class="summary">{sekki_mark}<span class="name">{name}</span><span class="yomi">{yomi}</span><span class="span">{md(i['sekki_start'])}〜{md(last)}</span></p>
    <p class="kou">{kou_mark}{i['kou_order']}　{kname}<span class="yomi">{kyomi}</span><span class="mean">{kmean}</span></p>
    <p class="essay">{{{{essay}}}}</p>
    {wheel(i['index'])}
    <p class="detail">{detail}</p>
  </section>"""


def wheel(index):
    """立春から大寒までの24の節気を季節ごとに並べた帯。今の節気を強調し、過ぎた節気を淡く塗る。"""
    groups = []
    for g, (cls, label) in enumerate(SEASONS):
        ticks = "".join(
            f'<i class="{"now" if n == index else "past" if n < index else ""}"></i>'.replace(' class=""', "")
            for n in range(g * 6, g * 6 + 6)
        )
        groups.append(f'<span class="{cls}">{ticks}<b>{label}</b></span>')
    name = SEKKI[index][0]
    return f'<div class="wheel" role="img" aria-label="立春から数えて{index + 1}番目の節気、{name}">{"".join(groups)}</div>'


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
