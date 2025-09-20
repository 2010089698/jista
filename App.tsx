import { StatusBar } from "expo-status-bar";
import React from "react";
import { StyleSheet } from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";

import { EventProvider } from "./src/hooks/useEventSelection";
import MainScreen from "./src/screens/MainScreen";

const App: React.FC = () => {
  return (
    <SafeAreaProvider>
      <EventProvider>
        <SafeAreaView style={styles.safeArea}>
          <MainScreen />
          <StatusBar style="dark" />
        </SafeAreaView>
      </EventProvider>
    </SafeAreaProvider>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
});

export default App;
