# -*- coding: utf-8 -*-
"""
Japan-O-EntrY 大会ページの「発行書類」からスタートリストPDFを自動取得 → 氏名で時刻抽出

依存: requests, beautifulsoup4, pdfplumber, python-dateutil

使い方例:
  python joe_startlist_scrape.py \
    --event_url "https://japan-o-entry.com/event/view/1923" \
    --name "山田 太郎" --class "M35" --event_date "2025-10-12"
"""

import argparse
import io
import re
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
import pdfplumber
from dateutil import tz
from dateutil.parser import parse as dt_parse


HEADERS = {
    "User-Agent": "StartlistMVP/0.2 (+https://example.invalid)",
    "Accept-Language": "ja,en;q=0.9",
}

# スタート系リンクテキストの日本語パターンを拡充
STARTLIST_HINTS = [
    r"スタート\s*リスト",
    r"スタート\s*時刻",
    r"スタート\s*順",
    r"スタート\s*割(り|り当て)?",
    r"スタート\s*表",
    r"\bstart\s*list\b",
    r"\bstart(?:ing)?\b",
    r"時差スタート",
    r"走順",
]

TIME_PATTERNS = [
    r"\b([01]?\d|2[0-3])[:\.時]([0-5]\d)\b",
    r"\b([01]?\d|2[0-3])時([0-5]\d)分\b",
    r"\b([01]?\d|2[0-3])：([0-5]\d)\b",
]

TIME_HEADER_HINTS = [
    r"スタート",
    r"時刻",
    r"\bstart\b",
    r"\btime\b",
]


@dataclass
class Row:
    cells: List[str]
    text: str


