/**
 * ORIGIN Learning Platform Mobile App
 * Main application entry point
 */
import React, {useEffect, useState, useRef} from 'react';
import {View, ActivityIndicator, StyleSheet} from 'react-native';
import {NavigationContainer, NavigationContainerRef} from '@react-navigation/native';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {Provider as PaperProvider} from 'react-native-paper';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import {theme} from './src/theme';
import {AppNavigator} from './src/navigation/AppNavigator';
import {useAuthStore} from './src/stores/authStore';
import {notificationService} from './src/services/notificationService';
import {useNotifications} from './src/hooks/useNotifications';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

function AppContent(): JSX.Element {
  const [isLoading, setIsLoading] = useState(true);
  const loadAuth = useAuthStore((state) => state.loadAuth);
  const navigationRef = useRef<NavigationContainerRef<any>>(null);
  
  // Initialize notifications
  useNotifications();

  useEffect(() => {
    // Load stored authentication tokens on app start
    const initializeAuth = async () => {
      try {
        await loadAuth();
      } catch (error) {
        console.error('Failed to initialize auth:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, [loadAuth]);

  useEffect(() => {
    // Set navigation ref for notification handling
    if (navigationRef.current) {
      notificationService.setNavigationRef(navigationRef.current);
    }
  }, []);

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
      </View>
    );
  }

  return (
    <NavigationContainer ref={navigationRef}>
      <AppNavigator />
    </NavigationContainer>
  );
}

function App(): JSX.Element {
  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <PaperProvider theme={theme}>
          <AppContent />
        </PaperProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background,
  },
});

export default App;
