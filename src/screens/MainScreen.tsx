import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Button,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import EventList from "../components/EventList";
import { JOEEventList } from "../components/JOEEventList";
import { useEventSelection } from "../hooks/useEventSelection";
import { fetchStartlistFromJOE, fetchJOEEvents, JOEEvent } from "../services/api";
import { persistEvent, loadMostRecentEvent, loadStoredEvents } from "../services/storage";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { EventStartTimes } from "../types/events";

const MainScreen: React.FC = () => {
  const {
    events,
    selectedEvent,
    isOffline,
    isLoading,
    error,
    refreshEvents,
    selectEvent,
  } = useEventSelection();
  const [competitorName, setCompetitorName] = useState("村上巧");
  const [joeEventUrl, setJoeEventUrl] = useState("https://japan-o-entry.com/event/view/2012");
  const [competitorClass, setCompetitorClass] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [isFetchingFromJOE, setIsFetchingFromJOE] = useState(false);
  const [joeError, setJoeError] = useState("");
  const [joeResult, setJoeResult] = useState<EventStartTimes | null>(null);
  const [savedEvents, setSavedEvents] = useState<EventStartTimes[]>([]);
  const [showSavedEvents, setShowSavedEvents] = useState(false);
  const [joeEvents, setJoeEvents] = useState<JOEEvent[]>([]);
  const [isLoadingJOEEvents, setIsLoadingJOEEvents] = useState(false);
  const [joeEventsError, setJoeEventsError] = useState("");
  const [showJOEEvents, setShowJOEEvents] = useState(false);

  // 保存済みイベントを読み込む関数を追加
  const loadSavedEvents = async () => {
    try {
      const events = await loadStoredEvents();
      setSavedEvents(events);
    } catch (error) {
      console.error("保存済みイベントの読み込みに失敗:", error);
    }
  };

  // アプリ起動時に保存済みの最新データを読み込み
  useEffect(() => {
    const loadSavedData = async () => {
      try {
        const savedEvent = await loadMostRecentEvent();
        if (savedEvent) {
          setJoeResult(savedEvent);
          console.log("保存済みデータを読み込みました:", savedEvent);
        }
        // 保存済みイベント一覧も読み込み
        await loadSavedEvents();
      } catch (error) {
        console.error("保存済みデータの読み込みに失敗:", error);
      }
    };
    
    void loadSavedData();
  }, []);

  useEffect(() => {
    void refreshEvents();
  }, [refreshEvents]);

  const handleSelectEvent = (eventId: string) => {
    void selectEvent(eventId, competitorName || undefined);
  };

  // 保存済みイベントを選択する関数
  const handleSelectSavedEvent = (event: EventStartTimes) => {
    setJoeResult(event);
    // selectedEventも更新して一貫性を保つ
    // setStateは利用できないため、setJoeResultのみで対応
    setShowSavedEvents(false);
  };

  // 保存済みイベントを削除する機能
  const handleDeleteSavedEvent = async (eventId: string) => {
    try {
      const events = await loadStoredEvents();
      const filtered = events.filter(e => e.id !== eventId);
      await AsyncStorage.setItem("@jista:selected-events", JSON.stringify(filtered));
      await loadSavedEvents(); // リストを更新
    } catch (error) {
      console.error("イベントの削除に失敗:", error);
    }
  };

  // Japan-O-Entryのイベント一覧を取得する関数
  const handleFetchJOEEvents = async () => {
    setIsLoadingJOEEvents(true);
    setJoeEventsError("");
    
    try {
      const events = await fetchJOEEvents();
      setJoeEvents(events);
      setShowJOEEvents(true);
    } catch (error) {
      console.error("Japan-O-Entryイベント一覧の取得に失敗:", error);
      setJoeEventsError(error instanceof Error ? error.message : "イベント一覧の取得に失敗しました");
    } finally {
      setIsLoadingJOEEvents(false);
    }
  };

  // Japan-O-Entryのイベントを選択した時の処理
  const handleSelectJOEEvent = (event: JOEEvent) => {
    setJoeEventUrl(event.url);
    setShowJOEEvents(false);
  };

  const handleFetchFromJOE = async () => {
    if (!joeEventUrl) {
      setJoeError("大会URLを入力してください");
      return;
    }
    
    // 氏名が空の場合は警告を表示するが、処理は続行
    if (!competitorName) {
      setJoeError("氏名が未入力です。全参加者のスタートリストが表示されます。");
    }
    
    setIsFetchingFromJOE(true);
    setJoeError("");
    setJoeResult(null);
    
    try {
      console.log("API呼び出し開始:", {
        joeEventUrl,
        competitorName,
        competitorClass,
        eventDate
      });
      
      const result = await fetchStartlistFromJOE(
        joeEventUrl,
        competitorName || undefined, // 空の場合はundefinedを渡す
        competitorClass || undefined,
        eventDate || undefined
      );
      
      console.log("APIレスポンス:", result);
      console.log("レスポンスの型:", typeof result);
      console.log("startTimesの長さ:", result?.startTimes?.length);
      console.log("startTimesの内容:", result?.startTimes);
      
      setJoeResult(result);
      
      // 取得したデータをローカルストレージに保存
      if (result) {
        try {
          await persistEvent(result);
          console.log("データをローカルストレージに保存しました");
        } catch (saveError) {
          console.error("ローカルストレージへの保存に失敗:", saveError);
        }
      }
      
      console.log("joeResult設定後:", result);
    } catch (error) {
      console.error("API呼び出しエラー:", error);
      setJoeError((error as Error).message);
    } finally {
      setIsFetchingFromJOE(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Jista</Text>
        <Text style={styles.subtitle}>
          オリエンテーリングイベントのスタート時刻を素早く確認
        </Text>
      </View>

      <View style={styles.section}>
        {isOffline && (
          <Text style={styles.offlineText}>
            オフラインモード: 保存済みのスタート時刻を表示しています。
          </Text>
        )}
        {error && <Text style={styles.errorText}>{error}</Text>}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>氏名（任意）</Text>
        <Text style={styles.sectionDescription}>
          氏名を入力するとサーバー側でスタートリストを絞り込めるようになります。
        </Text>
        <TextInput
          style={styles.input}
          placeholder="例：山田 太郎"
          value={competitorName}
          onChangeText={setCompetitorName}
          autoCapitalize="none"
          autoCorrect={false}
        />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Japan-O-Entry連携</Text>
        <Text style={styles.sectionDescription}>
          Japan-O-Entryの大会ページから直接スタートリストを取得できます。
        </Text>
        
        {/* Japan-O-Entryイベント一覧取得ボタン */}
        <Button
          title={isLoadingJOEEvents ? "取得中..." : "Japan-O-Entryイベント一覧を表示"}
          onPress={handleFetchJOEEvents}
          disabled={isLoadingJOEEvents}
        />
        
        {joeEventsError && <Text style={styles.errorText}>{joeEventsError}</Text>}
        
        {/* Japan-O-Entryイベント一覧表示 */}
        {showJOEEvents && joeEvents.length > 0 && (
          <View style={styles.joeEventsContainer}>
            <Text style={styles.joeEventsTitle}>Japan-O-Entryイベント一覧</Text>
            <JOEEventList events={joeEvents} onSelect={handleSelectJOEEvent} />
            <Button
              title="一覧を閉じる"
              onPress={() => setShowJOEEvents(false)}
            />
          </View>
        )}
        
        <TextInput
          style={styles.input}
          placeholder="大会ページURL（例：https://japan-o-entry.com/event/view/1923）"
          value={joeEventUrl}
          onChangeText={setJoeEventUrl}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
        />
        
        
        {joeError && <Text style={styles.errorText}>{joeError}</Text>}
        
        {/* デバッグ情報を追加 */}
        <Text style={styles.debugText}>
          デバッグ情報:
          {'\n'}URL: "{joeEventUrl}" (長さ: {joeEventUrl.length})
          {'\n'}氏名: "{competitorName}" (長さ: {competitorName.length})
          {'\n'}ボタン無効: {String(isFetchingFromJOE || !joeEventUrl)}
          {'\n'}joeResult: {joeResult ? '設定済み' : 'null'}
          {'\n'}joeError: {joeError || 'なし'}
          {'\n'}isFetchingFromJOE: {String(isFetchingFromJOE)}
          {'\n'}データ保存状態: {joeResult ? '保存済み' : '未保存'}
          {joeResult && (
            <>
              {'\n'}結果名: {joeResult.name}
              {'\n'}スタート時刻数: {joeResult.startTimes?.length || 0}
              {'\n'}最初のスタート時刻: {joeResult.startTimes?.[0]?.competitor} - {joeResult.startTimes?.[0]?.startTime}
            </>
          )}
        </Text>
        
        <Button
          title={isFetchingFromJOE ? "解析中..." : "Japan-O-Entryから取得"}
          onPress={handleFetchFromJOE}
          disabled={isFetchingFromJOE || !joeEventUrl}
        />
      </View>

      {/* 新しいセクション: 保存済みイベント選択 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>保存済みイベント</Text>
        <Text style={styles.sectionDescription}>
          以前に取得・保存したイベントから選択できます。
        </Text>
        
        {savedEvents.length > 0 ? (
          <>
            <Button
              title={`保存済みイベントを表示 (${savedEvents.length}件)`}
              onPress={() => setShowSavedEvents(!showSavedEvents)}
            />
            
            {showSavedEvents && (
              <View style={styles.savedEventsList}>
                {savedEvents.map((event, index) => (
                  <TouchableOpacity
                    key={event.id}
                    style={styles.savedEventItem}
                    onPress={() => handleSelectSavedEvent(event)}
                  >
                    <View style={styles.savedEventContent}>
                      <Text style={styles.savedEventName}>{event.name}</Text>
                      <Text style={styles.savedEventDate}>
                        {new Date(event.date).toLocaleDateString()}
                      </Text>
                      <Text style={styles.savedEventMeta}>
                        スタート時刻: {event.startTimes?.length || 0}件
                      </Text>
                      {/* スタート時刻のプレビューを追加 */}
                      {event.startTimes && event.startTimes.length > 0 && (
                        <View style={styles.startTimePreview}>
                          {event.startTimes.slice(0, 3).map((entry, idx) => (
                            <Text key={idx} style={styles.previewTime}>
                              {entry.competitor}: {entry.startTime}
                            </Text>
                          ))}
                          {event.startTimes.length > 3 && (
                            <Text style={styles.moreText}>
                              ...他{event.startTimes.length - 3}件
                            </Text>
                          )}
                        </View>
                      )}
                      <Text style={styles.savedEventFetched}>
                        取得: {new Date(event.fetchedAt).toLocaleString()}
                      </Text>
                    </View>
                    <TouchableOpacity
                      style={styles.deleteButton}
                      onPress={() => handleDeleteSavedEvent(event.id)}
                    >
                      <Text style={styles.deleteButtonText}>削除</Text>
                    </TouchableOpacity>
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </>
        ) : (
          <Text style={styles.sectionDescription}>
            保存済みのイベントはありません。
          </Text>
        )}
      </View>


    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
    paddingBottom: 32,
    flexGrow: 1,
  },
  header: {
    marginBottom: 8,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
  },
  subtitle: {
    color: "#555",
    marginTop: 4,
  },
  section: {
    marginTop: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: "600",
  },
  sectionDescription: {
    color: "#666",
    lineHeight: 20,
    marginTop: 8,
  },
  offlineText: {
    color: "#0a84ff",
    marginBottom: 8,
  },
  errorText: {
    color: "#ff3b30",
    marginBottom: 8,
  },
  input: {
    borderColor: "#ccc",
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: "#fff",
    marginTop: 8,
  },
  inputSpacing: {
    marginTop: 8,
  },
  loader: {
    marginTop: 12,
  },
  card: {
    padding: 16,
    borderRadius: 12,
    backgroundColor: "#f4f4f7",
    marginTop: 12,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: "600",
  },
  cardSubtitle: {
    color: "#444",
    marginTop: 4,
  },
  cardMeta: {
    color: "#888",
    fontSize: 12,
    marginTop: 4,
  },
  startTimeList: {
    marginTop: 12,
  },
  startTimeRow: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  startTimeRowSpacing: {
    marginTop: 8,
  },
  startTimeName: {
    fontWeight: "500",
  },
  startTimeValue: {
    fontVariant: ["tabular-nums"],
  },
  debugText: {
    fontSize: 12,
    color: "#666",
    marginTop: 8,
    marginBottom: 8,
    backgroundColor: "#f0f0f0",
    padding: 8,
    borderRadius: 4,
  },
  savedEventsList: {
    marginTop: 12,
  },
  savedEventItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 12,
    backgroundColor: "#f8f9fa",
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: "#e9ecef",
  },
  savedEventContent: {
    flex: 1,
  },
  savedEventName: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
  },
  savedEventDate: {
    fontSize: 14,
    color: "#666",
    marginTop: 2,
  },
  savedEventMeta: {
    fontSize: 12,
    color: "#888",
    marginTop: 2,
  },
  savedEventFetched: {
    fontSize: 11,
    color: "#aaa",
    marginTop: 2,
  },
  deleteButton: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: "#ff3b30",
    borderRadius: 6,
  },
  deleteButtonText: {
    color: "#fff",
    fontSize: 12,
    fontWeight: "bold",
  },
  joeEventsContainer: {
    marginTop: 12,
    padding: 12,
    backgroundColor: "#f8f9fa",
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#e9ecef",
  },
  joeEventsTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#333",
    marginBottom: 12,
  },
  startTimePreview: {
    marginTop: 8,
    padding: 8,
    backgroundColor: '#f5f5f5',
    borderRadius: 4,
  },
  previewTime: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  moreText: {
    fontSize: 11,
    color: '#999',
    fontStyle: 'italic',
  },
});

export default MainScreen;
