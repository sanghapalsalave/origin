/**
 * Skeleton screen for chat loading state
 */
import React from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {SkeletonAvatar} from './SkeletonAvatar';
import {SkeletonText} from './SkeletonText';
import {SkeletonCard} from './SkeletonCard';
import {theme} from '../../theme';

export const ChatSkeleton: React.FC = () => {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {Array.from({length: 8}).map((_, index) => (
        <View
          key={index}
          style={[
            styles.messageContainer,
            index % 2 === 0 ? styles.messageLeft : styles.messageRight,
          ]}>
          {index % 2 === 0 && <SkeletonAvatar size={32} style={styles.avatar} />}
          <View style={styles.messageBubble}>
            <SkeletonText width="100%" height={12} lines={Math.floor(Math.random() * 2) + 1} />
          </View>
          {index % 2 !== 0 && <SkeletonAvatar size={32} style={styles.avatar} />}
        </View>
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    padding: 16,
  },
  messageContainer: {
    flexDirection: 'row',
    marginBottom: 16,
    alignItems: 'flex-end',
  },
  messageLeft: {
    justifyContent: 'flex-start',
  },
  messageRight: {
    justifyContent: 'flex-end',
  },
  avatar: {
    marginHorizontal: 8,
  },
  messageBubble: {
    maxWidth: '70%',
    padding: 12,
    backgroundColor: theme.colors.surface,
    borderRadius: 16,
  },
});
