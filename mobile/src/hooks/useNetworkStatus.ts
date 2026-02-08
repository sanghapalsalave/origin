/**
 * Hook to monitor network connectivity status
 */
import {useState, useEffect} from 'react';
import NetInfo, {NetInfoState} from '@react-native-community/netinfo';

export const useNetworkStatus = () => {
  const [isOnline, setIsOnline] = useState(true);
  const [networkType, setNetworkType] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state: NetInfoState) => {
      setIsOnline(state.isConnected ?? false);
      setNetworkType(state.type);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return {
    isOnline,
    networkType,
  };
};
