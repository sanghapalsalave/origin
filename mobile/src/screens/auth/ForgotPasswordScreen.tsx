/**
 * Forgot password screen for password reset
 */
import React, {useState} from 'react';
import {View, StyleSheet, KeyboardAvoidingView, Platform, ScrollView} from 'react-native';
import {TextInput, Button, Text, HelperText} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../../navigation/AppNavigator';
import apiClient from '../../api/client';
import {theme} from '../../theme';

type ForgotPasswordScreenNavigationProp = StackNavigationProp<RootStackParamList, 'ForgotPassword'>;

export const ForgotPasswordScreen: React.FC = () => {
  const navigation = useNavigation<ForgotPasswordScreenNavigationProp>();
  
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const validateEmail = (email: string) => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleResetPassword = async () => {
    setError('');
    setSuccess(false);

    // Validation
    if (!email) {
      setError('Please enter your email address');
      return;
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);

    try {
      await apiClient.post('/auth/forgot-password', {
        email: email.toLowerCase().trim(),
      });

      setSuccess(true);
    } catch (err: any) {
      if (err.response?.status === 429) {
        setError('Too many reset attempts. Please try again later');
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to send reset email. Please try again');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.content}>
          <Text variant="displaySmall" style={styles.title}>
            Reset Password
          </Text>
          <Text variant="bodyLarge" style={styles.subtitle}>
            Enter your email address and we'll send you instructions to reset your password
          </Text>

          {!success ? (
            <>
              <TextInput
                label="Email"
                value={email}
                onChangeText={setEmail}
                mode="outlined"
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
                style={styles.input}
                error={!!error && !validateEmail(email) && email.length > 0}
                disabled={loading}
              />

              {error ? (
                <HelperText type="error" visible={!!error} style={styles.error}>
                  {error}
                </HelperText>
              ) : null}

              <Button
                mode="contained"
                onPress={handleResetPassword}
                loading={loading}
                disabled={loading}
                style={styles.button}>
                Send Reset Link
              </Button>
            </>
          ) : (
            <View style={styles.successContainer}>
              <Text variant="bodyLarge" style={styles.successText}>
                Password reset instructions have been sent to {email}
              </Text>
              <Text variant="bodyMedium" style={styles.successSubtext}>
                Please check your email and follow the instructions to reset your password.
              </Text>
            </View>
          )}

          <Button
            mode="text"
            onPress={() => navigation.navigate('Login')}
            disabled={loading}
            style={styles.textButton}>
            Back to Sign In
          </Button>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
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
  input: {
    marginBottom: 16,
  },
  error: {
    marginBottom: 8,
  },
  button: {
    marginTop: 8,
    marginBottom: 16,
  },
  textButton: {
    marginTop: 8,
  },
  successContainer: {
    marginBottom: 24,
    padding: 16,
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
  },
  successText: {
    color: theme.colors.primary,
    marginBottom: 12,
    textAlign: 'center',
  },
  successSubtext: {
    color: theme.colors.text,
    textAlign: 'center',
  },
});
