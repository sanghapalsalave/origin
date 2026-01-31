/**
 * Authentication state management using Zustand
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

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  accessToken: null,
  refreshToken: null,
  userId: null,

  setTokens: async (accessToken: string, refreshToken: string, userId: string) => {
    await AsyncStorage.setItem('accessToken', accessToken);
    await AsyncStorage.setItem('refreshToken', refreshToken);
    await AsyncStorage.setItem('userId', userId);
    set({
      isAuthenticated: true,
      accessToken,
      refreshToken,
      userId,
    });
  },

  clearAuth: async () => {
    await AsyncStorage.multiRemove(['accessToken', 'refreshToken', 'userId']);
    set({
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      userId: null,
    });
  },

  loadAuth: async () => {
    const [accessToken, refreshToken, userId] = await AsyncStorage.multiGet([
      'accessToken',
      'refreshToken',
      'userId',
    ]);
    
    if (accessToken[1] && refreshToken[1] && userId[1]) {
      set({
        isAuthenticated: true,
        accessToken: accessToken[1],
        refreshToken: refreshToken[1],
        userId: userId[1],
      });
    }
  },
}));
