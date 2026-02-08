/**
 * Skeleton screen for guild list loading state
 */
import React from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {SkeletonCard} from './SkeletonCard';
import {SkeletonText} from './SkeletonText';
import {theme} from '../../theme';

export const GuildListSkeleton: React.FC = () => {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {Array.from({length: 5}).map((_, index) => (
        <View key={index} style={styles.guildCard}>
          <SkeletonCard height={120} style={styles.cardImage} />
          <View style={styles.cardContent}>
            <SkeletonText width="80%" height={20} style={styles.title} />
            <SkeletonText width="100%" height={14} lines={2} style={styles.description} />
            <View style={styles.footer}>
              <SkeletonText width={60} height={12} />
              <SkeletonText width={80} height={12} />
            </View>
          </View>
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
  guildCard: {
    marginBottom: 16,
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    overflow: 'hidden',
  },
  cardImage: {
    borderRadius: 0,
  },
  cardContent: {
    padding: 16,
  },
  title: {
    marginBottom: 8,
  },
  description: {
    marginBottom: 12,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});
