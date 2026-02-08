/**
 * Responsive design utilities for mobile-first layout
 */
import {Dimensions, Platform} from 'react-native';

/**
 * Get current screen dimensions
 */
export const getScreenDimensions = () => {
  return Dimensions.get('window');
};

/**
 * Check if device is in portrait orientation
 */
export const isPortrait = () => {
  const {width, height} = getScreenDimensions();
  return height >= width;
};

/**
 * Check if device is in landscape orientation
 */
export const isLandscape = () => {
  const {width, height} = getScreenDimensions();
  return width > height;
};

/**
 * Check if screen width is below tablet breakpoint (768px)
 * Mobile-first: screens < 768px use single-column layouts
 */
export const isMobileWidth = () => {
  const {width} = getScreenDimensions();
  return width < 768;
};

/**
 * Check if screen width is tablet or larger
 */
export const isTabletWidth = () => {
  const {width} = getScreenDimensions();
  return width >= 768;
};

/**
 * Get responsive spacing based on screen size
 */
export const getResponsiveSpacing = (base: number) => {
  const {width} = getScreenDimensions();
  if (width < 768) {
    return base; // Mobile: use base spacing
  } else {
    return base * 1.5; // Tablet+: increase spacing
  }
};

/**
 * Get responsive font size based on screen size
 */
export const getResponsiveFontSize = (base: number) => {
  const {width} = getScreenDimensions();
  if (width < 768) {
    return base; // Mobile: use base size
  } else {
    return base * 1.2; // Tablet+: slightly larger
  }
};

/**
 * Platform-specific utilities
 */
export const isIOS = Platform.OS === 'ios';
export const isAndroid = Platform.OS === 'android';

/**
 * Safe area insets for notched devices
 */
export const getSafeAreaInsets = () => {
  // This will be enhanced with react-native-safe-area-context
  return {
    top: isIOS ? 44 : 0,
    bottom: isIOS ? 34 : 0,
    left: 0,
    right: 0,
  };
};
