import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { JOEEvent } from "../services/api";

type Props = {
  events: JOEEvent[];
  onSelect: (event: JOEEvent) => void;
};

const formatDate = (date: string) => {
  try {
    const dateObj = new Date(date);
    return dateObj.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return date;
  }
};

const getStatusColor = (status: string) => {
  if (status.includes('受付中')) {
    return '#4CAF50'; // 緑
  } else if (status.includes('締切済')) {
    return '#F44336'; // 赤
  } else if (status.includes('まもなく')) {
    return '#FF9800'; // オレンジ
  }
  return '#757575'; // グレー
};

export const JOEEventList: React.FC<Props> = ({ events, onSelect }) => {
  if (events.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>
          Japan-O-Entryからイベント一覧を取得中...
        </Text>
      </View>
    );
  }

  return (
    <View>
      {events.map((event) => (
        <TouchableOpacity 
          key={event.id} 
          style={styles.item} 
          onPress={() => onSelect(event)}
        >
          <View style={styles.itemHeader}>
            <Text style={styles.itemTitle}>{event.name}</Text>
            <Text style={[styles.statusText, { color: getStatusColor(event.status) }]}>
              {event.status}
            </Text>
          </View>
          <Text style={styles.itemSubtitle}>{formatDate(event.date)}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  emptyContainer: {
    padding: 20,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
  },
  item: {
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  itemTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    flex: 1,
    marginRight: 8,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '500',
  },
  itemSubtitle: {
    fontSize: 14,
    color: '#666',
  },
});
