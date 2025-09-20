"""Japan-O-Entryからのスタートリスト取得・解析サービス"""

import io
import re
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
    
    def find_time_candidates(self, text: str) -> List[str]:
        """テキストから時刻候補を抽出"""
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
                                rows_all.append(Row(cells=cells, text=" | ".join(cells)))
                else:
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        cols = re.split(r"\t+|\s{2,}", line.strip())
                        if cols and any(c.strip() for c in cols):
                            rows_all.append(Row(cells=cols, text=" | ".join(cols)))
        return rows_all
    
    def guess_time_column_index(self, rows: List[Row]) -> Optional[int]:
        """時刻列のインデックスを推定"""
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
        return best_idx if best_score >= 2 else None
    
    def score_row_for_person(
        self, 
        row: Row, 
        name_key: str, 
        class_key: Optional[str], 
        time_col_idx: Optional[int]
    ) -> Tuple[int, List[str]]:
        """行のスコアリングと時刻抽出"""
        score = 0
        text_norm = self.normalize_name(row.text)
        if name_key in text_norm:
            score += 10
        if class_key and class_key.lower() in row.text.lower():
            score += 3
        
        times = self.find_time_candidates(row.text)
        if not times:
            return score, []
        
        # 列見出しに近い時刻を優先
        if time_col_idx is not None and len(row.cells) > time_col_idx:
            col_text = row.cells[time_col_idx]
            col_times = self.find_time_candidates(col_text)
            if col_times:
                score += 5
                times = sorted(set(col_times + times), key=lambda x: (x not in col_times, x))
            else:
                score += 1
        
        return score, times
    
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
        
        # 結果を整形
        start_times = []
        for c in pick:
            for time_str in c["times"]:
                iso_time = self.combine_date_time(event_date, time_str) if event_date else time_str
                start_times.append({
                    "competitor": competitor_name or "Unknown",
                    "startTime": time_str,
                    "isoTime": iso_time,
                    "score": c["score"]
                })
        
        return {
            "id": "joe-event",
            "name": event_name,  # 抽出したイベント名を使用
            "date": event_date or datetime.now().strftime("%Y-%m-%d"),
            "startTimes": start_times,
            "fetchedAt": datetime.utcnow().isoformat(),
            "sourceUrl": last_url
        }
