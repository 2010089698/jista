# Jista MVP Setup

このリポジトリは、オリエンテーリングイベントのスタート時刻を確認するアプリ「Jista」のMVP要件定義に基づき、クライアント(Expo)とサーバー(FastAPI)を最小構成で起動できるようにした初期セットアップです。

## ディレクトリ構成

- `App.tsx` / `src/` - Expoベースのモバイルアプリケーション
- `server/` - FastAPIベースのバックエンドAPI
- `docs/` - 要件定義などのドキュメント

## 前提ツール

- Node.js 18 以上
- npm 9 以上
- Python 3.11 以上

## セットアップ

### 1. クライアント(Expo)

```bash
npm install
npm run start
```

`npm run start` を実行すると Expo の開発サーバーが立ち上がり、Expo Go から接続できるようになります。API はデフォルトで `http://localhost:8000` を参照するよう設定しています。

### 2. サーバー(FastAPI)

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn jista.app.main:app --reload
```

API サーバーはポート `8000` で起動します。`/events` でイベント一覧、`/events/{event_id}/start-times` でスタート時刻サンプルを取得できます。

## 環境変数

現状必要な環境変数はありません。将来的に API エンドポイントを切り替える場合は `.env` を用意し、`src/config.ts` から読み込む形を想定しています。

## 次のステップ

- Japan-O-Entry からの実データ取得実装
- スタート時刻のPDF解析ロジック
- 匿名IDでの継続率計測
- UI/UXのブラッシュアップおよびオフラインキャッシュの充実

