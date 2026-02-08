/**
 * Peer review screen for reviewing submissions
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Text, TextInput, Button, Card, RadioButton, Chip, HelperText} from 'react-native-paper';
import {theme} from '../../theme';

interface ReviewCriteria {
  id: string;
  name: string;
  description: string;
  score: number;
}

export const ReviewScreen: React.FC = () => {
  const [overallRating, setOverallRating] = useState('');
  const [feedback, setFeedback] = useState('');
  const [criteria, setCriteria] = useState<ReviewCriteria[]>([
    {
      id: '1',
      name: 'Code Quality',
      description: 'Clean, readable, and well-organized code',
      score: 0,
    },
    {
      id: '2',
      name: 'Functionality',
      description: 'Project works as intended and meets requirements',
      score: 0,
    },
    {
      id: '3',
      name: 'Documentation',
      description: 'Clear README and code comments',
      score: 0,
    },
    {
      id: '4',
      name: 'Best Practices',
      description: 'Follows industry standards and conventions',
      score: 0,
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Mock submission data
  const submission = {
    id: '1',
    user_name: 'Alice Johnson',
    project_title: 'E-commerce Mobile App',
    project_description: 'A full-featured e-commerce app built with React Native...',
    github_url: 'https://github.com/alice/ecommerce-app',
    demo_url: 'https://demo.example.com',
    submitted_date: '2024-02-01',
  };

  const handleCriteriaScore = (criteriaId: string, score: number) => {
    setCriteria(prev =>
      prev.map(c => (c.id === criteriaId ? {...c, score} : c))
    );
  };

  const handleSubmitReview = async () => {
    setError('');

    // Validation
    if (!overallRating) {
      setError('Please select an overall rating');
      return;
    }

    if (!feedback.trim()) {
      setError('Please provide detailed feedback');
      return;
    }

    if (criteria.some(c => c.score === 0)) {
      setError('Please rate all criteria');
      return;
    }

    setLoading(true);

    try {
      // TODO: Submit review to API
      console.log('Submitting review...');
      // Navigate back or show success message
    } catch (err: any) {
      setError('Failed to submit review. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text variant="displaySmall" style={styles.title}>
          Peer Review
        </Text>
        <Text variant="bodyLarge" style={styles.subtitle}>
          Review {submission.user_name}'s level-up project
        </Text>
      </View>

      {/* Submission Details */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleLarge" style={styles.projectTitle}>
            {submission.project_title}
          </Text>
          <Text variant="bodyMedium" style={styles.projectDescription}>
            {submission.project_description}
          </Text>

          <View style={styles.links}>
            <Chip icon="github" style={styles.linkChip}>
              View Code
            </Chip>
            {submission.demo_url && (
              <Chip icon="web" style={styles.linkChip}>
                Live Demo
              </Chip>
            )}
          </View>

          <Text variant="bodySmall" style={styles.submittedDate}>
            Submitted: {new Date(submission.submitted_date).toLocaleDateString()}
          </Text>
        </Card.Content>
      </Card>

      {/* Review Criteria */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Review Criteria
          </Text>

          {criteria.map((criterion) => (
            <View key={criterion.id} style={styles.criterionContainer}>
              <Text variant="titleSmall" style={styles.criterionName}>
                {criterion.name}
              </Text>
              <Text variant="bodySmall" style={styles.criterionDescription}>
                {criterion.description}
              </Text>

              <View style={styles.ratingButtons}>
                {[1, 2, 3, 4, 5].map((score) => (
                  <Button
                    key={score}
                    mode={criterion.score === score ? 'contained' : 'outlined'}
                    onPress={() => handleCriteriaScore(criterion.id, score)}
                    style={styles.ratingButton}
                    compact>
                    {score}
                  </Button>
                ))}
              </View>
            </View>
          ))}
        </Card.Content>
      </Card>

      {/* Overall Rating */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Overall Rating
          </Text>

          <RadioButton.Group onValueChange={setOverallRating} value={overallRating}>
            <View style={styles.radioOption}>
              <RadioButton value="approve" color={theme.colors.primary} />
              <Text variant="bodyMedium">Approve - Ready to level up</Text>
            </View>
            <View style={styles.radioOption}>
              <RadioButton value="reject" color={theme.colors.error} />
              <Text variant="bodyMedium">Reject - Needs improvement</Text>
            </View>
          </RadioButton.Group>
        </Card.Content>
      </Card>

      {/* Feedback */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Detailed Feedback *
          </Text>

          <TextInput
            label="Your Feedback"
            value={feedback}
            onChangeText={setFeedback}
            mode="outlined"
            multiline
            numberOfLines={8}
            style={styles.feedbackInput}
            disabled={loading}
            placeholder="Provide constructive feedback on strengths, areas for improvement, and suggestions..."
          />

          {error ? (
            <HelperText type="error" visible={!!error} style={styles.error}>
              {error}
            </HelperText>
          ) : null}
        </Card.Content>
      </Card>

      <Card style={styles.infoCard}>
        <Card.Content>
          <Text variant="bodyMedium" style={styles.infoText}>
            💡 Your review will help {submission.user_name} improve. Be constructive and specific in your feedback.
          </Text>
        </Card.Content>
      </Card>

      <View style={styles.actions}>
        <Button
          mode="contained"
          onPress={handleSubmitReview}
          loading={loading}
          disabled={loading}
          style={styles.submitButton}>
          Submit Review
        </Button>
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
  card: {
    margin: 16,
    marginBottom: 0,
  },
  projectTitle: {
    color: theme.colors.primary,
    marginBottom: 12,
  },
  projectDescription: {
    color: theme.colors.text,
    marginBottom: 16,
  },
  links: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 12,
  },
  linkChip: {
    backgroundColor: theme.colors.primary + '10',
  },
  submittedDate: {
    color: theme.colors.text,
    opacity: 0.6,
  },
  sectionTitle: {
    color: theme.colors.primary,
    marginBottom: 16,
  },
  criterionContainer: {
    marginBottom: 24,
  },
  criterionName: {
    color: theme.colors.text,
    marginBottom: 4,
  },
  criterionDescription: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 12,
  },
  ratingButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  ratingButton: {
    flex: 1,
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  feedbackInput: {
    marginBottom: 8,
  },
  error: {
    marginTop: 8,
  },
  infoCard: {
    margin: 16,
    backgroundColor: theme.colors.secondary + '10',
  },
  infoText: {
    color: theme.colors.text,
  },
  actions: {
    padding: 16,
  },
  submitButton: {
    marginBottom: 16,
  },
});
