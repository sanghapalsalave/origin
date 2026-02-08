/**
 * Interest selection screen for onboarding
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView, FlatList} from 'react-native';
import {Text, Button, Chip, Surface} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {theme} from '../../theme';

type InterestSelectionScreenNavigationProp = StackNavigationProp<RootStackParamList, 'Onboarding'>;

// Common interest areas for guilds
const INTEREST_AREAS = [
  {id: 'web-development', label: 'Web Development', icon: 'web'},
  {id: 'mobile-development', label: 'Mobile Development', icon: 'cellphone'},
  {id: 'data-science', label: 'Data Science', icon: 'chart-line'},
  {id: 'machine-learning', label: 'Machine Learning', icon: 'brain'},
  {id: 'devops', label: 'DevOps', icon: 'cloud'},
  {id: 'cybersecurity', label: 'Cybersecurity', icon: 'shield-lock'},
  {id: 'game-development', label: 'Game Development', icon: 'gamepad-variant'},
  {id: 'ui-ux-design', label: 'UI/UX Design', icon: 'palette'},
  {id: 'blockchain', label: 'Blockchain', icon: 'link-variant'},
  {id: 'cloud-architecture', label: 'Cloud Architecture', icon: 'server'},
];

export const InterestSelectionScreen: React.FC = () => {
  const navigation = useNavigation<InterestSelectionScreenNavigationProp>();
  const [selectedInterest, setSelectedInterest] = useState<string | null>(null);

  const handleContinue = () => {
    if (selectedInterest) {
      // Navigate to portfolio input with selected interest
      navigation.navigate('PortfolioInput', {interest: selectedInterest});
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <Text variant="displaySmall" style={styles.title}>
            What do you want to learn?
          </Text>
          <Text variant="bodyLarge" style={styles.subtitle}>
            Choose your primary interest area to get matched with the right guild
          </Text>

          <View style={styles.interestsContainer}>
            {INTEREST_AREAS.map((interest) => (
              <Surface
                key={interest.id}
                style={[
                  styles.interestCard,
                  selectedInterest === interest.id && styles.interestCardSelected,
                ]}
                elevation={selectedInterest === interest.id ? 4 : 1}>
                <Chip
                  selected={selectedInterest === interest.id}
                  onPress={() => setSelectedInterest(interest.id)}
                  style={styles.chip}
                  textStyle={styles.chipText}>
                  {interest.label}
                </Chip>
              </Surface>
            ))}
          </View>
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <Button
          mode="contained"
          onPress={handleContinue}
          disabled={!selectedInterest}
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
    marginBottom: 32,
    textAlign: 'center',
  },
  interestsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 12,
  },
  interestCard: {
    borderRadius: 8,
    marginBottom: 8,
  },
  interestCardSelected: {
    backgroundColor: theme.colors.primary + '10',
  },
  chip: {
    margin: 4,
  },
  chipText: {
    fontSize: 14,
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
