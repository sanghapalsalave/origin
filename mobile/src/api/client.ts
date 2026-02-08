/**
 * API client configuration with Axios
 * Includes error handling, retry logic, and token refresh
 */
import axios, {AxiosError, AxiosRequestConfig, AxiosResponse} from 'axios';
import {useAuthStore} from '../stores/authStore';

// Base API URL - should be configured via environment variables
const API_BASE_URL = __DEV__ 
  ? 'http://localhost:8000/api/v1' 
  : 'https://api.origin-learning.com/api/v1';

// Retry configuration
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000; // 1 second

// Exponential backoff delay calculation
const getRetryDelay = (retryCount: number): number => {
  return INITIAL_RETRY_DELAY * Math.pow(2, retryCount);
};

// Sleep utility for retry delays
const sleep = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const {accessToken} = useAuthStore.getState();
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
      _retryCount?: number;
    };

    // Handle 401 errors (token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const {refreshToken} = useAuthStore.getState();
        if (refreshToken) {
          // Attempt to refresh token
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const {access_token, refresh_token, user_id} = response.data;
          await useAuthStore.getState().setTokens(access_token, refresh_token, user_id);

          // Retry original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${access_token}`;
          }
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, clear auth and redirect to login
        await useAuthStore.getState().clearAuth();
        return Promise.reject(refreshError);
      }
    }

    // Handle 403 errors (forbidden)
    if (error.response?.status === 403) {
      // User doesn't have permission for this resource
      return Promise.reject({
        ...error,
        message: 'You do not have permission to access this resource',
      });
    }

    // Handle 400 errors (validation errors)
    if (error.response?.status === 400) {
      const validationErrors = error.response.data;
      return Promise.reject({
        ...error,
        message: 'Validation failed',
        validationErrors,
      });
    }

    // Handle 429 errors (rate limiting) with retry
    if (error.response?.status === 429) {
      const retryAfter = error.response.headers['retry-after'];
      const retryDelay = retryAfter ? parseInt(retryAfter, 10) * 1000 : 5000;
      
      await sleep(retryDelay);
      return apiClient(originalRequest);
    }

    // Handle network errors and 5xx errors with exponential backoff retry
    const shouldRetry = 
      !error.response || // Network error
      (error.response.status >= 500 && error.response.status < 600); // Server error

    if (shouldRetry) {
      const retryCount = originalRequest._retryCount || 0;
      
      if (retryCount < MAX_RETRIES) {
        originalRequest._retryCount = retryCount + 1;
        const delay = getRetryDelay(retryCount);
        
        await sleep(delay);
        return apiClient(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);

// Error types for better error handling
export interface ApiError {
  message: string;
  status?: number;
  validationErrors?: Record<string, string[]>;
}

// Helper to extract error message from API error
export const getErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error.response?.data?.message) {
      return error.response.data.message;
    }
    if (error.message) {
      return error.message;
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
};

// Helper to check if error is a network error
export const isNetworkError = (error: unknown): boolean => {
  return axios.isAxiosError(error) && !error.response;
};

// Helper to check if error is an authentication error
export const isAuthError = (error: unknown): boolean => {
  return axios.isAxiosError(error) && 
    (error.response?.status === 401 || error.response?.status === 403);
};

// Helper to check if error is a validation error
export const isValidationError = (error: unknown): boolean => {
  return axios.isAxiosError(error) && error.response?.status === 400;
};

export default apiClient;
