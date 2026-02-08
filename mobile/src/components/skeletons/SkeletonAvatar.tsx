/**
 * Skeleton avatar component for loading states
 */
import React, {useEffect, useRef} from 'react';
import {StyleSheet, Animated} from 'react-native';
import {theme} from '../../theme';

interface SkeletonAvatarProps {
  size?: number;
  style?: any;
}

export const SkeletonAvatar: React.FC<SkeletonAvatarProps> = ({
  size = 40,
  style,
}) => {
  const animatedValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(animatedValue, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(animatedValue, {
          toValue: 0,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    );

    animation.start();

    return () => animation.stop();
  }, [animatedValue]);

  const opacity = animatedValue.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.7],
  });

  return (
    <Animated.View
      style={[
        styles.avatar,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          opacity,
        },
        style,
      ]}
    />
  );
};

const styles = StyleSheet.create({
  avatar: {
    backgroundColor: theme.colors.surface,
  },
});
