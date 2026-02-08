/**
 * Level-up celebration animation with saffron color theme
 * Triggers on level-up approval
 */
import React, {useEffect, useRef} from 'react';
import {View, StyleSheet, Animated, Dimensions} from 'react-native';
import {Text, IconButton} from 'react-native-paper';
import {theme} from '../../theme';

interface LevelUpCelebrationProps {
  visible: boolean;
  newLevel: number;
  onDismiss: () => void;
}

const {width, height} = Dimensions.get('window');

export const LevelUpCelebration: React.FC<LevelUpCelebrationProps> = ({
  visible,
  newLevel,
  onDismiss,
}) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const confettiAnims = useRef(
    Array.from({length: 20}, () => ({
      x: new Animated.Value(0),
      y: new Animated.Value(0),
      rotate: new Animated.Value(0),
      opacity: new Animated.Value(1),
    }))
  ).current;

  useEffect(() => {
    if (visible) {
      // Start animations
      Animated.parallel([
        // Fade in background
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
        // Scale up level badge
        Animated.spring(scaleAnim, {
          toValue: 1,
          friction: 5,
          tension: 40,
          useNativeDriver: true,
        }),
        // Rotate level badge
        Animated.timing(rotateAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ]).start();

      // Animate confetti
      confettiAnims.forEach((anim, index) => {
        const startX = Math.random() * width;
        const endX = startX + (Math.random() - 0.5) * 200;
        const endY = height;

        Animated.parallel([
          Animated.timing(anim.x, {
            toValue: endX - startX,
            duration: 2000 + Math.random() * 1000,
            useNativeDriver: true,
          }),
          Animated.timing(anim.y, {
            toValue: endY,
            duration: 2000 + Math.random() * 1000,
            useNativeDriver: true,
          }),
          Animated.timing(anim.rotate, {
            toValue: Math.random() * 720,
            duration: 2000 + Math.random() * 1000,
            useNativeDriver: true,
          }),
          Animated.timing(anim.opacity, {
            toValue: 0,
            duration: 2000 + Math.random() * 1000,
            useNativeDriver: true,
          }),
        ]).start();
      });

      // Auto dismiss after 3 seconds
      const timer = setTimeout(() => {
        handleDismiss();
      }, 3000);

      return () => clearTimeout(timer);
    } else {
      // Reset animations
      fadeAnim.setValue(0);
      scaleAnim.setValue(0);
      rotateAnim.setValue(0);
      confettiAnims.forEach(anim => {
        anim.x.setValue(0);
        anim.y.setValue(0);
        anim.rotate.setValue(0);
        anim.opacity.setValue(1);
      });
    }
  }, [visible]);

  const handleDismiss = () => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onDismiss();
    });
  };

  if (!visible) {
    return null;
  }

  const rotate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: fadeAnim,
        },
      ]}>
      {/* Confetti particles */}
      {confettiAnims.map((anim, index) => {
        const startX = (index % 10) * (width / 10);
        const confettiRotate = anim.rotate.interpolate({
          inputRange: [0, 720],
          outputRange: ['0deg', '720deg'],
        });

        return (
          <Animated.View
            key={index}
            style={[
              styles.confetti,
              {
                left: startX,
                backgroundColor:
                  index % 3 === 0
                    ? theme.colors.secondary
                    : index % 3 === 1
                    ? theme.colors.primary
                    : '#FFD700',
                transform: [
                  {translateX: anim.x},
                  {translateY: anim.y},
                  {rotate: confettiRotate},
                ],
                opacity: anim.opacity,
              },
            ]}
          />
        );
      })}

      {/* Level badge */}
      <Animated.View
        style={[
          styles.badgeContainer,
          {
            transform: [{scale: scaleAnim}, {rotate}],
          },
        ]}>
        <View style={styles.badge}>
          <Text variant="displayLarge" style={styles.levelNumber}>
            {newLevel}
          </Text>
          <Text variant="titleMedium" style={styles.levelLabel}>
            LEVEL UP!
          </Text>
        </View>
      </Animated.View>

      {/* Congratulations text */}
      <Animated.View
        style={[
          styles.textContainer,
          {
            opacity: fadeAnim,
            transform: [{scale: scaleAnim}],
          },
        ]}>
        <Text variant="headlineLarge" style={styles.congratsText}>
          🎉 Congratulations! 🎉
        </Text>
        <Text variant="bodyLarge" style={styles.messageText}>
          You've reached Level {newLevel}!
        </Text>
      </Animated.View>

      {/* Close button */}
      <IconButton
        icon="close"
        size={24}
        onPress={handleDismiss}
        style={styles.closeButton}
        iconColor={theme.colors.onPrimary}
      />
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(75, 0, 130, 0.95)', // Purple with transparency
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  confetti: {
    position: 'absolute',
    top: -20,
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  badgeContainer: {
    marginBottom: 40,
  },
  badge: {
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: theme.colors.secondary,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 8,
    borderColor: '#FFD700', // Gold border
    shadowColor: theme.colors.secondary,
    shadowOffset: {width: 0, height: 0},
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 10,
  },
  levelNumber: {
    color: theme.colors.onSecondary,
    fontWeight: 'bold',
    fontSize: 72,
  },
  levelLabel: {
    color: theme.colors.onSecondary,
    fontWeight: 'bold',
    marginTop: -10,
  },
  textContainer: {
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  congratsText: {
    color: theme.colors.onPrimary,
    textAlign: 'center',
    marginBottom: 12,
  },
  messageText: {
    color: theme.colors.onPrimary,
    textAlign: 'center',
  },
  closeButton: {
    position: 'absolute',
    top: 40,
    right: 20,
  },
});
