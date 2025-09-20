import { API_BASE_URL } from "../config";
import { EventStartTimes, EventSummary } from "../types/events";

type EventsResponse = {
  events: EventSummary[];
};

type StartTimesResponse = EventStartTimes;

const DEFAULT_TIMEOUT_MS = 10000;

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "API request failed");
  }
  return response.json() as Promise<T>;
};

const fetchWithTimeout = async (
  input: RequestInfo | URL,
  init?: RequestInit & { timeoutMs?: number },
): Promise<Response> => {
  const controller = new AbortController();
  const timeoutMs = init?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new Error(
        "サーバーの応答がタイムアウトしました。ネットワークを確認してください。",
      );
    }
    throw err as Error;
  } finally {
    clearTimeout(id);
  }
};

export const fetchEvents = async (): Promise<EventSummary[]> => {
  try {
    const response = await fetchWithTimeout(`${API_BASE_URL}/events`);
    const data = await handleResponse<EventsResponse>(response);
    return data.events;
  } catch (err) {
    const e = err as Error;
    if (
      !e.message.includes("タイムアウト") &&
      !e.message.includes("API request failed")
    ) {
      throw new Error(
        "イベント一覧の取得に失敗しました。ネットワークまたはAPIのURLを確認してください。",
      );
    }
    throw e;
  }
};

export const fetchEventStartTimes = async (
  eventId: string,
  competitor?: string,
): Promise<EventStartTimes> => {
  const params = competitor
    ? `?competitor=${encodeURIComponent(competitor)}`
    : "";
  try {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/events/${eventId}/start-times${params}`,
    );
    return handleResponse<StartTimesResponse>(response);
  } catch (err) {
    const e = err as Error;
    if (
      !e.message.includes("タイムアウト") &&
      !e.message.includes("API request failed")
    ) {
      throw new Error(
        "スタート時刻の取得に失敗しました。ネットワークまたはAPIのURLを確認してください。",
      );
    }
    throw e;
  }
};

export const fetchStartlistFromJOE = async (
  eventUrl: string,
  competitor?: string,
  competitorClass?: string,
  eventDate?: string,
): Promise<EventStartTimes> => {
  const params = new URLSearchParams();
  if (competitor) params.append('competitor', competitor);
  if (competitorClass) params.append('competitor_class', competitorClass);
  if (eventDate) params.append('event_date', eventDate);
  
  try {
    const response = await fetchWithTimeout(
      `${API_BASE_URL}/events/fetch-startlist?${params}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_url: eventUrl }),
        timeoutMs: 30000, // PDF解析は時間がかかるため30秒に延長
      }
    );
    return handleResponse<StartTimesResponse>(response);
  } catch (err) {
    const e = err as Error;
    if (e.message.includes("タイムアウト")) {
      throw new Error(
        "PDF解析に時間がかかりすぎています。PDFファイルが大きいか、ネットワークが遅い可能性があります。",
      );
    }
    if (e.message.includes("スタートリストらしきリンクが見当たりません")) {
      throw new Error(
        "大会ページにスタートリストが見つかりませんでした。『発行書類』セクションを確認してください。",
      );
    }
    if (e.message.includes("PDFのダウンロードに失敗")) {
      throw new Error(
        "スタートリストPDFのダウンロードに失敗しました。ファイルが削除されているか、アクセス制限があります。",
      );
    }
    if (e.message.includes("氏名で該当行が見つからず")) {
      throw new Error(
        "指定した氏名でスタート時刻が見つかりませんでした。氏名の表記を確認してください。",
      );
    }
    throw new Error(
      `Japan-O-Entryからのスタートリスト取得に失敗しました: ${e.message}`,
    );
  }
};
