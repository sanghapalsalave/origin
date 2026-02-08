/**
 * Toast notification component for success/error feedback
 */
import React, {useEffect, useState} from 'react';
import {View, StyleSheet, Animated} from 'react-native';
import {Text, IconButton} from 'react-native-paper';
import {theme} from '../../theme';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastProps {
  visible: boolean;
  message: string;
  type?: ToastType;
  duration?: number;
  onDismiss: () => void;
}

export const Toast: React.FC<ToastProps> = ({
  visible,
  message,
  type = 'info',
  duration = 3000,
  onDismiss,
}) => {
  const [fadeAnim] = useState(new Animated.Value(0));

  useEffect(() => {
    if (visible) {
      // Fade in
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();

      // Auto dismiss after duration
      const timer = setTimeout(() => {
        handleDismiss();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [visible]);

  const handleDismiss = () => {
    // Fade out
    Animated.timing(fadeAnim, {
      toValue: 0,
      duration: 300,
      useNativeDriver: true,
    }).start(() => {
      onDismiss();
    });
  };

  if (!visible) {
    return null;
  }

  const getBackgroundColor = () => {
    switch (type) {
      case 'success':
        return theme.colors.secondary;
      case 'error':
        return theme.colors.error;
      case 'warning':
        return '#FF9933'; // Saffron
      case 'info':
      default:
        return theme.colors.primary;
    }
  };

  const getIcon = () => {
    switch (type) {
      case 'success':
        return 'check-circle';
      case 'error':
        return 'alert-circle';
      case 'warning':
        return 'alert';
      case 'info':
      default:
        return 'information';
    }
  };

  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: fadeAnim,
          transform: [
            {
              translateY: fadeAnim.interpolate({
                inputRange: [0, 1],
                outputRange: [-20, 0],
              }),
            },
          ],
        },
      ]}>
      <View style={[styles.toast, {backgroundColor: getBackgroundColor()}]}>
        <IconButton
          icon={getIcon()}
          iconColor="#FFFFFF"
          size={20}
          style={styles.icon}
        />
        <Text variant="bodyMedium" style={styles.message}>
          {message}
        </Text>
        <IconButton
          icon="close"
          iconColor="#FFFFFF"
          size={20}
          onPress={handleDismiss}
          style={styles.closeButton}
        />
      </View>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 60,
    left: 16,
    right: 16,
    zIndex: 9999,
  },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  icon: {
    margin: 0,
  },
  message: {
    flex: 1,
    color: '#FFFFFF',
    marginHorizontal: 8,
  },
  closeButton: {
    margin: 0,
  },
});
