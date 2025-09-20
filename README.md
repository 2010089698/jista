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

`npm run start` を実行すると Expo の開発サーバーが立ち上がり、Expo Go から接続できるようになります。API はデフォルトで `http://172.30.80.81:8000` を参照するよう設定しています。

### 2. サーバー(FastAPI)

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn jista.app.main:app --reload --host 0.0.0.0 --port 8000
```

API サーバーはポート `8000` で起動します。`/events` でイベント一覧、`/events/{event_id}/start-times` でスタート時刻サンプルを取得できます。

## WSL2 + Expo Go（実機）での接続手順

WSL2 の内部IP(例: 172.x.x.x)にはスマホから直接到達できません。WindowsホストのLAN IPにポート転送し、そのIPをクライアントの `.env` に設定してください。

1. WindowsのPowerShell（管理者）でポート転送を設定

```powershell
# 1) WSL2側のIPを取得
wsl.exe -e sh -c "ip -4 -brief a | grep eth0 | awk '{print $3}' | cut -d/ -f1"

# 2) ポートプロキシを作成（<WSL_IP> を上の結果に置換）
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=8000 connectaddress=<WSL_IP> connectport=8000

# 3) Windowsファイアウォールで許可
New-NetFirewallRule -DisplayName "WSL-8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

2. WindowsのLAN IPを確認してスマホから疎通確認

- スマホのブラウザで `http://<WindowsのLAN IP>:8000/health` が `{"status":"ok"}` になればOK

3. クライアント `.env` を設定（プロジェクト直下）

```dotenv
EXPO_PUBLIC_API_BASE_URL=http://<WindowsのLAN IP>:8000
```

4. Expoを再起動（キャッシュクリア推奨）

```bash
npm run start -- --clear
```

5. Expo Go で再読み込み。イベント一覧が表示されることを確認

補足:
- Androidエミュレータ: `http://10.0.2.2:8000`
- iOSシミュレータ: `http://127.0.0.1:8000`

## 環境変数

現状は `.env` の `EXPO_PUBLIC_API_BASE_URL` を設定することで API の接続先を切り替えられます。未設定時は `src/config.ts` のデフォルトURLが使われます。

## デプロイ情報

### 本番環境（GCP Cloud Run）

サーバーは以下のURLでデプロイ済みです：
- **本番URL**: https://jista-server-994293554156.asia-northeast1.run.app
- **ヘルスチェック**: https://jista-server-994293554156.asia-northeast1.run.app/health

### デプロイ手順

```bash
# 1. Dockerイメージをビルド
cd server
docker build -t gcr.io/jista-472702/jista-server .

# 2. GCP Container Registryにプッシュ
docker push gcr.io/jista-472702/jista-server

# 3. Cloud Runにデプロイ
gcloud run deploy jista-server --image gcr.io/jista-472702/jista-server --platform managed --region asia-northeast1 --allow-unauthenticated
```

### 最近の修正（2024年9月）

- **Queryパラメータ対応**: `fetch-startlist`エンドポイントでクエリパラメータ（`competitor`, `competitor_class`, `event_date`）を正しく受け取れるように修正
- **デプロイ完了**: 修正版が本番環境に反映済み

## 次のステップ

- Japan-O-Entry からの実データ取得実装
- スタート時刻のPDF解析ロジック
- 匿名IDでの継続率計測
- UI/UXのブラッシュアップおよびオフラインキャッシュの充実

