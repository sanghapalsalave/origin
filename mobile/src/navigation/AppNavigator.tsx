/**
 * Main app navigation structure
 */
import React from 'react';
import {createStackNavigator} from '@react-navigation/stack';
import {useAuthStore} from '../stores/authStore';

// Placeholder screens - will be implemented in later tasks
const HomeScreen = () => null;
const LoginScreen = () => null;
const OnboardingScreen = () => null;

export type RootStackParamList = {
  Home: undefined;
  Login: undefined;
  Onboarding: undefined;
  // Add more routes as needed
};

const Stack = createStackNavigator<RootStackParamList>();

export const AppNavigator: React.FC = () => {
  const {isAuthenticated} = useAuthStore();

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
      }}>
      {!isAuthenticated ? (
        <>
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Onboarding" component={OnboardingScreen} />
        </>
      ) : (
        <Stack.Screen name="Home" component={HomeScreen} />
      )}
    </Stack.Navigator>
  );
};
