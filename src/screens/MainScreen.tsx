import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Button,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import EventList from "../components/EventList";
import { useEventSelection } from "../hooks/useEventSelection";

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
  const [competitorName, setCompetitorName] = useState("");

  useEffect(() => {
    void refreshEvents();
  }, [refreshEvents]);

  const handleSelectEvent = (eventId: string) => {
    void selectEvent(eventId, competitorName || undefined);
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
        <Button
          title={isLoading ? "更新中..." : "イベントを更新"}
          onPress={() => void refreshEvents()}
          disabled={isLoading}
        />
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
        <Text style={styles.sectionTitle}>イベント一覧</Text>
        {isLoading && events.length === 0 ? (
          <ActivityIndicator style={styles.loader} />
        ) : (
          <EventList events={events} onSelect={handleSelectEvent} />
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>選択したイベントのスタート時刻</Text>
        {selectedEvent ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{selectedEvent.name}</Text>
            <Text style={styles.cardSubtitle}>
              {new Date(selectedEvent.date).toLocaleString()}
            </Text>
            <Text style={styles.cardMeta}>
              取得日時: {new Date(selectedEvent.fetchedAt).toLocaleString()}
            </Text>
            <View style={styles.startTimeList}>
              {selectedEvent.startTimes.map((entry, index) => (
                <View
                  key={`${entry.competitor}-${entry.startTime}`}
                  style={[
                    styles.startTimeRow,
                    index > 0 && styles.startTimeRowSpacing,
                  ]}
                >
                  <Text style={styles.startTimeName}>{entry.competitor}</Text>
                  <Text style={styles.startTimeValue}>{entry.startTime}</Text>
                </View>
              ))}
            </View>
          </View>
        ) : (
          <Text style={styles.sectionDescription}>
            イベントを選択するとスタート時刻がここに表示されます。オフラインでも最新の5件を保存します。
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
});

export default MainScreen;
