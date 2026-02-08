/**
 * ORIGIN brand theme configuration
 * Colors: Deep royal purple (#4B0082) primary, vibrant saffron (#FF9933) for level-ups
 * Font: Montserrat
 * 
 * Mobile-first responsive design:
 * - Single-column layouts for screens < 768px
 * - Support for portrait and landscape orientations
 * - Consistent brand colors and typography
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
  // Responsive breakpoints
  breakpoints: {
    mobile: 768, // Screens < 768px use single-column layouts
  },
  // Spacing scale
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
};

export type AppTheme = typeof theme;

// Brand colors for direct use
export const brandColors = {
  purple: '#4B0082',
  saffron: '#FF9933',
  white: '#FFFFFF',
  black: '#000000',
  surface: '#F5F5F5',
  error: '#B00020',
};

// Typography scale
export const typography = {
  displayLarge: {
    fontFamily: 'Montserrat-Bold',
    fontSize: 57,
    lineHeight: 64,
  },
  displayMedium: {
    fontFamily: 'Montserrat-Bold',
    fontSize: 45,
    lineHeight: 52,
  },
  displaySmall: {
    fontFamily: 'Montserrat-Bold',
    fontSize: 36,
    lineHeight: 44,
  },
  headlineLarge: {
    fontFamily: 'Montserrat-Bold',
    fontSize: 32,
    lineHeight: 40,
  },
  headlineMedium: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 28,
    lineHeight: 36,
  },
  headlineSmall: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 24,
    lineHeight: 32,
  },
  titleLarge: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 22,
    lineHeight: 28,
  },
  titleMedium: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 16,
    lineHeight: 24,
  },
  titleSmall: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 14,
    lineHeight: 20,
  },
  bodyLarge: {
    fontFamily: 'Montserrat-Regular',
    fontSize: 16,
    lineHeight: 24,
  },
  bodyMedium: {
    fontFamily: 'Montserrat-Regular',
    fontSize: 14,
    lineHeight: 20,
  },
  bodySmall: {
    fontFamily: 'Montserrat-Regular',
    fontSize: 12,
    lineHeight: 16,
  },
  labelLarge: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 14,
    lineHeight: 20,
  },
  labelMedium: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 12,
    lineHeight: 16,
  },
  labelSmall: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 11,
    lineHeight: 16,
  },
};

