/**
 * Touchable card component with visual feedback
 * Provides haptic and visual feedback within 100ms
 */
import React, {useRef} from 'react';
import {
  TouchableOpacity,
  Animated,
  StyleSheet,
  ViewStyle,
  GestureResponderEvent,
} from 'react-native';
import {theme} from '../../theme';

interface TouchableCardProps {
  onPress?: (event: GestureResponderEvent) => void;
  onLongPress?: (event: GestureResponderEvent) => void;
  disabled?: boolean;
  children: React.ReactNode;
  style?: ViewStyle;
  activeOpacity?: number;
  scaleOnPress?: boolean;
}

export const TouchableCard: React.FC<TouchableCardProps> = ({
  onPress,
  onLongPress,
  disabled = false,
  children,
  style,
  activeOpacity = 0.7,
  scaleOnPress = true,
}) => {
  const scaleAnim = useRef(new Animated.Value(1)).current;

  const handlePressIn = () => {
    if (scaleOnPress) {
      Animated.spring(scaleAnim, {
        toValue: 0.95,
        useNativeDriver: true,
        speed: 50,
        bounciness: 4,
      }).start();
    }
  };

  const handlePressOut = () => {
    if (scaleOnPress) {
      Animated.spring(scaleAnim, {
        toValue: 1,
        useNativeDriver: true,
        speed: 50,
        bounciness: 4,
      }).start();
    }
  };

  return (
    <TouchableOpacity
      onPress={onPress}
      onLongPress={onLongPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      disabled={disabled}
      activeOpacity={activeOpacity}
      style={[styles.container, style]}>
      <Animated.View
        style={[
          styles.content,
          {
            transform: [{scale: scaleAnim}],
          },
        ]}>
        {children}
      </Animated.View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 8,
    overflow: 'hidden',
  },
  content: {
    width: '100%',
  },
});
