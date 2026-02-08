/**
 * Skeleton screen for profile loading state
 */
import React from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {SkeletonAvatar} from './SkeletonAvatar';
import {SkeletonText} from './SkeletonText';
import {SkeletonCard} from './SkeletonCard';
import {theme} from '../../theme';

export const ProfileSkeleton: React.FC = () => {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Profile Header */}
      <View style={styles.header}>
        <SkeletonAvatar size={80} style={styles.avatar} />
        <SkeletonText width={150} height={24} style={styles.name} />
        <SkeletonText width={200} height={14} style={styles.bio} />
      </View>

      {/* Stats Section */}
      <View style={styles.statsContainer}>
        {Array.from({length: 3}).map((_, index) => (
          <View key={index} style={styles.statCard}>
            <SkeletonText width={60} height={28} />
            <SkeletonText width={80} height={12} style={styles.statLabel} />
          </View>
        ))}
      </View>

      {/* Content Sections */}
      <View style={styles.section}>
        <SkeletonText width={120} height={20} style={styles.sectionTitle} />
        <SkeletonCard height={100} style={styles.card} />
      </View>

      <View style={styles.section}>
        <SkeletonText width={140} height={20} style={styles.sectionTitle} />
        <SkeletonCard height={150} style={styles.card} />
      </View>
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
  header: {
    alignItems: 'center',
    marginBottom: 24,
  },
  avatar: {
    marginBottom: 16,
  },
  name: {
    marginBottom: 8,
  },
  bio: {
    marginBottom: 4,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 24,
  },
  statCard: {
    alignItems: 'center',
  },
  statLabel: {
    marginTop: 8,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    marginBottom: 12,
  },
  card: {
    marginBottom: 8,
  },
});
