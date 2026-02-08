/**
 * Icebreaker screen displaying personalized questions for new squads
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView, FlatList} from 'react-native';
import {Text, Card, Button, Avatar, Chip} from 'react-native-paper';
import {theme} from '../../theme';

interface IcebreakerQuestion {
  id: string;
  question: string;
  for_member: string;
  member_avatar?: string;
  posted_at: string;
  is_answered: boolean;
}

// Mock data
const MOCK_ICEBREAKERS: IcebreakerQuestion[] = [
  {
    id: '1',
    question: 'What inspired you to learn web development?',
    for_member: 'Alice Johnson',
    posted_at: '2024-02-08T10:00:00Z',
    is_answered: false,
  },
  {
    id: '2',
    question: 'Share your favorite coding project you\'ve worked on!',
    for_member: 'Bob Smith',
    posted_at: '2024-02-08T10:05:00Z',
    is_answered: true,
  },
  {
    id: '3',
    question: 'What\'s one technology you\'re excited to master this month?',
    for_member: 'Carol Davis',
    posted_at: '2024-02-08T10:10:00Z',
    is_answered: false,
  },
];

export const IcebreakerScreen: React.FC = () => {
  const [icebreakers, setIcebreakers] = useState<IcebreakerQuestion[]>(MOCK_ICEBREAKERS);

  const handleAnswer = (id: string) => {
    // Navigate to chat or answer modal
    console.log('Answer icebreaker:', id);
  };

  const renderIcebreaker = ({item}: {item: IcebreakerQuestion}) => {
    const postedTime = new Date(item.posted_at);
    const now = new Date();
    const hoursAgo = Math.floor((now.getTime() - postedTime.getTime()) / (1000 * 60 * 60));

    return (
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.header}>
            <Avatar.Text
              size={40}
              label={item.for_member.split(' ').map(n => n[0]).join('')}
              style={styles.avatar}
            />
            <View style={styles.headerText}>
              <Text variant="titleMedium" style={styles.memberName}>
                {item.for_member}
              </Text>
              <Text variant="bodySmall" style={styles.timeText}>
                {hoursAgo < 1 ? 'Just now' : `${hoursAgo}h ago`}
              </Text>
            </View>
            {item.is_answered && (
              <Chip icon="check" style={styles.answeredChip} textStyle={styles.answeredText}>
                Answered
              </Chip>
            )}
          </View>

          <Text variant="bodyLarge" style={styles.question}>
            {item.question}
          </Text>

          {!item.is_answered && (
            <Button
              mode="contained"
              onPress={() => handleAnswer(item.id)}
              style={styles.answerButton}>
              Answer in Chat
            </Button>
          )}
        </Card.Content>
      </Card>
    );
  };

  return (
    <View style={styles.container}>
      <View style={styles.headerSection}>
        <Text variant="displaySmall" style={styles.title}>
          Icebreakers
        </Text>
        <Text variant="bodyLarge" style={styles.subtitle}>
          Get to know your squad members!
        </Text>
      </View>

      <FlatList
        data={icebreakers}
        keyExtractor={item => item.id}
        renderItem={renderIcebreaker}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text variant="bodyLarge">No icebreakers yet</Text>
            <Text variant="bodyMedium" style={styles.emptySubtext}>
              Check back soon for personalized questions!
            </Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  headerSection: {
    padding: 24,
    backgroundColor: theme.colors.primary + '10',
  },
  title: {
    color: theme.colors.primary,
    marginBottom: 8,
  },
  subtitle: {
    color: theme.colors.text,
  },
  listContent: {
    padding: 16,
  },
  card: {
    marginBottom: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatar: {
    backgroundColor: theme.colors.primary,
  },
  headerText: {
    flex: 1,
    marginLeft: 12,
  },
  memberName: {
    color: theme.colors.text,
  },
  timeText: {
    color: theme.colors.text,
    opacity: 0.6,
  },
  answeredChip: {
    backgroundColor: theme.colors.secondary + '20',
    height: 28,
  },
  answeredText: {
    color: theme.colors.secondary,
    fontSize: 11,
  },
  question: {
    color: theme.colors.text,
    marginBottom: 16,
    fontStyle: 'italic',
  },
  answerButton: {
    marginTop: 8,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
  },
  emptySubtext: {
    marginTop: 8,
    color: theme.colors.text,
    opacity: 0.6,
  },
});
