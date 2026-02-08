/**
 * Syllabus view screen with daily tasks and completion tracking
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView, FlatList} from 'react-native';
import {Text, Card, Checkbox, ProgressBar, Button, Chip, IconButton} from 'react-native-paper';
import {useRoute, RouteProp} from '@react-navigation/native';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {SyllabusSkeleton} from '../../components/skeletons';
import {TouchableCard} from '../../components/touchable';
import {theme} from '../../theme';

type SyllabusViewScreenRouteProp = RouteProp<RootStackParamList, 'SyllabusView'>;

interface Task {
  id: string;
  title: string;
  description: string;
  type: 'reading' | 'coding' | 'project';
  estimated_time: number; // minutes
  is_completed: boolean;
}

interface SyllabusDay {
  day_number: number;
  title: string;
  description: string;
  is_unlocked: boolean;
  is_completed: boolean;
  tasks: Task[];
}

interface Syllabus {
  id: string;
  squad_name: string;
  total_days: number;
  current_day: number;
  completion_percentage: number;
  days: SyllabusDay[];
}

// Mock data
const MOCK_SYLLABUS: Syllabus = {
  id: '1',
  squad_name: 'Squad Alpha',
  total_days: 30,
  current_day: 3,
  completion_percentage: 0.15,
  days: [
    {
      day_number: 1,
      title: 'Introduction to React Native',
      description: 'Learn the basics of React Native and set up your development environment',
      is_unlocked: true,
      is_completed: true,
      tasks: [
        {
          id: '1',
          title: 'Read React Native documentation',
          description: 'Go through the official getting started guide',
          type: 'reading',
          estimated_time: 60,
          is_completed: true,
        },
        {
          id: '2',
          title: 'Set up development environment',
          description: 'Install Node.js, React Native CLI, and Android Studio',
          type: 'coding',
          estimated_time: 90,
          is_completed: true,
        },
      ],
    },
    {
      day_number: 2,
      title: 'Components and Props',
      description: 'Understanding React Native components and how to pass data',
      is_unlocked: true,
      is_completed: true,
      tasks: [
        {
          id: '3',
          title: 'Learn about functional components',
          description: 'Study functional components and hooks',
          type: 'reading',
          estimated_time: 45,
          is_completed: true,
        },
        {
          id: '4',
          title: 'Build a simple component',
          description: 'Create a reusable button component',
          type: 'coding',
          estimated_time: 60,
          is_completed: true,
        },
      ],
    },
    {
      day_number: 3,
      title: 'State Management',
      description: 'Learn how to manage state in React Native applications',
      is_unlocked: true,
      is_completed: false,
      tasks: [
        {
          id: '5',
          title: 'Study useState and useEffect',
          description: 'Understand React hooks for state management',
          type: 'reading',
          estimated_time: 50,
          is_completed: false,
        },
        {
          id: '6',
          title: 'Build a counter app',
          description: 'Create an app with state management',
          type: 'coding',
          estimated_time: 75,
          is_completed: false,
        },
      ],
    },
  ],
};

export const SyllabusViewScreen: React.FC = () => {
  const route = useRoute<SyllabusViewScreenRouteProp>();
  const [loading, setLoading] = useState(false);
  const [syllabus, setSyllabus] = useState<Syllabus>(MOCK_SYLLABUS);
  const [expandedDay, setExpandedDay] = useState<number | null>(syllabus.current_day);

  const handleTaskToggle = (dayNumber: number, taskId: string) => {
    setSyllabus(prev => ({
      ...prev,
      days: prev.days.map(day =>
        day.day_number === dayNumber
          ? {
              ...day,
              tasks: day.tasks.map(task =>
                task.id === taskId
                  ? {...task, is_completed: !task.is_completed}
                  : task
              ),
            }
          : day
      ),
    }));
  };

  const handleDayPress = (dayNumber: number) => {
    setExpandedDay(expandedDay === dayNumber ? null : dayNumber);
  };

  const getTaskIcon = (type: string) => {
    switch (type) {
      case 'reading':
        return 'book-open-variant';
      case 'coding':
        return 'code-braces';
      case 'project':
        return 'folder-multiple';
      default:
        return 'checkbox-marked-circle';
    }
  };

  if (loading) {
    return <SyllabusSkeleton />;
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text variant="headlineMedium" style={styles.title}>
          30-Day Syllabus
        </Text>
        <Text variant="bodyMedium" style={styles.subtitle}>
          {syllabus.squad_name}
        </Text>
        
        <View style={styles.progressContainer}>
          <View style={styles.progressHeader}>
            <Text variant="bodyMedium">Overall Progress</Text>
            <Text variant="bodyMedium" style={styles.progressText}>
              {Math.round(syllabus.completion_percentage * 100)}%
            </Text>
          </View>
          <ProgressBar
            progress={syllabus.completion_percentage}
            color={theme.colors.secondary}
            style={styles.progressBar}
          />
          <Text variant="bodySmall" style={styles.dayCounter}>
            Day {syllabus.current_day} of {syllabus.total_days}
          </Text>
        </View>
      </View>

      <View style={styles.content}>
        {syllabus.days.map((day) => (
          <TouchableCard
            key={day.day_number}
            onPress={() => day.is_unlocked && handleDayPress(day.day_number)}
            style={styles.dayCard}>
            <Card style={[!day.is_unlocked && styles.lockedCard]}>
              <Card.Content>
                <View style={styles.dayHeader}>
                  <View style={styles.dayTitleContainer}>
                    <Text variant="titleMedium" style={styles.dayTitle}>
                      Day {day.day_number}: {day.title}
                    </Text>
                    {day.is_completed && (
                      <Chip icon="check" style={styles.completedChip} textStyle={styles.completedText}>
                        Completed
                      </Chip>
                    )}
                    {!day.is_unlocked && (
                      <Chip icon="lock" style={styles.lockedChip}>
                        Locked
                      </Chip>
                    )}
                  </View>
                  {day.is_unlocked && (
                    <IconButton
                      icon={expandedDay === day.day_number ? 'chevron-up' : 'chevron-down'}
                      size={20}
                    />
                  )}
                </View>

                <Text variant="bodyMedium" style={styles.dayDescription}>
                  {day.description}
                </Text>

                {expandedDay === day.day_number && day.is_unlocked && (
                  <View style={styles.tasksContainer}>
                    {day.tasks.map((task) => (
                      <View key={task.id} style={styles.taskItem}>
                        <Checkbox
                          status={task.is_completed ? 'checked' : 'unchecked'}
                          onPress={() => handleTaskToggle(day.day_number, task.id)}
                          color={theme.colors.primary}
                        />
                        <View style={styles.taskContent}>
                          <View style={styles.taskHeader}>
                            <IconButton
                              icon={getTaskIcon(task.type)}
                              size={16}
                              style={styles.taskIcon}
                            />
                            <Text
                              variant="bodyMedium"
                              style={[
                                styles.taskTitle,
                                task.is_completed && styles.completedTask,
                              ]}>
                              {task.title}
                            </Text>
                          </View>
                          <Text variant="bodySmall" style={styles.taskDescription}>
                            {task.description}
                          </Text>
                          <Text variant="bodySmall" style={styles.estimatedTime}>
                            ⏱️ {task.estimated_time} min
                          </Text>
                        </View>
                      </View>
                    ))}
                  </View>
                )}
              </Card.Content>
            </Card>
          </TouchableCard>
        ))}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    padding: 16,
    backgroundColor: theme.colors.primary + '10',
  },
  title: {
    color: theme.colors.primary,
    marginBottom: 4,
  },
  subtitle: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 16,
  },
  progressContainer: {
    marginTop: 8,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  progressText: {
    color: theme.colors.primary,
    fontWeight: '600',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginBottom: 8,
  },
  dayCounter: {
    color: theme.colors.text,
    opacity: 0.6,
  },
  content: {
    padding: 16,
  },
  dayCard: {
    marginBottom: 12,
  },
  lockedCard: {
    opacity: 0.6,
  },
  dayHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  dayTitleContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
  },
  dayTitle: {
    color: theme.colors.primary,
  },
  completedChip: {
    backgroundColor: theme.colors.secondary + '20',
    height: 24,
  },
  completedText: {
    color: theme.colors.secondary,
    fontSize: 10,
  },
  lockedChip: {
    backgroundColor: theme.colors.surface,
    height: 24,
  },
  dayDescription: {
    color: theme.colors.text,
    marginBottom: 12,
  },
  tasksContainer: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: theme.colors.surface,
  },
  taskItem: {
    flexDirection: 'row',
    marginBottom: 16,
  },
  taskContent: {
    flex: 1,
    marginLeft: 8,
  },
  taskHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  taskIcon: {
    margin: 0,
    marginRight: 4,
  },
  taskTitle: {
    flex: 1,
    color: theme.colors.text,
  },
  completedTask: {
    textDecorationLine: 'line-through',
    opacity: 0.6,
  },
  taskDescription: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 4,
  },
  estimatedTime: {
    color: theme.colors.text,
    opacity: 0.5,
  },
});
