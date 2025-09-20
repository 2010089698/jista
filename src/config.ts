const DEFAULT_API_BASE_URL = "http://172.30.80.81:8000";

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL;
// 一時ログ（動作確認用）。不要になったら削除してください。
// eslint-disable-next-line no-console
console.log("API_BASE_URL =", API_BASE_URL);
