/**
 * Error boundary component to catch and handle React errors
 */
import React, {Component, ErrorInfo, ReactNode} from 'react';
import {View, StyleSheet} from 'react-native';
import {Text, Button} from 'react-native-paper';
import {theme} from '../theme';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to monitoring service
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // TODO: Send to error tracking service (Sentry, etc.)
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <View style={styles.container}>
          <View style={styles.content}>
            <Text variant="headlineMedium" style={styles.title}>
              Oops! Something went wrong
            </Text>
            <Text variant="bodyLarge" style={styles.message}>
              We're sorry for the inconvenience. The app encountered an unexpected error.
            </Text>
            {__DEV__ && this.state.error && (
              <View style={styles.errorDetails}>
                <Text variant="labelMedium" style={styles.errorLabel}>
                  Error Details (Dev Only):
                </Text>
                <Text variant="bodySmall" style={styles.errorText}>
                  {this.state.error.toString()}
                </Text>
              </View>
            )}
            <Button
              mode="contained"
              onPress={this.handleReset}
              style={styles.button}>
              Try Again
            </Button>
          </View>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  content: {
    maxWidth: 400,
    alignItems: 'center',
  },
  title: {
    color: theme.colors.error,
    marginBottom: 16,
    textAlign: 'center',
  },
  message: {
    color: theme.colors.text,
    marginBottom: 24,
    textAlign: 'center',
  },
  errorDetails: {
    width: '100%',
    padding: 16,
    backgroundColor: theme.colors.error + '10',
    borderRadius: 8,
    marginBottom: 24,
  },
  errorLabel: {
    color: theme.colors.error,
    marginBottom: 8,
  },
  errorText: {
    color: theme.colors.text,
    fontFamily: 'monospace',
  },
  button: {
    minWidth: 200,
  },
});
