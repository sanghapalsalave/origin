/**
 * Error tracking service for mobile app
 * Integrates with Sentry or similar error tracking service
 */

// Flag to track if error tracking is initialized
let isInitialized = false;

interface ErrorContext {
  [key: string]: any;
}

interface UserContext {
  id: string;
  email?: string;
  username?: string;
}

/**
 * Initialize error tracking service
 */
export const initErrorTracking = (): void => {
  if (isInitialized) {
    return;
  }

  try {
    // TODO: Initialize Sentry or similar service
    // Example with Sentry:
    // import * as Sentry from '@sentry/react-native';
    // 
    // Sentry.init({
    //   dsn: 'YOUR_SENTRY_DSN',
    //   environment: __DEV__ ? 'development' : 'production',
    //   enableAutoSessionTracking: true,
    //   sessionTrackingIntervalMillis: 10000,
    //   tracesSampleRate: 0.1,
    // });

    isInitialized = true;
    console.log('Error tracking initialized');
  } catch (error) {
    console.error('Failed to initialize error tracking:', error);
  }
};

/**
 * Capture an exception
 */
export const captureException = (
  error: Error,
  context?: ErrorContext,
  level: 'error' | 'warning' | 'info' = 'error'
): void => {
  if (!isInitialized) {
    console.error('Exception:', error, context);
    return;
  }

  try {
    // TODO: Send to error tracking service
    // Example with Sentry:
    // import * as Sentry from '@sentry/react-native';
    // 
    // if (context) {
    //   Sentry.withScope((scope) => {
    //     scope.setLevel(level);
    //     Object.entries(context).forEach(([key, value]) => {
    //       scope.setContext(key, value);
    //     });
    //     Sentry.captureException(error);
    //   });
    // } else {
    //   Sentry.captureException(error);
    // }

    console.error('Exception captured:', error, context);
  } catch (e) {
    console.error('Failed to capture exception:', e);
  }
};

/**
 * Capture a message
 */
export const captureMessage = (
  message: string,
  level: 'error' | 'warning' | 'info' = 'info',
  context?: ErrorContext
): void => {
  if (!isInitialized) {
    console.log('Message:', message, context);
    return;
  }

  try {
    // TODO: Send to error tracking service
    // Example with Sentry:
    // import * as Sentry from '@sentry/react-native';
    // 
    // if (context) {
    //   Sentry.withScope((scope) => {
    //     scope.setLevel(level);
    //     Object.entries(context).forEach(([key, value]) => {
    //       scope.setContext(key, value);
    //     });
    //     Sentry.captureMessage(message);
    //   });
    // } else {
    //   Sentry.captureMessage(message, level);
    // }

    console.log('Message captured:', message, context);
  } catch (e) {
    console.error('Failed to capture message:', e);
  }
};

/**
 * Set user context
 */
export const setUserContext = (user: UserContext): void => {
  if (!isInitialized) {
    return;
  }

  try {
    // TODO: Set user context in error tracking service
    // Example with Sentry:
    // import * as Sentry from '@sentry/react-native';
    // 
    // Sentry.setUser({
    //   id: user.id,
    //   email: user.email,
    //   username: user.username,
    // });

    console.log('User context set:', user.id);
  } catch (e) {
    console.error('Failed to set user context:', e);
  }
};

/**
 * Clear user context
 */
export const clearUserContext = (): void => {
  if (!isInitialized) {
    return;
  }

  try {
    // TODO: Clear user context in error tracking service
    // Example with Sentry:
    // import * as Sentry from '@sentry/react-native';
    // Sentry.setUser(null);

    console.log('User context cleared');
  } catch (e) {
    console.error('Failed to clear user context:', e);
  }
};

/**
 * Add breadcrumb for context
 */
export const addBreadcrumb = (
  message: string,
  category: string = 'default',
  level: 'error' | 'warning' | 'info' = 'info',
  data?: ErrorContext
): void => {
  if (!isInitialized) {
    return;
  }

  try {
    // TODO: Add breadcrumb to error tracking service
    // Example with Sentry:
    // import * as Sentry from '@sentry/react-native';
    // 
    // Sentry.addBreadcrumb({
    //   message,
    //   category,
    //   level,
    //   data,
    // });

    console.log('Breadcrumb added:', message, category);
  } catch (e) {
    console.error('Failed to add breadcrumb:', e);
  }
};

/**
 * Track screen view
 */
export const trackScreenView = (screenName: string): void => {
  addBreadcrumb(`Screen: ${screenName}`, 'navigation', 'info');
};

/**
 * Track user action
 */
export const trackUserAction = (action: string, data?: ErrorContext): void => {
  addBreadcrumb(action, 'user', 'info', data);
};
