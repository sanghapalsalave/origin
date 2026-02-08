/**
 * Hook for managing push notifications
 */
import {useEffect, useState} from 'react';
import {notificationService} from '../services/notificationService';

export const useNotifications = () => {
  const [hasPermission, setHasPermission] = useState(false);
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const setupNotifications = async () => {
      // Request permission
      const permission = await notificationService.requestPermission();
      setHasPermission(permission);

      if (permission) {
        // Get FCM token
        const fcmToken = await notificationService.getToken();
        setToken(fcmToken);

        if (fcmToken) {
          // Register device with backend
          await notificationService.registerDevice(fcmToken);
        }

        // Initialize notification listeners
        notificationService.initialize();

        // Setup Android channels
        await notificationService.setupNotificationChannels();
      }
    };

    setupNotifications();

    // Cleanup on unmount
    return () => {
      notificationService.clearNotifications();
    };
  }, []);

  return {
    hasPermission,
    token,
  };
};
