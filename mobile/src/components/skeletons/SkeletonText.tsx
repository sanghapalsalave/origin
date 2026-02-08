/**
 * Skeleton text component for loading states
 */
import React, {useEffect, useRef} from 'react';
import {View, StyleSheet, Animated} from 'react-native';
import {theme} from '../../theme';

interface SkeletonTextProps {
  width?: number | string;
  height?: number;
  lines?: number;
  style?: any;
}

export const SkeletonText: React.FC<SkeletonTextProps> = ({
  width = '100%',
  height = 16,
  lines = 1,
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
    <View style={style}>
      {Array.from({length: lines}).map((_, index) => (
        <Animated.View
          key={index}
          style={[
            styles.line,
            {
              width: index === lines - 1 ? '70%' : width,
              height,
              opacity,
              marginBottom: index < lines - 1 ? 8 : 0,
            },
          ]}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  line: {
    backgroundColor: theme.colors.surface,
    borderRadius: 4,
  },
});
