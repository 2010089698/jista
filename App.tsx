import { StatusBar } from "expo-status-bar";
import React from "react";
import { SafeAreaView, StyleSheet } from "react-native";

import { EventProvider } from "./src/hooks/useEventSelection";
import MainScreen from "./src/screens/MainScreen";

const App: React.FC = () => {
  return (
    <EventProvider>
      <SafeAreaView style={styles.safeArea}>
        <MainScreen />
        <StatusBar style="dark" />
      </SafeAreaView>
    </EventProvider>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
});

export default App;
