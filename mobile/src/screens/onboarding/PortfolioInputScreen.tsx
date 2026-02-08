/**
 * Portfolio input screen with multiple input options
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Text, Button, TextInput, Card, IconButton, HelperText} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import DocumentPicker from 'react-native-document-picker';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {theme} from '../../theme';

type PortfolioInputScreenNavigationProp = StackNavigationProp<RootStackParamList, 'PortfolioInput'>;
type PortfolioInputScreenRouteProp = RouteProp<RootStackParamList, 'PortfolioInput'>;

export const PortfolioInputScreen: React.FC = () => {
  const navigation = useNavigation<PortfolioInputScreenNavigationProp>();
  const route = useRoute<PortfolioInputScreenRouteProp>();
  
  const [githubUrl, setGithubUrl] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [portfolioUrl, setPortfolioUrl] = useState('');
  const [resumeFile, setResumeFile] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePickResume = async () => {
    try {
      const result = await DocumentPicker.pick({
        type: [DocumentPicker.types.pdf, DocumentPicker.types.doc, DocumentPicker.types.docx],
      });
      setResumeFile(result[0]);
      setError('');
    } catch (err) {
      if (!DocumentPicker.isCancel(err)) {
        setError('Failed to pick resume file');
      }
    }
  };

  const handleContinue = async () => {
    setError('');

    // Validate at least one input method
    if (!githubUrl && !linkedinUrl && !portfolioUrl && !resumeFile) {
      setError('Please provide at least one portfolio input method');
      return;
    }

    setLoading(true);

    try {
      // TODO: Call portfolio analysis API
      // For now, navigate to skill confirmation
      navigation.navigate('SkillConfirmation', {
        interest: route.params?.interest,
        portfolioData: {
          githubUrl,
          linkedinUrl,
          portfolioUrl,
          resumeFile: resumeFile?.name,
        },
      });
    } catch (err: any) {
      setError('Failed to analyze portfolio. Please try again');
    } finally {
      setLoading(false);
    }
  };

  const handleSkip = () => {
    // Navigate to manual entry
    navigation.navigate('SkillConfirmation', {
      interest: route.params?.interest,
      portfolioData: null,
    });
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <Text variant="displaySmall" style={styles.title}>
            Tell us about yourself
          </Text>
          <Text variant="bodyLarge" style={styles.subtitle}>
            Connect your portfolio to help us assess your skill level
          </Text>

          <Card style={styles.card}>
            <Card.Content>
              <View style={styles.inputSection}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  GitHub Profile
                </Text>
                <TextInput
                  label="GitHub URL"
                  value={githubUrl}
                  onChangeText={setGithubUrl}
                  mode="outlined"
                  placeholder="https://github.com/username"
                  autoCapitalize="none"
                  keyboardType="url"
                  style={styles.input}
                  disabled={loading}
                  left={<TextInput.Icon icon="github" />}
                />
              </View>

              <View style={styles.inputSection}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  LinkedIn Profile
                </Text>
                <TextInput
                  label="LinkedIn URL"
                  value={linkedinUrl}
                  onChangeText={setLinkedinUrl}
                  mode="outlined"
                  placeholder="https://linkedin.com/in/username"
                  autoCapitalize="none"
                  keyboardType="url"
                  style={styles.input}
                  disabled={loading}
                  left={<TextInput.Icon icon="linkedin" />}
                />
              </View>

              <View style={styles.inputSection}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  Portfolio Website
                </Text>
                <TextInput
                  label="Portfolio URL"
                  value={portfolioUrl}
                  onChangeText={setPortfolioUrl}
                  mode="outlined"
                  placeholder="https://yourportfolio.com"
                  autoCapitalize="none"
                  keyboardType="url"
                  style={styles.input}
                  disabled={loading}
                  left={<TextInput.Icon icon="web" />}
                />
              </View>

              <View style={styles.inputSection}>
                <Text variant="titleMedium" style={styles.sectionTitle}>
                  Resume Upload
                </Text>
                <Button
                  mode="outlined"
                  onPress={handlePickResume}
                  disabled={loading}
                  icon="file-document"
                  style={styles.uploadButton}>
                  {resumeFile ? resumeFile.name : 'Upload Resume (PDF, DOC, DOCX)'}
                </Button>
                {resumeFile && (
                  <HelperText type="info">
                    Selected: {resumeFile.name}
                  </HelperText>
                )}
              </View>
            </Card.Content>
          </Card>

          {error ? (
            <HelperText type="error" visible={!!error} style={styles.error}>
              {error}
            </HelperText>
          ) : null}
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <Button
          mode="text"
          onPress={handleSkip}
          disabled={loading}
          style={styles.skipButton}>
          Skip - Enter Manually
        </Button>
        <Button
          mode="contained"
          onPress={handleContinue}
          loading={loading}
          disabled={loading}
          style={styles.button}>
          Analyze Portfolio
        </Button>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    padding: 24,
  },
  title: {
    color: theme.colors.primary,
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    color: theme.colors.text,
    marginBottom: 24,
    textAlign: 'center',
  },
  card: {
    marginBottom: 16,
  },
  inputSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    marginBottom: 8,
    color: theme.colors.primary,
  },
  input: {
    marginBottom: 8,
  },
  uploadButton: {
    marginTop: 8,
  },
  error: {
    marginTop: 8,
  },
  footer: {
    padding: 24,
    backgroundColor: theme.colors.background,
    borderTopWidth: 1,
    borderTopColor: theme.colors.surface,
  },
  skipButton: {
    marginBottom: 8,
  },
  button: {
    marginTop: 8,
  },
});
