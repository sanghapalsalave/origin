/**
 * Touchable component with ripple effect
 * Provides instant visual feedback (< 100ms)
 */
import React from 'react';
import {StyleSheet, ViewStyle, GestureResponderEvent} from 'react-native';
import {TouchableRipple as PaperTouchableRipple} from 'react-native-paper';
import {theme} from '../../theme';

interface TouchableRippleProps {
  onPress?: (event: GestureResponderEvent) => void;
  onLongPress?: (event: GestureResponderEvent) => void;
  disabled?: boolean;
  children: React.ReactNode;
  style?: ViewStyle;
  rippleColor?: string;
  borderless?: boolean;
}

export const TouchableRipple: React.FC<TouchableRippleProps> = ({
  onPress,
  onLongPress,
  disabled = false,
  children,
  style,
  rippleColor = theme.colors.primary + '20',
  borderless = false,
}) => {
  return (
    <PaperTouchableRipple
      onPress={onPress}
      onLongPress={onLongPress}
      disabled={disabled}
      rippleColor={rippleColor}
      borderless={borderless}
      style={[styles.container, style]}>
      {children}
    </PaperTouchableRipple>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 8,
  },
});
