# Cloud Run デプロイガイド

このガイドでは、Jista FastAPIサーバーをGoogle Cloud Runにデプロイする方法を説明します。

## 前提条件

1. Google Cloud アカウント
2. Google Cloud CLI (`gcloud`) がインストール済み
3. Docker がインストール済み
4. Google Cloud プロジェクトが作成済み

## セットアップ

### 1. Google Cloud CLIの認証

```bash
gcloud auth login
gcloud auth configure-docker
```

### 2. プロジェクトIDの設定

```bash
export PROJECT_ID=your-actual-project-id
```

## デプロイ方法

### 方法1: 自動デプロイスクリプトを使用

```bash
cd /home/info/projects/jista/server
./deploy.sh
```

### 方法2: 手動デプロイ

```bash
# 1. Dockerイメージをビルド
docker build -t gcr.io/$PROJECT_ID/jista-server .

# 2. イメージをプッシュ
docker push gcr.io/$PROJECT_ID/jista-server

# 3. Cloud Runにデプロイ
gcloud run deploy jista-server \
  --image gcr.io/$PROJECT_ID/jista-server \
  --region asia-northeast1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10
```

## ローカルテスト

デプロイ前にローカルでテストできます：

```bash
# Dockerイメージをビルド
docker build -t jista-server .

# ローカルで実行
docker run -p 8000:8000 jista-server

# ヘルスチェック
curl http://localhost:8000/health
```

## 環境変数の設定

本番環境で環境変数を設定する場合：

```bash
gcloud run services update jista-server \
  --region asia-northeast1 \
  --set-env-vars "ENVIRONMENT=production,DATABASE_URL=your-database-url"
```

## トラブルシューティング

### よくある問題

1. **認証エラー**: `gcloud auth login` を実行
2. **プロジェクトID未設定**: `export PROJECT_ID=your-project-id` を設定
3. **Docker認証エラー**: `gcloud auth configure-docker` を実行

### ログの確認

```bash
gcloud run services logs read jista-server --region asia-northeast1
```

## エンドポイント

デプロイ後、以下のエンドポイントが利用可能です：

- `GET /health` - ヘルスチェック
- `GET /events` - イベント一覧
- `GET /events/{event_id}/start-times` - スタート時刻取得

## コスト最適化

- 最小インスタンス数を0に設定（コールドスタートあり）
- 最大インスタンス数を適切に設定
- メモリとCPUの使用量を監視
