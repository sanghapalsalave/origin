/**
 * Profile completion screen for timezone and language preferences
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Text, Button, HelperText, Menu, Divider} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../../navigation/AppNavigator';
import apiClient from '../../api/client';
import {theme} from '../../theme';

type ProfileCompletionScreenNavigationProp = StackNavigationProp<RootStackParamList, 'ProfileCompletion'>;
type ProfileCompletionScreenRouteProp = RouteProp<RootStackParamList, 'ProfileCompletion'>;

const TIMEZONES = [
  {value: 'America/New_York', label: 'Eastern Time (ET)'},
  {value: 'America/Chicago', label: 'Central Time (CT)'},
  {value: 'America/Denver', label: 'Mountain Time (MT)'},
  {value: 'America/Los_Angeles', label: 'Pacific Time (PT)'},
  {value: 'Europe/London', label: 'London (GMT)'},
  {value: 'Europe/Paris', label: 'Central European Time (CET)'},
  {value: 'Asia/Tokyo', label: 'Japan Standard Time (JST)'},
  {value: 'Asia/Shanghai', label: 'China Standard Time (CST)'},
  {value: 'Asia/Kolkata', label: 'India Standard Time (IST)'},
  {value: 'Australia/Sydney', label: 'Australian Eastern Time (AET)'},
];

const LANGUAGES = [
  {value: 'en', label: 'English'},
  {value: 'es', label: 'Spanish'},
  {value: 'fr', label: 'French'},
  {value: 'de', label: 'German'},
  {value: 'zh', label: 'Chinese'},
  {value: 'ja', label: 'Japanese'},
  {value: 'ko', label: 'Korean'},
  {value: 'pt', label: 'Portuguese'},
  {value: 'hi', label: 'Hindi'},
];

export const ProfileCompletionScreen: React.FC = () => {
  const navigation = useNavigation<ProfileCompletionScreenNavigationProp>();
  const route = useRoute<ProfileCompletionScreenRouteProp>();
  
  const [timezone, setTimezone] = useState('America/New_York');
  const [language, setLanguage] = useState('en');
  const [timezoneMenuVisible, setTimezoneMenuVisible] = useState(false);
  const [languageMenuVisible, setLanguageMenuVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleComplete = async () => {
    setError('');
    setLoading(true);

    try {
      // Submit onboarding data to API
      await apiClient.post('/onboarding/complete', {
        interest: route.params?.interest,
        portfolio_data: route.params?.portfolioData,
        skill_level: route.params?.skillLevel,
        timezone,
        language,
      });

      // Onboarding complete - navigation will be handled by AppNavigator
      // User will be redirected to Home screen automatically
    } catch (err: any) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to complete profile. Please try again');
      }
    } finally {
      setLoading(false);
    }
  };

  const selectedTimezone = TIMEZONES.find(tz => tz.value === timezone);
  const selectedLanguage = LANGUAGES.find(lang => lang.value === language);

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <Text variant="displaySmall" style={styles.title}>
            Almost Done!
          </Text>
          <Text variant="bodyLarge" style={styles.subtitle}>
            Set your timezone and language preferences
          </Text>

          <View style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Timezone
            </Text>
            <Text variant="bodyMedium" style={styles.sectionDescription}>
              We'll match you with learners in compatible timezones (±3 hours)
            </Text>
            
            <Menu
              visible={timezoneMenuVisible}
              onDismiss={() => setTimezoneMenuVisible(false)}
              anchor={
                <Button
                  mode="outlined"
                  onPress={() => setTimezoneMenuVisible(true)}
                  disabled={loading}
                  icon="clock-outline"
                  style={styles.menuButton}>
                  {selectedTimezone?.label || 'Select Timezone'}
                </Button>
              }>
              {TIMEZONES.map((tz) => (
                <Menu.Item
                  key={tz.value}
                  onPress={() => {
                    setTimezone(tz.value);
                    setTimezoneMenuVisible(false);
                  }}
                  title={tz.label}
                />
              ))}
            </Menu>
          </View>

          <View style={styles.section}>
            <Text variant="titleMedium" style={styles.sectionTitle}>
              Preferred Language
            </Text>
            <Text variant="bodyMedium" style={styles.sectionDescription}>
              Audio standups and notifications will be in your preferred language
            </Text>
            
            <Menu
              visible={languageMenuVisible}
              onDismiss={() => setLanguageMenuVisible(false)}
              anchor={
                <Button
                  mode="outlined"
                  onPress={() => setLanguageMenuVisible(true)}
                  disabled={loading}
                  icon="translate"
                  style={styles.menuButton}>
                  {selectedLanguage?.label || 'Select Language'}
                </Button>
              }>
              {LANGUAGES.map((lang) => (
                <Menu.Item
                  key={lang.value}
                  onPress={() => {
                    setLanguage(lang.value);
                    setLanguageMenuVisible(false);
                  }}
                  title={lang.label}
                />
              ))}
            </Menu>
          </View>

          {error ? (
            <HelperText type="error" visible={!!error} style={styles.error}>
              {error}
            </HelperText>
          ) : null}
        </View>
      </ScrollView>

      <View style={styles.footer}>
        <Button
          mode="contained"
          onPress={handleComplete}
          loading={loading}
          disabled={loading}
          style={styles.button}>
          Complete Profile
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
  section: {
    marginBottom: 32,
  },
  sectionTitle: {
    marginBottom: 8,
    color: theme.colors.primary,
  },
  sectionDescription: {
    marginBottom: 16,
    color: theme.colors.text,
  },
  menuButton: {
    marginTop: 8,
  },
  error: {
    marginTop: 16,
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
