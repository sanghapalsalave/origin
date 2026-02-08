/**
 * Main app navigation structure
 */
import React from 'react';
import {createStackNavigator} from '@react-navigation/stack';
import {useAuthStore} from '../stores/authStore';
import {LoginScreen, RegisterScreen, ForgotPasswordScreen} from '../screens/auth';
import {
  InterestSelectionScreen,
  PortfolioInputScreen,
  SkillConfirmationScreen,
  ProfileCompletionScreen,
} from '../screens/onboarding';
import {GuildListScreen} from '../screens/guild';
import {SquadDetailScreen} from '../screens/squad';
import {SyllabusViewScreen} from '../screens/syllabus';
import {ChatScreen} from '../screens/chat';
import {ProfileScreen, LevelUpScreen, ReviewScreen} from '../screens/profile';

// Placeholder screens - will be implemented in later tasks
const HomeScreen = () => null;

export type RootStackParamList = {
  Home: undefined;
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
  Onboarding: undefined;
  PortfolioInput: {interest: string};
  SkillConfirmation: {interest: string; portfolioData: any};
  ProfileCompletion: {interest: string; portfolioData: any; skillLevel: string};
  GuildList: undefined;
  GuildDetail: {guildId: string};
  SquadDetail: {squadId: string};
  SyllabusView: {squadId: string};
  Chat: {squadId: string};
  Profile: {userId: string};
  LevelUpScreen: undefined;
  ReviewScreen: {reviewId: string};
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
          <Stack.Screen name="Register" component={RegisterScreen} />
          <Stack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
          <Stack.Screen name="Onboarding" component={InterestSelectionScreen} />
          <Stack.Screen name="PortfolioInput" component={PortfolioInputScreen} />
          <Stack.Screen name="SkillConfirmation" component={SkillConfirmationScreen} />
          <Stack.Screen name="ProfileCompletion" component={ProfileCompletionScreen} />
        </>
      ) : (
        <>
          <Stack.Screen name="Home" component={HomeScreen} />
          <Stack.Screen name="GuildList" component={GuildListScreen} />
          <Stack.Screen name="SquadDetail" component={SquadDetailScreen} />
          <Stack.Screen name="SyllabusView" component={SyllabusViewScreen} />
          <Stack.Screen name="Chat" component={ChatScreen} />
          <Stack.Screen name="Profile" component={ProfileScreen} />
          <Stack.Screen name="LevelUpScreen" component={LevelUpScreen} />
          <Stack.Screen name="ReviewScreen" component={ReviewScreen} />
        </>
      )}
    </Stack.Navigator>
  );
};
