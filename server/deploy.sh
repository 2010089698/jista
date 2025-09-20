#!/bin/bash

# FastAPIアプリケーションをCloud Runにデプロイするスクリプト

set -e

# 設定
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"asia-northeast1"}
SERVICE_NAME=${SERVICE_NAME:-"jista-server"}
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo "🚀 Jista Server をCloud Runにデプロイします..."
echo "プロジェクトID: $PROJECT_ID"
echo "リージョン: $REGION"
echo "サービス名: $SERVICE_NAME"

# プロジェクトIDが設定されているかチェック
if [ "$PROJECT_ID" = "your-project-id" ]; then
    echo "❌ エラー: PROJECT_IDを設定してください"
    echo "例: export PROJECT_ID=your-actual-project-id"
    exit 1
fi

# Google Cloud CLIでログイン確認
echo "🔐 Google Cloud認証を確認中..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Google Cloudにログインしていません"
    echo "gcloud auth login を実行してください"
    exit 1
fi

# プロジェクトを設定
echo "📋 プロジェクトを設定中..."
gcloud config set project $PROJECT_ID

# Dockerイメージをビルド
echo "🐳 Dockerイメージをビルド中..."
docker build -t $IMAGE_NAME .

# イメージをGoogle Container Registryにプッシュ
echo "📤 イメージをプッシュ中..."
docker push $IMAGE_NAME

# Cloud Runにデプロイ
echo "🚀 Cloud Runにデプロイ中..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --port 8000 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --set-env-vars "ENVIRONMENT=production"

# デプロイ完了
echo "✅ デプロイ完了!"
echo "🌐 サービスURL:"
gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"

echo ""
echo "🧪 ヘルスチェック:"
echo "curl \$(gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)')/health"
