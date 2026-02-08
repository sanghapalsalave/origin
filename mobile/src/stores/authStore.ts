/**
 * Authentication state management using Zustand
 * Implements secure token storage with AsyncStorage
 */
import {create} from 'zustand';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  setTokens: (accessToken: string, refreshToken: string, userId: string) => Promise<void>;
  clearAuth: () => Promise<void>;
  loadAuth: () => Promise<void>;
}

// Storage keys
const STORAGE_KEYS = {
  ACCESS_TOKEN: '@origin:accessToken',
  REFRESH_TOKEN: '@origin:refreshToken',
  USER_ID: '@origin:userId',
};

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  accessToken: null,
  refreshToken: null,
  userId: null,

  setTokens: async (accessToken: string, refreshToken: string, userId: string) => {
    try {
      // Store tokens securely in AsyncStorage
      await AsyncStorage.multiSet([
        [STORAGE_KEYS.ACCESS_TOKEN, accessToken],
        [STORAGE_KEYS.REFRESH_TOKEN, refreshToken],
        [STORAGE_KEYS.USER_ID, userId],
      ]);
      
      set({
        isAuthenticated: true,
        accessToken,
        refreshToken,
        userId,
      });
    } catch (error) {
      console.error('Failed to store auth tokens:', error);
      throw error;
    }
  },

  clearAuth: async () => {
    try {
      await AsyncStorage.multiRemove([
        STORAGE_KEYS.ACCESS_TOKEN,
        STORAGE_KEYS.REFRESH_TOKEN,
        STORAGE_KEYS.USER_ID,
      ]);
      
      set({
        isAuthenticated: false,
        accessToken: null,
        refreshToken: null,
        userId: null,
      });
    } catch (error) {
      console.error('Failed to clear auth tokens:', error);
      throw error;
    }
  },

  loadAuth: async () => {
    try {
      const values = await AsyncStorage.multiGet([
        STORAGE_KEYS.ACCESS_TOKEN,
        STORAGE_KEYS.REFRESH_TOKEN,
        STORAGE_KEYS.USER_ID,
      ]);
      
      const accessToken = values[0][1];
      const refreshToken = values[1][1];
      const userId = values[2][1];
      
      if (accessToken && refreshToken && userId) {
        set({
          isAuthenticated: true,
          accessToken,
          refreshToken,
          userId,
        });
      }
    } catch (error) {
      console.error('Failed to load auth tokens:', error);
      // Don't throw - just leave user unauthenticated
    }
  },
}));
