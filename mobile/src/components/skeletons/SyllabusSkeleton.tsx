/**
 * Skeleton screen for syllabus loading state
 */
import React from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {SkeletonText} from './SkeletonText';
import {SkeletonCard} from './SkeletonCard';
import {theme} from '../../theme';

export const SyllabusSkeleton: React.FC = () => {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <SkeletonText width="60%" height={28} style={styles.title} />
        <SkeletonText width="40%" height={14} style={styles.subtitle} />
      </View>

      {/* Progress Bar */}
      <SkeletonCard height={8} style={styles.progressBar} />

      {/* Daily Tasks */}
      {Array.from({length: 5}).map((_, index) => (
        <View key={index} style={styles.dayCard}>
          <View style={styles.dayHeader}>
            <SkeletonText width={80} height={18} />
            <SkeletonText width={60} height={14} />
          </View>
          <SkeletonText width="100%" height={14} lines={2} style={styles.dayDescription} />
          
          {/* Tasks */}
          <View style={styles.tasksList}>
            {Array.from({length: 3}).map((_, taskIndex) => (
              <View key={taskIndex} style={styles.taskItem}>
                <SkeletonCard width={20} height={20} borderRadius={4} />
                <SkeletonText width="80%" height={14} style={styles.taskText} />
              </View>
            ))}
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
  header: {
    marginBottom: 16,
  },
  title: {
    marginBottom: 8,
  },
  subtitle: {
    marginBottom: 4,
  },
  progressBar: {
    marginBottom: 24,
    borderRadius: 4,
  },
  dayCard: {
    marginBottom: 16,
    padding: 16,
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
  },
  dayHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  dayDescription: {
    marginBottom: 16,
  },
  tasksList: {
    gap: 12,
  },
  taskItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  taskText: {
    marginLeft: 12,
  },
});
