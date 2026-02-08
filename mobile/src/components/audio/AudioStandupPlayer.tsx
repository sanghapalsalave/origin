/**
 * Audio standup player component with playback tracking
 */
import React, {useState, useEffect, useRef} from 'react';
import {View, StyleSheet} from 'react-native';
import {Text, IconButton, ProgressBar, Card} from 'react-native-paper';
import Sound from 'react-native-sound';
import {theme} from '../../theme';

interface AudioStandupPlayerProps {
  audioUrl: string;
  title: string;
  date: string;
  onPlaybackComplete?: () => void;
}

export const AudioStandupPlayer: React.FC<AudioStandupPlayerProps> = ({
  audioUrl,
  title,
  date,
  onPlaybackComplete,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const soundRef = useRef<Sound | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Initialize sound
    Sound.setCategory('Playback');

    return () => {
      // Cleanup
      if (soundRef.current) {
        soundRef.current.release();
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  const loadAudio = () => {
    if (soundRef.current) {
      return;
    }

    setIsLoading(true);

    soundRef.current = new Sound(audioUrl, '', (error) => {
      setIsLoading(false);

      if (error) {
        console.error('Failed to load audio:', error);
        return;
      }

      if (soundRef.current) {
        setDuration(soundRef.current.getDuration());
      }
    });
  };

  const handlePlayPause = () => {
    if (!soundRef.current) {
      loadAudio();
      return;
    }

    if (isPlaying) {
      // Pause
      soundRef.current.pause();
      setIsPlaying(false);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    } else {
      // Play
      soundRef.current.play((success) => {
        if (success) {
          console.log('Playback completed');
          setIsPlaying(false);
          setCurrentTime(0);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
          }
          // Track completion
          if (onPlaybackComplete) {
            onPlaybackComplete();
          }
        }
      });

      setIsPlaying(true);

      // Update progress
      intervalRef.current = setInterval(() => {
        if (soundRef.current) {
          soundRef.current.getCurrentTime((seconds) => {
            setCurrentTime(seconds);
          });
        }
      }, 100);
    }
  };

  const handleSeek = (position: number) => {
    if (soundRef.current) {
      const seekTime = position * duration;
      soundRef.current.setCurrentTime(seekTime);
      setCurrentTime(seekTime);
    }
  };

  const handleSpeedChange = () => {
    const speeds = [1.0, 1.25, 1.5, 2.0];
    const currentIndex = speeds.indexOf(playbackSpeed);
    const nextSpeed = speeds[(currentIndex + 1) % speeds.length];
    setPlaybackSpeed(nextSpeed);

    if (soundRef.current) {
      soundRef.current.setSpeed(nextSpeed);
    }
  };

  const handleRewind = () => {
    if (soundRef.current) {
      const newTime = Math.max(0, currentTime - 10);
      soundRef.current.setCurrentTime(newTime);
      setCurrentTime(newTime);
    }
  };

  const handleForward = () => {
    if (soundRef.current) {
      const newTime = Math.min(duration, currentTime + 10);
      soundRef.current.setCurrentTime(newTime);
      setCurrentTime(newTime);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = duration > 0 ? currentTime / duration : 0;

  return (
    <Card style={styles.container}>
      <Card.Content>
        <View style={styles.header}>
          <View style={styles.titleContainer}>
            <Text variant="titleMedium" style={styles.title}>
              {title}
            </Text>
            <Text variant="bodySmall" style={styles.date}>
              {new Date(date).toLocaleDateString()}
            </Text>
          </View>
          <IconButton
            icon="information"
            size={20}
            onPress={() => console.log('Show standup details')}
          />
        </View>

        <View style={styles.progressContainer}>
          <Text variant="bodySmall" style={styles.timeText}>
            {formatTime(currentTime)}
          </Text>
          <ProgressBar
            progress={progress}
            color={theme.colors.secondary}
            style={styles.progressBar}
          />
          <Text variant="bodySmall" style={styles.timeText}>
            {formatTime(duration)}
          </Text>
        </View>

        <View style={styles.controls}>
          <IconButton
            icon="rewind-10"
            size={28}
            onPress={handleRewind}
            disabled={!soundRef.current || isLoading}
          />

          <IconButton
            icon={isPlaying ? 'pause-circle' : 'play-circle'}
            size={56}
            onPress={handlePlayPause}
            disabled={isLoading}
            iconColor={theme.colors.primary}
          />

          <IconButton
            icon="fast-forward-10"
            size={28}
            onPress={handleForward}
            disabled={!soundRef.current || isLoading}
          />
        </View>

        <View style={styles.footer}>
          <IconButton
            icon="speedometer"
            size={20}
            onPress={handleSpeedChange}
            disabled={!soundRef.current || isLoading}
          />
          <Text variant="bodySmall" style={styles.speedText}>
            {playbackSpeed}x
          </Text>
        </View>
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  titleContainer: {
    flex: 1,
  },
  title: {
    color: theme.colors.primary,
    marginBottom: 4,
  },
  date: {
    color: theme.colors.text,
    opacity: 0.6,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  progressBar: {
    flex: 1,
    height: 4,
    marginHorizontal: 12,
    borderRadius: 2,
  },
  timeText: {
    color: theme.colors.text,
    opacity: 0.7,
    minWidth: 40,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  speedText: {
    color: theme.colors.text,
    marginLeft: -8,
  },
});
