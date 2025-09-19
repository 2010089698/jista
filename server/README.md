# Jista Backend API

FastAPI を用いた Jista MVP のバックエンド。Japan-O-Entry からデータを取得する実装の代わりに、ローカルのサンプルデータを返すモックを用意しています。

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn jista.app.main:app --reload
```

## 利用可能なエンドポイント

- `GET /health` - ヘルスチェック
- `GET /events` - イベント一覧（サンプルデータ）
- `GET /events/{event_id}/start-times?competitor=` - 指定イベントのスタート時刻サンプル。`competitor` を指定すると簡易フィルタを実行

将来的には Japan-O-Entry のサイトをクローリングして JSON/PDF から情報を取得する実装に置き換えます。
