/**
 * Hook to track screen dimension changes
 */
import {useState, useEffect} from 'react';
import {Dimensions, ScaledSize} from 'react-native';

interface ScreenDimensions {
  width: number;
  height: number;
  isMobile: boolean;
  isTablet: boolean;
}

export const useDimensions = (): ScreenDimensions => {
  const [dimensions, setDimensions] = useState<ScreenDimensions>(() => {
    const {width, height} = Dimensions.get('window');
    return {
      width,
      height,
      isMobile: width < 768,
      isTablet: width >= 768,
    };
  });

  useEffect(() => {
    const handleChange = ({window}: {window: ScaledSize}) => {
      const {width, height} = window;
      setDimensions({
        width,
        height,
        isMobile: width < 768,
        isTablet: width >= 768,
      });
    };

    const subscription = Dimensions.addEventListener('change', handleChange);

    return () => {
      subscription?.remove();
    };
  }, []);

  return dimensions;
};
