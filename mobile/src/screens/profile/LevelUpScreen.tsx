/**
 * Level-up project submission screen
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Text, TextInput, Button, Card, Chip, HelperText} from 'react-native-paper';
import DocumentPicker from 'react-native-document-picker';
import {theme} from '../../theme';

export const LevelUpScreen: React.FC = () => {
  const [projectTitle, setProjectTitle] = useState('');
  const [projectDescription, setProjectDescription] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [demoUrl, setDemoUrl] = useState('');
  const [attachments, setAttachments] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const currentLevel = 5;
  const nextLevel = currentLevel + 1;

  const handleAttachmentPick = async () => {
    try {
      const result = await DocumentPicker.pick({
        type: [DocumentPicker.types.allFiles],
        allowMultiSelection: true,
      });

      setAttachments(prev => [...prev, ...result]);
    } catch (err) {
      if (!DocumentPicker.isCancel(err)) {
        console.error('File picker error:', err);
      }
    }
  };

  const handleSubmit = async () => {
    setError('');

    // Validation
    if (!projectTitle.trim()) {
      setError('Project title is required');
      return;
    }

    if (!projectDescription.trim()) {
      setError('Project description is required');
      return;
    }

    if (!githubUrl.trim()) {
      setError('GitHub repository URL is required');
      return;
    }

    setLoading(true);

    try {
      // TODO: Submit to API
      console.log('Submitting level-up project...');
      // Navigate to success screen or show success message
    } catch (err: any) {
      setError('Failed to submit project. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text variant="displaySmall" style={styles.title}>
          Level Up Project
        </Text>
        <Text variant="bodyLarge" style={styles.subtitle}>
          Submit your project to advance from Level {currentLevel} to Level {nextLevel}
        </Text>
      </View>

      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Requirements
          </Text>
          <View style={styles.requirements}>
            <Chip icon="check" style={styles.requirementChip}>
              Complete all Level {currentLevel} tasks
            </Chip>
            <Chip icon="check" style={styles.requirementChip}>
              2 peer reviewers (Level {currentLevel + 2}+)
            </Chip>
            <Chip icon="check" style={styles.requirementChip}>
              AI assessment approval
            </Chip>
          </View>
        </Card.Content>
      </Card>

      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Project Details
          </Text>

          <TextInput
            label="Project Title *"
            value={projectTitle}
            onChangeText={setProjectTitle}
            mode="outlined"
            style={styles.input}
            disabled={loading}
          />

          <TextInput
            label="Project Description *"
            value={projectDescription}
            onChangeText={setProjectDescription}
            mode="outlined"
            multiline
            numberOfLines={6}
            style={styles.input}
            disabled={loading}
            placeholder="Describe your project, technologies used, challenges faced, and what you learned..."
          />

          <TextInput
            label="GitHub Repository URL *"
            value={githubUrl}
            onChangeText={setGithubUrl}
            mode="outlined"
            keyboardType="url"
            autoCapitalize="none"
            style={styles.input}
            disabled={loading}
            placeholder="https://github.com/username/project"
          />

          <TextInput
            label="Live Demo URL (Optional)"
            value={demoUrl}
            onChangeText={setDemoUrl}
            mode="outlined"
            keyboardType="url"
            autoCapitalize="none"
            style={styles.input}
            disabled={loading}
            placeholder="https://your-demo.com"
          />

          <View style={styles.attachmentSection}>
            <Text variant="bodyMedium" style={styles.attachmentLabel}>
              Additional Files (Optional)
            </Text>
            <Button
              mode="outlined"
              icon="paperclip"
              onPress={handleAttachmentPick}
              disabled={loading}
              style={styles.attachButton}>
              Add Files
            </Button>

            {attachments.length > 0 && (
              <View style={styles.attachmentList}>
                {attachments.map((file, index) => (
                  <Chip
                    key={index}
                    icon="file-document"
                    onClose={() => setAttachments(prev => prev.filter((_, i) => i !== index))}
                    style={styles.attachmentChip}>
                    {file.name}
                  </Chip>
                ))}
              </View>
            )}
          </View>

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
            💡 Your project will be reviewed by 2 senior guild members and assessed by AI. You'll receive detailed feedback within 48 hours.
          </Text>
        </Card.Content>
      </Card>

      <View style={styles.actions}>
        <Button
          mode="contained"
          onPress={handleSubmit}
          loading={loading}
          disabled={loading}
          style={styles.submitButton}>
          Submit for Review
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
    backgroundColor: theme.colors.secondary + '10',
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
  sectionTitle: {
    color: theme.colors.primary,
    marginBottom: 16,
  },
  requirements: {
    gap: 8,
  },
  requirementChip: {
    backgroundColor: theme.colors.secondary + '10',
  },
  input: {
    marginBottom: 16,
  },
  attachmentSection: {
    marginTop: 8,
  },
  attachmentLabel: {
    marginBottom: 8,
    color: theme.colors.text,
  },
  attachButton: {
    marginBottom: 12,
  },
  attachmentList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  attachmentChip: {
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
