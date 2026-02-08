/**
 * Notification service for FCM (Android) and APNs (iOS)
 * Handles push notifications in foreground and background
 */
import messaging from '@react-native-firebase/messaging';
import {Platform, Alert} from 'react-native';
import {NavigationContainerRef} from '@react-navigation/native';
import apiClient from '../api/client';

export type NotificationType = 'mention' | 'syllabus_unlock' | 'peer_review' | 'audio_standup';

interface NotificationData {
  type: NotificationType;
  title: string;
  body: string;
  data?: {
    squadId?: string;
    userId?: string;
    channelId?: string;
    syllabusId?: string;
    reviewId?: string;
  };
}

class NotificationService {
  private navigationRef: NavigationContainerRef<any> | null = null;

  /**
   * Set navigation reference for handling notification taps
   */
  setNavigationRef(ref: NavigationContainerRef<any>) {
    this.navigationRef = ref;
  }

  /**
   * Request notification permissions
   */
  async requestPermission(): Promise<boolean> {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        console.log('Notification permission granted');
      } else {
        console.log('Notification permission denied');
      }

      return enabled;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return false;
    }
  }

  /**
   * Get FCM token for device registration
   */
  async getToken(): Promise<string | null> {
    try {
      const token = await messaging().getToken();
      console.log('FCM Token:', token);
      return token;
    } catch (error) {
      console.error('Error getting FCM token:', error);
      return null;
    }
  }

  /**
   * Register device token with backend
   */
  async registerDevice(token: string): Promise<void> {
    try {
      await apiClient.post('/notifications/devices', {
        device_token: token,
        platform: Platform.OS,
      });
      console.log('Device registered successfully');
    } catch (error) {
      console.error('Error registering device:', error);
    }
  }

  /**
   * Initialize notification listeners
   */
  initialize() {
    // Handle foreground notifications
    messaging().onMessage(async remoteMessage => {
      console.log('Foreground notification:', remoteMessage);
      this.handleForegroundNotification(remoteMessage);
    });

    // Handle background/quit state notifications
    messaging().onNotificationOpenedApp(remoteMessage => {
      console.log('Notification opened app from background:', remoteMessage);
      this.handleNotificationTap(remoteMessage);
    });

    // Handle notification that opened app from quit state
    messaging()
      .getInitialNotification()
      .then(remoteMessage => {
        if (remoteMessage) {
          console.log('Notification opened app from quit state:', remoteMessage);
          this.handleNotificationTap(remoteMessage);
        }
      });

    // Handle token refresh
    messaging().onTokenRefresh(async token => {
      console.log('FCM token refreshed:', token);
      await this.registerDevice(token);
    });
  }

  /**
   * Handle foreground notification display
   */
  private handleForegroundNotification(remoteMessage: any) {
    const {notification, data} = remoteMessage;

    if (notification) {
      // Show alert for foreground notifications
      Alert.alert(
        notification.title || 'New Notification',
        notification.body || '',
        [
          {
            text: 'Dismiss',
            style: 'cancel',
          },
          {
            text: 'View',
            onPress: () => this.handleNotificationTap(remoteMessage),
          },
        ]
      );
    }
  }

  /**
   * Handle notification tap and navigate to relevant screen
   */
  private handleNotificationTap(remoteMessage: any) {
    const {data} = remoteMessage;

    if (!this.navigationRef || !data) {
      return;
    }

    const notificationType = data.type as NotificationType;

    switch (notificationType) {
      case 'mention':
        // Navigate to chat screen
        if (data.squadId) {
          this.navigationRef.navigate('Chat', {squadId: data.squadId});
        }
        break;

      case 'syllabus_unlock':
        // Navigate to syllabus screen
        if (data.squadId) {
          this.navigationRef.navigate('SyllabusView', {squadId: data.squadId});
        }
        break;

      case 'peer_review':
        // Navigate to review screen
        if (data.reviewId) {
          this.navigationRef.navigate('ReviewScreen', {reviewId: data.reviewId});
        }
        break;

      case 'audio_standup':
        // Navigate to squad detail or audio player
        if (data.squadId) {
          this.navigationRef.navigate('SquadDetail', {squadId: data.squadId});
        }
        break;

      default:
        // Navigate to home
        this.navigationRef.navigate('Home');
    }
  }

  /**
   * Setup notification channels (Android only)
   */
  async setupNotificationChannels() {
    if (Platform.OS === 'android') {
      // Create notification channels for different types
      // This would use react-native-push-notification or similar library
      console.log('Setting up Android notification channels');
    }
  }

  /**
   * Clear all notifications
   */
  async clearNotifications() {
    try {
      // Clear badge count (iOS)
      if (Platform.OS === 'ios') {
        await messaging().setApplicationIconBadgeNumber(0);
      }
    } catch (error) {
      console.error('Error clearing notifications:', error);
    }
  }

  /**
   * Unregister device token
   */
  async unregisterDevice() {
    try {
      const token = await this.getToken();
      if (token) {
        await apiClient.delete(`/notifications/devices/${token}`);
        console.log('Device unregistered successfully');
      }
    } catch (error) {
      console.error('Error unregistering device:', error);
    }
  }
}

export const notificationService = new NotificationService();
