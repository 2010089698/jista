import React from "react";
import {
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { EventSummary } from "../types/events";

type Props = {
  events: EventSummary[];
  onSelect: (eventId: string) => void;
};

const formatDate = (date: string) => new Date(date).toLocaleDateString();

export const EventList: React.FC<Props> = ({ events, onSelect }) => {
  if (events.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>
          オンラインでイベントを取得すると一覧が表示されます。
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      data={events}
      keyExtractor={(item) => item.id}
      renderItem={({ item }) => (
        <TouchableOpacity style={styles.item} onPress={() => onSelect(item.id)}>
          <Text style={styles.itemTitle}>{item.name}</Text>
          <Text style={styles.itemSubtitle}>{formatDate(item.date)}</Text>
        </TouchableOpacity>
      )}
    />
  );
};

const styles = StyleSheet.create({
  emptyContainer: {
    paddingVertical: 16,
    paddingHorizontal: 12,
    alignItems: "center",
  },
  emptyText: {
    color: "#666",
  },
  item: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomColor: "#e0e0e0",
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  itemTitle: {
    fontSize: 16,
    fontWeight: "600",
  },
  itemSubtitle: {
    fontSize: 12,
    color: "#666",
    marginTop: 4,
  },
});

export default EventList;
