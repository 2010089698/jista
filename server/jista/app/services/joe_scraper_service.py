"""Service for scraping Japan-O-Entry event data."""
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import JOEEvent


class JOEScraperService:
    """Service for scraping Japan-O-Entry event data."""

    def __init__(self, base_url: str = "https://japan-o-entry.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_events(self) -> List[JOEEvent]:
        """Scrape event list from Japan-O-Entry homepage."""
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            events = []
            
            # イベント一覧テーブルを探す（2番目のテーブルがイベント一覧）
            tables = soup.find_all('table')
            if len(tables) < 2:
                return events
            
            table = tables[1]  # 2番目のテーブルがイベント一覧
            rows = table.find_all('tr')[1:]  # 最初の行はヘッダー
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 3:
                    continue
                
                # 日付セル
                date_cell = cells[0]
                date_text = date_cell.get_text(strip=True)
                
                # イベント名セル
                event_cell = cells[1]
                event_link = event_cell.find('a')
                if not event_link:
                    continue
                
                event_name = event_link.get_text(strip=True)
                event_url = event_link.get('href', '')
                
                # ステータスセル
                status_cell = cells[2]
                status_text = status_cell.get_text(strip=True)
                
                # イベントIDをURLから抽出
                event_id = self._extract_event_id(event_url)
                if not event_id:
                    continue
                
                # 日付を正規化
                normalized_date = self._normalize_date(date_text)
                
                event = JOEEvent(
                    id=event_id,
                    name=event_name,
                    date=normalized_date,
                    url=urljoin(self.base_url, event_url),
                    status=status_text
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            print(f"Error scraping Japan-O-Entry events: {e}")
            return []

    def _extract_event_id(self, url: str) -> Optional[str]:
        """Extract event ID from Japan-O-Entry URL."""
        if not url:
            return None
        
        # URL例: /event/view/1923 -> 1923
        match = re.search(r'/event/view/(\d+)', url)
        if match:
            return match.group(1)
        
        return None

    def _normalize_date(self, date_text: str) -> str:
        """Normalize date text to ISO format."""
        if not date_text:
            return ""
        
        # 日付の正規化処理
        # 例: "9/20 (土)" -> "2025-09-20"
        try:
            # 現在の年を取得
            current_year = datetime.now().year
            
            # 月日を抽出
            match = re.search(r'(\d+)/(\d+)', date_text)
            if match:
                month = int(match.group(1))
                day = int(match.group(2))
                
                # 日付が過去の場合は来年とみなす
                event_date = datetime(current_year, month, day)
                if event_date < datetime.now():
                    event_date = datetime(current_year + 1, month, day)
                
                return event_date.strftime('%Y-%m-%d')
        except Exception:
            pass
        
        return date_text
