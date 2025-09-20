# Python 3.11の公式イメージを使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# アプリケーションコードをコピー
COPY jista/ ./jista/

# ポート8000を公開
EXPOSE 8000

# 環境変数を設定
ENV PORT=8000
ENV HOST=0.0.0.0

# Cloud Run用の起動コマンド
CMD ["uvicorn", "jista.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
