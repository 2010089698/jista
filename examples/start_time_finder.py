# start_time_finder.py
# 目的：
# - PDFのスタートリストから、指定した氏名（＋任意でクラス）に一致する行を探す
# - その行からスタート時刻っぽい文字列を抜き出す
# - 見つかった時刻を正規化して表示（候補が複数なら全部）
#
# 依存：
#   pip install pdfplumber pandas python-dateutil
#
# 想定するPDF：
# - 表形式 or それに近い整列テキスト（完全に画像スキャンは対象外：必要ならOCR追加）
# - 列名や区切りがあいまいでも、時刻は 9:07 / 09:07 / 9時07分 / 9.07 などを拾う

import argparse
import re
from datetime import datetime
from dateutil import tz
from dateutil.parser import parse as dt_parse
import pdfplumber
import pandas as pd

TIME_PATTERNS = [
    r'\b([01]?\d|2[0-3])[:\.時]([0-5]\d)\b',    # 9:07, 09:07, 9.07, 9時07 など
    r'\b([01]?\d|2[0-3])時([0-5]\d)分\b',       # 9時07分
    r'\b([01]?\d|2[0-3])：([0-5]\d)\b',         # 全角コロン
]

def normalize_name(s: str):
    # 超簡易の正規化：空白・全角半角スペース除去、大小文字無視
    return re.sub(r'\s+', '', s).lower()

def find_time_candidates(text: str):
    cands = []
    for pat in TIME_PATTERNS:
        for m in re.finditer(pat, text):
            hh = m.group(1)
            mm = m.group(2)
            # 全角数字は一応半角化
            hh = str(hh).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            mm = str(mm).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            try:
                hh_i = int(hh)
                mm_i = int(mm)
                if 0 <= hh_i <= 23 and 0 <= mm_i <= 59:
                    cands.append(f"{hh_i:02d}:{mm_i:02d}")
            except:
                pass
    # 重複除去
    return sorted(set(cands))

def combine_date_time(date_str: str, time_str: str, tz_name="Asia/Tokyo"):
    # date_str がなければ時間だけ返す
    if not date_str:
        return time_str
    try:
        # date_str は YYYY-MM-DD などを想定。曖昧でも dateutil がだいたい解釈する
        d = dt_parse(date_str).date()
        hh, mm = map(int, time_str.split(":"))
        tzinfo = tz.gettz(tz_name)
        dt = datetime(d.year, d.month, d.day, hh, mm, tzinfo=tzinfo)
        # ISO形式（タイムゾーンオフセット付き）
        return dt.isoformat()
    except Exception:
        return f"{date_str}T{time_str}"

def extract_tables(pdf_path):
    """pdfplumber で各ページの表を抽出。表がないページは line 文字列のリストとして返す"""
    rows_all = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # 1) table抽出
            tables = page.extract_tables()
            if tables:
                for tbl in tables:
                    for row in tbl:
                        if row and any(cell is not None and str(cell).strip() for cell in row):
                            rows_all.append([str(cell) if cell is not None else "" for cell in row])
            else:
                # 2) テキスト行で代替
                text = page.extract_text() or ""
                for line in text.splitlines():
                    # 疑似的に列に分割（タブや大量スペースを区切り扱い）
                    cols = re.split(r'\t+|\s{2,}', line.strip())
                    if cols and any(c.strip() for c in cols):
                        rows_all.append(cols)
    return rows_all

def score_row_for_person(row_text: str, name_key: str, class_key: str = None):
    # 氏名一致を重視、クラス一致で加点
    score = 0
    if name_key in normalize_name(row_text):
        score += 10
    if class_key and class_key.lower() in row_text.lower():
        score += 3
    return score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, help="スタートリストPDFのパス")
    parser.add_argument("--name", required=True, help="自分の氏名（PDF内と同じ表記が望ましい）")
    parser.add_argument("--class", dest="klass", required=False, help="クラス（例: M35, W21A など）")
    parser.add_argument("--event_date", required=False, help="大会日（例: 2025-10-12）")
    args = parser.parse_args()

    target_name_norm = normalize_name(args.name)
    target_class = args.klass

    print(f"PDF読み込み中: {args.pdf}")
    rows = extract_tables(args.pdf)
    if not rows:
        print("表っぽい行が見つかりませんでした。スキャンPDFの可能性あり。OCR対応は別途。")
        return

    # 各行をテキスト化してスコアリング
    candidates = []
    for r in rows:
        row_text = " | ".join([c for c in r if c is not None])
        s = score_row_for_person(row_text, target_name_norm, target_class)
        if s > 0:
            times = find_time_candidates(row_text)
            if times:
                candidates.append({
                    "row_text": row_text,
                    "times": times,
                    "score": s
                })

    if not candidates:
        # 名前だけでヒットしなかったとき、緩め検索：苗字部分一致などを追加してもOK
        print("候補が見つかりませんでした。氏名の表記ゆれ（漢字/かな/ローマ字/スペース）やクラスを確認してください。")
        return

    # スコアで降順、テキスト短いほうを優先気味に
    candidates.sort(key=lambda x: (x["score"], -len(x["row_text"])), reverse=True)

    # 上位3件だけ表示
    top = candidates[:3]

    print("\n抽出候補（最大3件）:")
    for i, c in enumerate(top, 1):
        # 時刻をISO化（event_date があれば付与）
        iso_list = [combine_date_time(args.event_date, t) for t in c["times"]]
        print(f"[{i}] score={c['score']}")
        print("  行テキスト:", c["row_text"])
        print("  時刻候補  :", ", ".join(iso_list))

    # 最有力の第一候補だけサマリ
    best_times = [combine_date_time(args.event_date, t) for t in top[0]["times"]]
    print("\n最有力候補（第1位）:")
    print("  時刻候補:", ", ".join(best_times))
    print("  ※ 候補が複数あれば、PDF上の列構成次第でどれがスタート時刻か揺れます。UIでワンタップ確認を挟む想定。")

if __name__ == "__main__":
    main()
