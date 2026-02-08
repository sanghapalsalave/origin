/**
 * Authentication API hooks and functions
 */
import {useMutation} from '@tanstack/react-query';
import apiClient from './client';
import {useAuthStore} from '../stores/authStore';

interface LoginRequest {
  email: string;
  password: string;
}

interface RegisterRequest {
  name: string;
  email: string;
  password: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user_id: string;
}

interface ForgotPasswordRequest {
  email: string;
}

/**
 * Login mutation hook
 */
export const useLogin = () => {
  const {setTokens} = useAuthStore();

  return useMutation({
    mutationFn: async (data: LoginRequest) => {
      const response = await apiClient.post<AuthResponse>('/auth/login', data);
      return response.data;
    },
    onSuccess: async (data) => {
      await setTokens(data.access_token, data.refresh_token, data.user_id);
    },
  });
};

/**
 * Register mutation hook
 */
export const useRegister = () => {
  const {setTokens} = useAuthStore();

  return useMutation({
    mutationFn: async (data: RegisterRequest) => {
      const response = await apiClient.post<AuthResponse>('/auth/register', data);
      return response.data;
    },
    onSuccess: async (data) => {
      await setTokens(data.access_token, data.refresh_token, data.user_id);
    },
  });
};

/**
 * Logout mutation hook
 */
export const useLogout = () => {
  const {clearAuth} = useAuthStore();

  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout');
    },
    onSuccess: async () => {
      await clearAuth();
    },
    onError: async () => {
      // Clear auth even if logout request fails
      await clearAuth();
    },
  });
};

/**
 * Forgot password mutation hook
 */
export const useForgotPassword = () => {
  return useMutation({
    mutationFn: async (data: ForgotPasswordRequest) => {
      const response = await apiClient.post('/auth/forgot-password', data);
      return response.data;
    },
  });
};
