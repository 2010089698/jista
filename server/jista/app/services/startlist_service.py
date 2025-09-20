"""Japan-O-Entryからのスタートリスト取得・解析サービス"""

import io
import re
import hashlib
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
import pdfplumber
from dateutil import tz
from dateutil.parser import parse as dt_parse


@dataclass
class Row:
    cells: List[str]
    text: str


class StartlistService:
    """Japan-O-Entryからスタートリストを取得・解析するサービス"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Jista/1.0 (+https://jista.app)",
            "Accept-Language": "ja,en;q=0.9",
        }
        
        # スタート系リンクテキストの日本語パターン
        self.STARTLIST_HINTS = [
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
        
        # 時刻パターン
        self.TIME_PATTERNS = [
            r"\b([01]?\d|2[0-3])[:\.時]([0-5]\d)\b",
            r"\b([01]?\d|2[0-3])時([0-5]\d)分\b",
            r"\b([01]?\d|2[0-3])：([0-5]\d)\b",
        ]
        
        # 時刻ヘッダーヒント
        self.TIME_HEADER_HINTS = [
            r"スタート",
            r"時刻",
            r"\bstart\b",
            r"\btime\b",
        ]
    
    def normalize_name(self, s: str) -> str:
        """氏名を正規化"""
        return re.sub(r"\s+", "", s).lower()
    
    def _cell_has_name(self, cell_text: str, name_key: str) -> bool:
        """セル内に氏名があるかをチェック"""
        return name_key and (self.normalize_name(cell_text).find(name_key) != -1)
    
    def find_times_with_spans(self, text: str) -> List[Tuple[str, int, int]]:
        """テキストから (時刻文字列, start_idx, end_idx) の配列を返す"""
        results = []
        for pattern in self.TIME_PATTERNS:
            for m in re.finditer(pattern, text):
                hh = str(m.group(1)).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
                mm = str(m.group(2)).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
                try:
                    hh_i, mm_i = int(hh), int(mm)
                    if 0 <= hh_i <= 23 and 0 <= mm_i <= 59:
                        results.append((f"{hh_i:02d}:{mm_i:02d}", m.start(), m.end()))
                except Exception:
                    pass
        return results

    def find_time_candidates(self, text: str) -> List[str]:
        """テキストから時刻候補を抽出（互換性のため残す）"""
        candidates: List[str] = []
        for pattern in self.TIME_PATTERNS:
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
    
    def _find_line_index(self, text: str, name_key: str) -> int:
        """テキスト内で名前が見つかった行番号を返す"""
        lines = [ln for ln in re.split(r'\r?\n', text) if ln.strip()]
        for i, ln in enumerate(lines):
            if name_key in self.normalize_name(ln):
                return i
        return -1

    def _extract_time_from_same_line(self, col_text: str, line_idx: int) -> Optional[str]:
        """指定された行番号から時刻を抽出"""
        lines = [ln for ln in re.split(r'\r?\n', col_text) if ln.strip()]
        if 0 <= line_idx < len(lines):
            spans = self.find_times_with_spans(lines[line_idx])
            if spans:
                # 同じ行に時刻が複数あっても、その行の中ほどに近いものを採用
                mid = len(lines[line_idx]) // 2
                best = min(spans, key=lambda t: abs(t[1] - mid))
                return best[0]
        return None
    
    def combine_date_time(self, date_str: str, time_str: str, tz_name: str = "Asia/Tokyo") -> str:
        """日付と時刻を結合してISO形式で返す"""
        if not date_str:
            return time_str
        try:
            d = dt_parse(date_str).date()
            hh, mm = map(int, time_str.split(":"))
            tzinfo = tz.gettz(tz_name)
            return datetime(d.year, d.month, d.day, hh, mm, tzinfo=tzinfo).isoformat()
        except Exception:
            return f"{date_str}T{time_str}"
    
    def extract_rows_from_pdf_bytes(self, pdf_bytes: bytes) -> List[Row]:
        """PDFバイトから行データを抽出"""
        rows_all: List[Row] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for tbl in tables:
                        for row in tbl:
                            if row and any(cell is not None and str(cell).strip() for cell in row):
                                cells = [str(cell) if cell is not None else "" for cell in row]
                                
                                # 1セルに大量の行が詰まっている場合は分解
                                if len(cells) == 1 and ("\n" in cells[0] or "\r" in cells[0]):
                                    for ln in cells[0].splitlines():
                                        ln = ln.strip()
                                        if not ln or re.search(r'時刻\s+スタート', ln):
                                            continue  # 見出し除外
                                        # 行っぽいものだけ
                                        if self.find_time_candidates(ln):
                                            pseudo_cells = re.split(r"\s{2,}|\t+|\s+", ln)
                                            rows_all.append(Row(cells=pseudo_cells, text=" | ".join(pseudo_cells)))
                                    continue
                                
                                rows_all.append(Row(cells=cells, text=" | ".join(cells)))
                else:
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        cols = re.split(r"\t+|\s{2,}", line.strip())
                        if cols and any(c.strip() for c in cols):
                            rows_all.append(Row(cells=cols, text=" | ".join(cols)))
        return rows_all
    
    def guess_time_column_index(self, rows: List[Row]) -> Optional[int]:
        """時刻列のインデックスを推定（強化版）"""
        # まず既存ロジックを使ってみる
        look_rows = rows[:10]
        best_idx: Optional[int] = None
        best_score = -1
        for r in look_rows:
            for i, c in enumerate(r.cells):
                t = str(c)
                score = 0
                for pat in self.TIME_HEADER_HINTS:
                    if re.search(pat, t, flags=re.I):
                        score += 2
                if re.search(r'^\s*(時間|時刻|時|Start|Time)\s*$', t, flags=re.I):
                    score += 1
                if self.find_time_candidates(t):
                    score += 1
                if score > best_score:
                    best_score, best_idx = score, i
        
        if best_score >= 2:
            return best_idx

        # 集計ベースのバックアップ推定
        col_scores = {}
        sample = rows[:200]  # 取り過ぎ防止
        max_cols = max((len(r.cells) for r in sample), default=0)
        for r in sample:
            for i in range(len(r.cells)):
                if self.find_time_candidates(str(r.cells[i])):
                    col_scores[i] = col_scores.get(i, 0) + 1
        if not col_scores:
            return None
        # 最もヒットが多い列を採用。ただし一定以上の差があるときだけ
        best_idx = max(col_scores, key=col_scores.get)
        if col_scores[best_idx] >= 2:
            return best_idx
        return None
    
    def score_row_for_person(
        self,
        row: Row,
        name_key: str,
        class_key: Optional[str],
        time_col_idx: Optional[int]
    ) -> Tuple[int, List[str]]:
        """
        行のスコアリングと時刻抽出（名前に近い時刻を選択）
        - 1) セル単位で氏名一致を探す（なければ弱い行一致）
        - 2) 時刻列が推定できていればそこを最優先（セル内複数時刻は名前に近いものを選択）
        - 3) そうでなければ「名前セルの列」と「時刻セルの列」の距離が最短のものを1つだけ採用
        - 4) どうしても見つからないときだけ行全体から1つ（名前に近い時刻を選択）
        """
        score = 0
        text_norm = self.normalize_name(row.text)
        
        # まず氏名一致を確認
        has_name = bool(name_key and name_key in text_norm)
        if has_name:
            score += 10
        elif class_key and class_key.lower() in row.text.lower():
            score += 3
        else:
            # 氏名もクラスも手がかりなしなら終了
            return score, []

        # ここからが修正ポイント:
        # 1セルに複数行が詰まっている場合は「氏名を含む行」だけに限定して時刻抽出
        # 改行で分割して、正規化した氏名が入っている行を探す
        multiline_cell = (len(row.cells) == 1 and ("\n" in row.cells[0] or "\r" in row.cells[0]))
        if multiline_cell:
            lines = [ln for ln in row.cells[0].splitlines() if ln.strip()]
            # 正規化して氏名が入る行を抽出
            candid_lines = [ln for ln in lines if name_key in self.normalize_name(ln)]
            # 見出し行（"時刻 スタートナンバー 氏名 ..."）を除外
            candid_lines = [ln for ln in candid_lines if not re.search(r'時刻\s+スタート', ln)]
            # 氏名が複数回出たら最も短い行を採用（冗長ヘッダを避ける雑だけど効く策）
            if candid_lines:
                best_line = min(candid_lines, key=len)
                times_spans = self.find_times_with_spans(best_line)
                if times_spans:
                    # 名前に近い時刻を選択
                    name_pos = self.normalize_name(best_line).find(name_key)
                    if name_pos != -1:
                        best = min(times_spans, key=lambda t: abs(t[1] - name_pos))
                    else:
                        # 氏名位置が取れないなら、行の中ほどに近い時刻を採用
                        mid = len(best_line)//2
                        best = min(times_spans, key=lambda t: abs(t[1] - mid))
                    return score + 5, [best[0]]

        # ふつうの表（セル分割がきちんとできている）なら行合わせロジック
        # 推定時刻列を優先。ただし「名前が入っているセルの行番号」と「時刻列の同じ行番号」で時刻を抽出
        if time_col_idx is not None and time_col_idx < len(row.cells):
            col_text = str(row.cells[time_col_idx])

            # 名前が入っているセルを探し、そこでの行番号を特定
            name_cell_idx = None
            for i, c in enumerate(row.cells):
                if name_key in self.normalize_name(str(c)):
                    name_cell_idx = i
                    break

            # デフォルトは旧挙動へのフォールバック
            fallback = None
            spans_all = self.find_times_with_spans(col_text)
            if spans_all:
                mid = len(col_text) // 2
                fallback = min(spans_all, key=lambda t: abs(t[1] - mid))[0]

            # 行合わせができるならそれを最優先
            if name_cell_idx is not None:
                name_cell_text = str(row.cells[name_cell_idx])
                line_idx = self._find_line_index(name_cell_text, name_key)
                if line_idx != -1:
                    same_line_time = self._extract_time_from_same_line(col_text, line_idx)
                    if same_line_time:
                        return score + 6, [same_line_time]

            # 行合わせで取れなかった場合のみフォールバック
            if fallback:
                return score + 4, [fallback]

        # 近傍セル探索（名前セルに最も近い時刻セルを1つだけ）
        name_cols = [i for i, c in enumerate(row.cells) if name_key in self.normalize_name(str(c))]
        times_by_col = {}
        for j, c in enumerate(row.cells):
            c_text = str(c)
            t_spans = self.find_times_with_spans(c_text)
            if t_spans:
                times_by_col[j] = (c_text, t_spans)

        if name_cols and times_by_col:
            # まず列距離で最小の列を選ぶ
            best_col = None
            best_dist = 1e9
            for k in name_cols:
                for j in times_by_col.keys():
                    dist = abs(j - k)
                    if dist < best_dist:
                        best_dist, best_col = dist, j
            c_text, t_spans = times_by_col[best_col]
            # その列の中で「名前に近い」時刻を選ぶ（列テキスト内で氏名が無ければ中央に近い時刻）
            name_pos_in_col = self.normalize_name(c_text).find(name_key)
            ref_pos = name_pos_in_col if name_pos_in_col != -1 else len(c_text)//2
            best = min(t_spans, key=lambda t: abs(t[1] - ref_pos))
            return score + 4, [best[0]]

        # 最後の最後に行全体から1つ（近接選択）
        name_pos = self.normalize_name(row.text).find(name_key)
        row_spans = self.find_times_with_spans(row.text)
        if row_spans:
            if name_pos != -1:
                best = min(row_spans, key=lambda t: abs(t[1] - name_pos))
            else:
                mid = len(row.text)//2
                best = min(row_spans, key=lambda t: abs(t[1] - mid))
            return score + 1, [best[0]]
        return score, []
    
    def fetch_event_page(self, url: str) -> str:
        """大会ページを取得"""
        r = requests.get(url, headers=self.headers, timeout=20)
        r.raise_for_status()
        return r.text
    
    def pick_startlist_links(self, html: str, base_url: str) -> List[str]:
        """HTMLからスタートリストリンクを抽出"""
        soup = BeautifulSoup(html, "html.parser")
        links: List[str] = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True) or ""
            href = a["href"]
            hint_hit = any(re.search(pat, text, flags=re.I) for pat in self.STARTLIST_HINTS)
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
    
    def to_drive_direct_download(self, u: str) -> Optional[str]:
        """Google Drive URLを直接ダウンロードURLに変換"""
        try:
            p = urlparse(u)
            if p.netloc.endswith("drive.google.com") or p.netloc.endswith("docs.google.com"):
                qs = parse_qs(p.query)
                for key in ("id", "fileid"):
                    if key in qs:
                        fid = qs[key][0]
                        return f"https://drive.google.com/uc?export=download&id={fid}"
                m = re.search(r'/file/d/([^/]+)/', p.path)
                if m:
                    fid = m.group(1)
                    return f"https://drive.google.com/uc?export=download&id={fid}"
                if "url" in qs:
                    return qs["url"][0]
            return None
        except Exception:
            return None
    
    def download_from_google_drive(self, url: str) -> Optional[bytes]:
        """Google DriveからPDFをダウンロード"""
        sess = requests.Session()
        sess.headers.update(self.headers)
        
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
    
    def resolve_to_pdf(self, url: str, visited: Optional[set] = None) -> Optional[bytes]:
        """URLからPDFバイトを取得"""
        if visited is None:
            visited = set()
        if url in visited or len(visited) > 20:
            return None
        visited.add(url)
        
        # Google Drive は confirm トークンに対応した専用処理を優先
        if re.search(r'(drive|docs)\.google\.com', urlparse(url).netloc):
            b = self.download_from_google_drive(url)
            if b:
                return b
            dl = self.to_drive_direct_download(url)
            if dl:
                b = self.download_from_google_drive(dl)
                if b:
                    return b
        
        # 通常の直リンク/HTML中リンク検出
        try:
            with requests.get(url, headers=self.headers, timeout=30, allow_redirects=True, stream=True) as r:
                r.raise_for_status()
                ctype = (r.headers.get("Content-Type") or "").lower()
                cdisp = (r.headers.get("Content-Disposition") or "").lower()
                content = r.content
                
                # PDF判定を強化
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
                        b = self.resolve_to_pdf(nxt, visited)
                        if b:
                            return b
                    # Google Drive viewer ページから file id を抽出
                    m_gid = re.search(r'/file/d/([^/]+)/', text)
                    if m_gid:
                        fid = m_gid.group(1)
                        dl = f"https://drive.google.com/uc?export=download&id={fid}"
                        b = self.download_from_google_drive(dl)
                        if b:
                            return b
                    
                    soup = BeautifulSoup(text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if re.search(r'\.pdf($|\?)', href, re.I):
                            b = requests.get(urljoin(url, href), headers=self.headers, timeout=30).content
                            return b
                        if re.search(r'(drive|docs)\.google\.com', href):
                            b = self.resolve_to_pdf(urljoin(url, href), visited)
                            if b:
                                return b
        except requests.RequestException:
            pass
        return None
    
    def extract_event_name_from_html(self, html_content: str) -> str:
        """HTMLからイベント名を抽出"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # タイトルタグから抽出
            title = soup.find('title')
            if title and title.text:
                title_text = title.text.strip()
                # "大会名 | Japan-O-Entry" のような形式から大会名を抽出
                if '|' in title_text:
                    event_name = title_text.split('|')[0].strip()
                    if event_name and event_name != 'Japan-O-Entry':
                        return event_name
            
            # h1タグから抽出
            h1 = soup.find('h1')
            if h1 and h1.text:
                return h1.text.strip()
            
            # メタタグから抽出
            meta_title = soup.find('meta', attrs={'name': 'title'})
            if meta_title and meta_title.get('content'):
                return meta_title.get('content').strip()
            
            # ページ内のテキストから大会名らしきものを検索
            # "大会名"、"大会"、"オリエンテーリング"などのキーワードを含むテキストを探す
            for tag in soup.find_all(['h1', 'h2', 'h3', 'div', 'span']):
                if tag.text and any(keyword in tag.text for keyword in ['大会', 'オリエンテーリング', 'カップ', 'クラシック']):
                    text = tag.text.strip()
                    if len(text) > 5 and len(text) < 100:  # 適切な長さのテキスト
                        return text
            
        except Exception as e:
            print(f"イベント名抽出エラー: {e}")
        
        return "Japan-O-Entry Event"  # デフォルト値
    
    def fetch_event_start_times(
        self, 
        event_url: str, 
        competitor_name: Optional[str] = None,
        competitor_class: Optional[str] = None,
        event_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """大会ページからスタートリストを取得・解析"""
        
        # 1. 大会ページからイベント名を取得
        print(f"[1/5] 大会ページ取得: {event_url}")
        html = self.fetch_event_page(event_url)
        
        # イベント名を抽出
        event_name = self.extract_event_name_from_html(html)
        print(f"[1/5] 抽出されたイベント名: {event_name}")
        
        print("[2/5] スタートリスト候補リンク探索")
        pdf_links = self.pick_startlist_links(html, event_url)
        if not pdf_links:
            raise ValueError("スタートリストらしきリンクが見当たりません")
        
        # 2. PDFをダウンロード・解析
        pdf_bytes = None
        last_url = None
        for pdf_url in pdf_links:
            print(f"  試行: {pdf_url}")
            pdf_bytes = self.resolve_to_pdf(pdf_url)
            last_url = pdf_url
            if pdf_bytes:
                print("  -> PDF取得OK")
                break
        
        if not pdf_bytes:
            raise ValueError("PDFのダウンロードに失敗")
        
        print("[3/5] PDFから行抽出→氏名マッチ→時刻抽出")
        rows = self.extract_rows_from_pdf_bytes(pdf_bytes)
        if not rows:
            raise ValueError("PDFから表データ・テキスト行を取得できず")
        
        time_col_idx = self.guess_time_column_index(rows)
        target_name_norm = self.normalize_name(competitor_name) if competitor_name else ""
        
        candidates = []
        for r in rows:
            s, times = self.score_row_for_person(r, target_name_norm, competitor_class, time_col_idx)
            if s > 0 and times:
                candidates.append({"row_text": r.text, "times": times, "score": s})
        
        if not candidates:
            raise ValueError("氏名で該当行が見つからず")
        
        candidates.sort(key=lambda x: (x["score"], -len(x["row_text"])), reverse=True)
        pick = candidates[:3]
        
        # 結果を整形（重複時刻を除去）
        start_times = []
        seen_times = set()
        for c in pick:
            for time_str in c["times"]:
                if time_str in seen_times:
                    continue
                seen_times.add(time_str)
                iso_time = self.combine_date_time(event_date, time_str) if event_date else time_str
                start_times.append({
                    "competitor": competitor_name or "Unknown",
                    "startTime": time_str,
                    "isoTime": iso_time,
                    "score": c["score"]
                })
        
        # 一意のIDを生成（イベント名とURLからハッシュを生成）
        unique_id = hashlib.md5(f"{event_name}_{event_url}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
        
        return {
            "id": f"joe-event-{unique_id}",  # 一意のIDを生成
            "name": event_name,  # 抽出したイベント名を使用
            "date": event_date or datetime.now().strftime("%Y-%m-%d"),
            "startTimes": start_times,
            "fetchedAt": datetime.utcnow().isoformat(),
            "sourceUrl": last_url
        }
