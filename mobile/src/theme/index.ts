/**
 * ORIGIN brand theme configuration
 * Colors: Deep royal purple (#4B0082) primary, vibrant saffron (#FF9933) for level-ups
 * Font: Montserrat
 */
import {MD3LightTheme as DefaultTheme} from 'react-native-paper';

export const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#4B0082', // Deep royal purple
    secondary: '#FF9933', // Vibrant saffron
    accent: '#FF9933',
    background: '#FFFFFF',
    surface: '#F5F5F5',
    text: '#000000',
    error: '#B00020',
    onPrimary: '#FFFFFF',
    onSecondary: '#FFFFFF',
  },
  fonts: {
    ...DefaultTheme.fonts,
    regular: {
      fontFamily: 'Montserrat-Regular',
      fontWeight: '400' as const,
    },
    medium: {
      fontFamily: 'Montserrat-Medium',
      fontWeight: '500' as const,
    },
    bold: {
      fontFamily: 'Montserrat-Bold',
      fontWeight: '700' as const,
    },
  },
};

export type AppTheme = typeof theme;
