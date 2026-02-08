/**
 * Hook to track device orientation changes
 */
import {useState, useEffect} from 'react';
import {Dimensions, ScaledSize} from 'react-native';

type Orientation = 'portrait' | 'landscape';

export const useOrientation = (): Orientation => {
  const [orientation, setOrientation] = useState<Orientation>(() => {
    const {width, height} = Dimensions.get('window');
    return height >= width ? 'portrait' : 'landscape';
  });

  useEffect(() => {
    const handleChange = ({window}: {window: ScaledSize}) => {
      const {width, height} = window;
      setOrientation(height >= width ? 'portrait' : 'landscape');
    };

    const subscription = Dimensions.addEventListener('change', handleChange);

    return () => {
      subscription?.remove();
    };
  }, []);

  return orientation;
};
