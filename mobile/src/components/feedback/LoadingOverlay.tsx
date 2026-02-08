/**
 * Loading overlay component for full-screen loading states
 */
import React from 'react';
import {View, StyleSheet, Modal} from 'react-native';
import {ActivityIndicator, Text} from 'react-native-paper';
import {theme} from '../../theme';

interface LoadingOverlayProps {
  visible: boolean;
  message?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  visible,
  message = 'Loading...',
}) => {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent>
      <View style={styles.container}>
        <View style={styles.content}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
          {message && (
            <Text variant="bodyLarge" style={styles.message}>
              {message}
            </Text>
          )}
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    backgroundColor: theme.colors.surface,
    padding: 32,
    borderRadius: 12,
    alignItems: 'center',
    minWidth: 200,
  },
  message: {
    marginTop: 16,
    color: theme.colors.text,
  },
});