def normalize_name(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def find_time_candidates(text: str) -> List[str]:
    candidates: List[str] = []
    for pattern in TIME_PATTERNS:
        for m in re.finditer(pattern, text):
            hh = str(m.group(1)).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            mm = str(m.group(2)).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            try:
                hh_i, mm_i = int(hh), int(mm)
                if 0 <= hh_i <= 23 and 0 <= mm_i <= 59:
                    candidates.append(f"{hh_i:02d}:{mm_i:02d}")
            except Exception:
                pass
    return sorted(set(candidates))


def combine_date_time(date_str: str, time_str: str, tz_name: str = "Asia/Tokyo") -> str:
    if not date_str:
        return time_str
    try:
        d = dt_parse(date_str).date()
        hh, mm = map(int, time_str.split(":"))
        tzinfo = tz.gettz(tz_name)
        return datetime(d.year, d.month, d.day, hh, mm, tzinfo=tzinfo).isoformat()
    except Exception:
        return f"{date_str}T{time_str}"


def extract_rows_from_pdf_bytes(pdf_bytes: bytes) -> List[Row]:
    rows_all: List[Row] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            if tables:
                for tbl in tables:
                    for row in tbl:
                        if row and any(cell is not None and str(cell).strip() for cell in row):
                            cells = [str(cell) if cell is not None else "" for cell in row]
                            rows_all.append(Row(cells=cells, text=" | ".join(cells)))
            else:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    cols = re.split(r"\t+|\s{2,}", line.strip())
                    if cols and any(c.strip() for c in cols):
                        rows_all.append(Row(cells=cols, text=" | ".join(cols)))
    return rows_all


def guess_time_column_index(rows: List[Row]) -> Optional[int]:
    # 先頭〜数行の見出しから「時刻/スタート/Start/Time」列を推定
    look_rows = rows[:10]
    best_idx: Optional[int] = None
    best_score = -1
    for r in look_rows:
        for i, c in enumerate(r.cells):
            t = str(c)
            score = 0
            for pat in TIME_HEADER_HINTS:
                if re.search(pat, t, flags=re.I):
                    score += 2
            if re.search(r'^\s*(時間|時刻|時|Start|Time)\s*$', t, flags=re.I):
                score += 1
            if find_time_candidates(t):
                score += 1
            if score > best_score:
                best_score, best_idx = score, i
    return best_idx if best_score >= 2 else None


def score_row_for_person(row: Row, name_key: str, class_key: Optional[str], time_col_idx: Optional[int]) -> Tuple[int, List[str]]:
    score = 0
    text_norm = normalize_name(row.text)
    if name_key in text_norm:
        score += 10
    if class_key and class_key.lower() in row.text.lower():
        score += 3

    times = find_time_candidates(row.text)
    if not times:
        return score, []

    # 列見出しに近い時刻を優先
    if time_col_idx is not None and len(row.cells) > time_col_idx:
        col_text = row.cells[time_col_idx]
        col_times = find_time_candidates(col_text)
        if col_times:
            score += 5
            times = sorted(set(col_times + times), key=lambda x: (x not in col_times, x))
        else:
            score += 1

    return score, times


def fetch_event_page(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def pick_startlist_links(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True) or ""
        href = a["href"]
        hint_hit = any(re.search(pat, text, flags=re.I) for pat in STARTLIST_HINTS)
        file_like = re.search(r'\.(pdf|xlsx?|csv)$', href.split('?')[0], re.I) is not None
        if hint_hit or ("start" in href.lower()) or ("スタート" in href):
            links.append(urljoin(base_url, href))
        elif file_like and ("start" in href.lower() or "スタート" in href):
            links.append(urljoin(base_url, href))
    seen, uniq = set(), []
    for u in links:
        if u not in seen:
            uniq.append(u)
            seen.add(u)
    return uniq


def to_drive_direct_download(u: str) -> Optional[str]:
    # Google Drive / Docs の代表的な形式をダウンロードURLに正規化（できる範囲で）
    try:
        p = urlparse(u)
        if p.netloc.endswith("drive.google.com") or p.netloc.endswith("docs.google.com"):
            qs = parse_qs(p.query)
            # ?id=xxxxx, ?fileid=xxxxx 等に対応
            for key in ("id", "fileid"):
                if key in qs:
                    fid = qs[key][0]
                    return f"https://drive.google.com/uc?export=download&id={fid}"
            # /file/d/<id>/view 形式
            m = re.search(r'/file/d/([^/]+)/', p.path)
            if m:
                fid = m.group(1)
                return f"https://drive.google.com/uc?export=download&id={fid}"
            # viewer で url= が埋め込まれているケース
            if "url" in qs:
                return qs["url"][0]
        return None
    except Exception:
        return None


def download_from_google_drive(url: str) -> Optional[bytes]:
    sess = requests.Session()
    sess.headers.update(HEADERS)

    def extract_file_id(u: str) -> Optional[str]:
        try:
            p = urlparse(u)
            if not (p.netloc.endswith("drive.google.com") or p.netloc.endswith("docs.google.com")):
                return None
            qs = parse_qs(p.query)
            if "id" in qs:
                return qs["id"][0]
            if "fileid" in qs:
                return qs["fileid"][0]
            m_local = re.search(r'/file/d/([^/]+)/', p.path)
            if m_local:
                return m_local.group(1)
            m_local = re.search(r'/uc\?.*?id=([^&]+)', u)
            if m_local:
                return m_local.group(1)
            return None
        except Exception:
            return None

    fid = extract_file_id(url)
    if not fid:
        return None

    base = "https://drive.google.com/uc"
    params = {"export": "download", "id": fid}

    # 1st try
    r = sess.get(base, params=params, allow_redirects=True, timeout=40, stream=True)
    r.raise_for_status()

    ctype = (r.headers.get("Content-Type") or "").lower()
    if "pdf" in ctype or "application/octet-stream" in ctype or "application/pdf" in ctype:
        return r.content

    # HTML警告ページ → confirmトークン追跡
    html = r.text
    m = re.search(r'href="(?P<link>[^"]*?confirm=([^"&]+)[^"]*?\bid=' + re.escape(fid) + r'[^"]*)"', html, flags=re.I)
    if not m:
        m2 = re.search(r'name="confirm"\s+value="([^"]+)"', html, flags=re.I)
        if m2:
            confirm = m2.group(1)
            params2 = {"export": "download", "id": fid, "confirm": confirm}
            r2 = sess.get(base, params=params2, allow_redirects=True, timeout=40, stream=True)
            r2.raise_for_status()
            if "pdf" in (r2.headers.get("Content-Type") or "").lower():
                return r2.content
            return r2.content if r2.content else None
        return None

    confirm_rel = m.group("link")
    confirm_url = urljoin(base + "?", confirm_rel)
    r3 = sess.get(confirm_url, allow_redirects=True, timeout=40, stream=True)
    r3.raise_for_status()
    if "pdf" in (r3.headers.get("Content-Type") or "").lower():
        return r3.content
    return r3.content if r3.content else None


def resolve_to_pdf(url: str, visited: Optional[set] = None) -> Optional[bytes]:
    if visited is None:
        visited = set()
    # ループ防止
    if url in visited or len(visited) > 20:
        return None
    visited.add(url)
    # Google Drive は confirm トークンに対応した専用処理を優先
    if re.search(r'(drive|docs)\.google\.com', urlparse(url).netloc):
        b = download_from_google_drive(url)
        if b:
            return b
        dl = to_drive_direct_download(url)
        if dl:
            b = download_from_google_drive(dl)
            if b:
                return b

    # 通常の直リンク/HTML中リンク検出
    try:
        with requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True, stream=True) as r:
            r.raise_for_status()
            ctype = (r.headers.get("Content-Type") or "").lower()
            cdisp = (r.headers.get("Content-Disposition") or "").lower()
            content = r.content

            # PDF判定を強化: Content-Type, Content-Disposition, マジックヘッダ
            is_pdf_type = ("pdf" in ctype) or ("application/octet-stream" in ctype)
            is_pdf_name = (".pdf" in cdisp) or url.lower().endswith(".pdf")
            is_pdf_magic = content.startswith(b"%PDF")

            if is_pdf_type or is_pdf_name or is_pdf_magic:
                return content

            if "html" in ctype:
                text = r.text
                # meta refresh
                m = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=([^"\' >]+)', text, flags=re.I)
                if m:
                    nxt = urljoin(url, m.group(1))
                    b = resolve_to_pdf(nxt, visited)
                    if b:
                        return b
                # Google Drive viewer ページ（ログイン誘導含む）から file id を抽出
                m_gid = re.search(r'/file/d/([^/]+)/', text)
                if m_gid:
                    fid = m_gid.group(1)
                    dl = f"https://drive.google.com/uc?export=download&id={fid}"
                    b = download_from_google_drive(dl)
                    if b:
                        return b

                soup = BeautifulSoup(text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if re.search(r'\.pdf($|\?)', href, re.I):
                        b = requests.get(urljoin(url, href), headers=HEADERS, timeout=30).content
                        return b
                    if re.search(r'(drive|docs)\.google\.com', href):
                        b = resolve_to_pdf(urljoin(url, href), visited)
                        if b:
                            return b
    except requests.RequestException:
        pass
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event_url", help="Japan-O-EntrY の大会ページ URL（/event/view/xxxx）")
    ap.add_argument("--pdf_url", help="スタートリストPDFの直リンク（Google Drive共有URLなども可）")
    ap.add_argument("--name", required=True, help="氏名（PDF表記に合わせるのが望ましい）")
    ap.add_argument("--class", dest="klass", help="クラス（例: M35, W21A など）")
    ap.add_argument("--event_date", help="大会日（例: 2025-10-12）")
    args = ap.parse_args()

    pdf_bytes: Optional[bytes] = None
    last_url: Optional[str] = None

    if args.pdf_url:
        print("[1/3] 直リンクからPDF取得:", args.pdf_url)
        pdf_bytes = resolve_to_pdf(args.pdf_url)
        last_url = args.pdf_url
        if not pdf_bytes:
            print("直リンクからのダウンロードに失敗。共有設定やアクセス制限をご確認ください。")
            sys.exit(2)
    else:
        if not args.event_url:
            print("--event_url か --pdf_url のどちらかを指定してください。")
            sys.exit(1)
        print("[1/4] 大会ページ取得:", args.event_url)
        html = fetch_event_page(args.event_url)

        print("[2/4] スタートリスト候補リンク探索")
        cand_links = pick_startlist_links(html, args.event_url)
        if not cand_links:
            print("スタートリストらしきリンクが見当たりません。『発行書類』に未掲載か、命名が独特な可能性。大会ページを目視確認してください。")
            soup = BeautifulSoup(html, "html.parser")
            alt = [urljoin(args.event_url, a["href"]) for a in soup.find_all("a", href=True)
                   if re.search(r"(発行|要項|スタート|start|リザルト|結果|bulletin|pdf)", a.get_text(" ", strip=True) + a["href"], re.I)]
            if alt:
                print("関連ありそうなリンク候補:\n  - " + "\n  - ".join(alt[:10]))
            sys.exit(1)

        for u in cand_links:
            print("  試行:", u)
            pdf_bytes = resolve_to_pdf(u)
            last_url = u
            if pdf_bytes:
                print("  -> PDF取得OK")
                break
        if not pdf_bytes:
            print("PDFのダウンロードに失敗。外部ビューアや認証付きの可能性あり。ブラウザで開けるか要確認。")
            sys.exit(2)

    print("[3/4] PDFから行抽出→氏名マッチ→時刻抽出")
    rows = extract_rows_from_pdf_bytes(pdf_bytes)
    if not rows:
        print("PDFから表データ・テキスト行を取得できず。画像スキャンかも。OCR対応が必要。")
        sys.exit(3)

    time_col_idx = guess_time_column_index(rows)
    target_name_norm = normalize_name(args.name)

    candidates = []
    for r in rows:
        s, times = score_row_for_person(r, target_name_norm, args.klass, time_col_idx)
        if s > 0 and times:
            candidates.append({"row_text": r.text, "times": times, "score": s})

    if not candidates:
        print("氏名で該当行が見つからず。表記ゆれ（漢字/かな/ローマ字/スペース）やクラスを見直してください。")
        sys.exit(4)

    candidates.sort(key=lambda x: (x["score"], -len(x["row_text"])), reverse=True)
    pick = candidates[:3]

    print("[4/4] 抽出候補（最大3件）:")
    for i, c in enumerate(pick, 1):
        iso_list = [combine_date_time(args.event_date, t) for t in c["times"]]
        print(f"[{i}] score={c['score']}")
        print("  行テキスト:", c["row_text"])
        print("  時刻候補  :", ", ".join(iso_list))

    best_times = [combine_date_time(args.event_date, t) for t in pick[0]["times"]]
    print("\n最有力候補:")
    print("  時刻候補:", ", ".join(best_times))
    print("  出典URL :", last_url)


if __name__ == "__main__":
    main()


