/**
 * Skill confirmation screen showing detected skill level
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Text, Button, Card, Chip, SegmentedButtons} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {theme} from '../../theme';

type SkillConfirmationScreenNavigationProp = StackNavigationProp<RootStackParamList, 'SkillConfirmation'>;
type SkillConfirmationScreenRouteProp = RouteProp<RootStackParamList, 'SkillConfirmation'>;

const SKILL_LEVELS = [
  {value: 'beginner', label: 'Beginner', description: 'Just starting out'},
  {value: 'intermediate', label: 'Intermediate', description: '1-3 years experience'},
  {value: 'advanced', label: 'Advanced', description: '3-5 years experience'},
  {value: 'expert', label: 'Expert', description: '5+ years experience'},
];

export const SkillConfirmationScreen: React.FC = () => {
  const navigation = useNavigation<SkillConfirmationScreenNavigationProp>();
  const route = useRoute<SkillConfirmationScreenRouteProp>();
  
  // Mock detected skill level - in real app, this would come from portfolio analysis
  const [skillLevel, setSkillLevel] = useState('intermediate');
  const [loading, setLoading] = useState(false);

  const handleContinue = async () => {
    setLoading(true);

    try {
      // Navigate to profile completion
      navigation.navigate('ProfileCompletion', {
        interest: route.params?.interest,
        portfolioData: route.params?.portfolioData,
        skillLevel,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <Text variant="displaySmall" style={styles.title}>
            Confirm Your Skill Level
          </Text>
          <Text variant="bodyLarge" style={styles.subtitle}>
            {route.params?.portfolioData 
              ? 'Based on your portfolio analysis, we detected your skill level'
              : 'Select your current skill level'}
          </Text>

          {route.params?.portfolioData && (
            <Card style={styles.detectionCard}>
              <Card.Content>
                <Text variant="titleMedium" style={styles.detectionTitle}>
                  Detected Skills
                </Text>
                <View style={styles.skillsContainer}>
                  <Chip icon="check" style={styles.skillChip}>React Native</Chip>
                  <Chip icon="check" style={styles.skillChip}>TypeScript</Chip>
                  <Chip icon="check" style={styles.skillChip}>Node.js</Chip>
                  <Chip icon="check" style={styles.skillChip}>REST APIs</Chip>
                </View>
              </Card.Content>
            </Card>
          )}

          <Card style={styles.card}>
            <Card.Content>
              <Text variant="titleMedium" style={styles.sectionTitle}>
                Select Your Level
              </Text>
              
              <SegmentedButtons
                value={skillLevel}
                onValueChange={setSkillLevel}
                buttons={SKILL_LEVELS.map(level => ({
                  value: level.value,
                  label: level.label,
                }))}
                style={styles.segmentedButtons}
              />

              <View style={styles.levelDescription}>
                <Text variant="bodyMedium" style={styles.descriptionText}>
                  {SKILL_LEVELS.find(l => l.value === skillLevel)?.description}
                </Text>
              </View>
            </Card.Content>
          </Card>

          <Card style={styles.infoCard}>
            <Card.Content>
              <Text variant="bodyMedium" style={styles.infoText}>
                💡 Your skill level helps us match you with compatible learners and generate appropriate curriculum
              </Text>
            </Card.Content>
          </Card>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <Button
          mode="contained"
          onPress={handleContinue}
          loading={loading}
          disabled={loading}
          style={styles.button}>
          Continue
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
  detectionCard: {
    marginBottom: 16,
    backgroundColor: theme.colors.primary + '10',
  },
  detectionTitle: {
    marginBottom: 12,
    color: theme.colors.primary,
  },
  skillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    marginRight: 8,
    marginBottom: 8,
  },
  card: {
    marginBottom: 16,
  },
  sectionTitle: {
    marginBottom: 16,
    color: theme.colors.primary,
  },
  segmentedButtons: {
    marginBottom: 16,
  },
  levelDescription: {
    padding: 12,
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
  },
  descriptionText: {
    textAlign: 'center',
    color: theme.colors.text,
  },
  infoCard: {
    backgroundColor: theme.colors.secondary + '10',
  },
  infoText: {
    color: theme.colors.text,
  },
  footer: {
    padding: 24,
    backgroundColor: theme.colors.background,
    borderTopWidth: 1,
    borderTopColor: theme.colors.surface,
  },
  button: {
    marginTop: 8,
  },
});
