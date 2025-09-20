# スタートリスト時刻抽出ツール

PDFのスタートリストから指定した氏名（＋任意でクラス）に一致する行を探し、スタート時刻を抽出・正規化する最小スクリプトです。

## セットアップ

```bash
# 必要なライブラリをインストール
pip install -r requirements.txt
```

## 使い方

```bash
python start_time_finder.py --pdf path/to/startlist.pdf --name "山田 太郎" --class "M35" --event_date "2025-10-12"
```

### 大会ページURLから自動取得（新機能）

```bash
# 必要ライブラリをインストール（初回のみ）
pip install -r requirements.txt

# 大会ページURLと氏名（＋任意でクラス・大会日）を指定
python joe_startlist_scrape.py \
  --event_url "https://japan-o-entry.com/event/view/1923" \
  --name "山田 太郎" --class "M35" --event_date "2025-10-12"
```

#### 振る舞い
- 大会ページの「発行書類」から「スタート」「Start」系PDFリンクを自動検出
- PDFをダウンロードし、氏名（＋クラス）で該当行を特定 → 時刻候補を抽出
- 見つからない場合は、未掲載・表記揺れ・外部ビューア等の理由をメッセージ表示

#### 注意点
- 外部の Google Drive ビューアに飛ぶファイルは直ダウンロードURLへ変換（`uc?export=download`）を試行しますが、権限制限や警告画面が入る場合は人手対応が必要です。
- 完全な画像スキャンPDFは対象外（OCR対応を別途導入してください）。

### パラメータ

- `--pdf`: スタートリストPDFのパス（必須）
- `--name`: 自分の氏名（必須）
- `--class`: クラス（任意、例: M35, W21A など）
- `--event_date`: 大会日（任意、例: 2025-10-12）

### 実行例

```bash
# 基本使用
python start_time_finder.py --pdf startlist.pdf --name "田中 花子"

# クラス指定
python start_time_finder.py --pdf startlist.pdf --name "田中 花子" --class "W21A"

# 日付込みでISO形式出力
python start_time_finder.py --pdf startlist.pdf --name "田中 花子" --class "W21A" --event_date "2025-10-12"
```

## 機能

- PDFの表から行を復元して氏名・クラスでマッチング
- 行テキストから時刻パターンを抽出（9:07, 09:07, 9時07分など）
- 時刻をISO形式に正規化
- 候補が複数の場合は全て表示

## 想定限界

- 完全な画像スキャンPDFは対象外（OCR対応は別途必要）
- 表形式に近い整列テキストが前提
- 同姓同名が多い場合はBibや所属もキーにすると安定度向上

## 次の一手（必要に応じて）

- OCR対応：`pytesseract` + `pdf2image` を追加
- 列ラベリング：時刻の信頼度重み付け
- Googleカレンダー連携：iCal生成
