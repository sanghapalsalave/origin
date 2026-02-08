/**
 * Networking screen displaying 1-on-1 pairings for week-one completion
 */
import React, {useState, useEffect} from 'react';
import {View, StyleSheet, FlatList, RefreshControl} from 'react-native';
import {Text, Card, Button, Avatar, Chip, ActivityIndicator} from 'react-native-paper';
import {theme} from '../../theme';

interface NetworkingPairing {
  id: string;
  partner_id: string;
  partner_name: string;
  partner_avatar?: string;
  partner_level: number;
  partner_skills: string[];
  scheduled_for: string;
  status: 'pending' | 'scheduled' | 'completed';
  meeting_link?: string;
}

// Mock data
const MOCK_PAIRINGS: NetworkingPairing[] = [
  {
    id: '1',
    partner_id: 'user123',
    partner_name: 'Alice Johnson',
    partner_level: 3,
    partner_skills: ['React', 'TypeScript', 'Node.js'],
    scheduled_for: '2024-02-10T14:00:00Z',
    status: 'scheduled',
    meeting_link: 'https://meet.example.com/abc123',
  },
  {
    id: '2',
    partner_id: 'user456',
    partner_name: 'Bob Smith',
    partner_level: 5,
    partner_skills: ['Python', 'Django', 'PostgreSQL'],
    scheduled_for: '2024-02-12T16:00:00Z',
    status: 'pending',
  },
];

export const NetworkingScreen: React.FC = () => {
  const [pairings, setPairings] = useState<NetworkingPairing[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadPairings();
  }, []);

  const loadPairings = async () => {
    try {
      // TODO: Replace with actual API call
      // const response = await api.get('/networking/pairings');
      // setPairings(response.data);
      
      // Simulate API call
      setTimeout(() => {
        setPairings(MOCK_PAIRINGS);
        setLoading(false);
        setRefreshing(false);
      }, 1000);
    } catch (error) {
      console.error('Failed to load pairings:', error);
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadPairings();
  };

  const handleScheduleMeeting = (pairingId: string) => {
    // TODO: Navigate to scheduling screen or open calendar
    console.log('Schedule meeting for pairing:', pairingId);
  };

  const handleJoinMeeting = (meetingLink: string) => {
    // TODO: Open meeting link in browser or app
    console.log('Join meeting:', meetingLink);
  };

  const handleMarkComplete = (pairingId: string) => {
    // TODO: Call API to mark pairing as completed
    setPairings(prev =>
      prev.map(p =>
        p.id === pairingId ? {...p, status: 'completed'} : p
      )
    );
  };

  const getStatusColor = (status: NetworkingPairing['status']) => {
    switch (status) {
      case 'completed':
        return theme.colors.secondary;
      case 'scheduled':
        return theme.colors.primary;
      case 'pending':
        return theme.colors.text + '60';
      default:
        return theme.colors.text;
    }
  };

  const getStatusLabel = (status: NetworkingPairing['status']) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'scheduled':
        return 'Scheduled';
      case 'pending':
        return 'Pending';
      default:
        return status;
    }
  };

  const formatDateTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    
    const timeStr = date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
    
    if (diffDays === 0) {
      return `Today at ${timeStr}`;
    } else if (diffDays === 1) {
      return `Tomorrow at ${timeStr}`;
    } else if (diffDays > 1 && diffDays < 7) {
      return `${date.toLocaleDateString('en-US', {weekday: 'long'})} at ${timeStr}`;
    } else {
      return `${date.toLocaleDateString('en-US', {month: 'short', day: 'numeric'})} at ${timeStr}`;
    }
  };

  const renderPairing = ({item}: {item: NetworkingPairing}) => {
    return (
      <Card style={styles.card}>
        <Card.Content>
          <View style={styles.header}>
            <Avatar.Text
              size={56}
              label={item.partner_name.split(' ').map(n => n[0]).join('')}
              style={styles.avatar}
            />
            <View style={styles.headerInfo}>
              <Text variant="titleLarge" style={styles.partnerName}>
                {item.partner_name}
              </Text>
              <Text variant="bodyMedium" style={styles.levelText}>
                Level {item.partner_level}
              </Text>
            </View>
            <Chip
              style={[styles.statusChip, {backgroundColor: getStatusColor(item.status) + '20'}]}
              textStyle={[styles.statusText, {color: getStatusColor(item.status)}]}>
              {getStatusLabel(item.status)}
            </Chip>
          </View>

          <View style={styles.skillsContainer}>
            <Text variant="labelMedium" style={styles.skillsLabel}>
              Skills:
            </Text>
            <View style={styles.skillsRow}>
              {item.partner_skills.map((skill, index) => (
                <Chip key={index} style={styles.skillChip} textStyle={styles.skillText}>
                  {skill}
                </Chip>
              ))}
            </View>
          </View>

          {item.status !== 'completed' && (
            <View style={styles.scheduleInfo}>
              <Text variant="bodyMedium" style={styles.scheduleLabel}>
                {item.status === 'scheduled' ? 'Scheduled for:' : 'Suggested time:'}
              </Text>
              <Text variant="bodyLarge" style={styles.scheduleTime}>
                {formatDateTime(item.scheduled_for)}
              </Text>
            </View>
          )}

          <View style={styles.actions}>
            {item.status === 'pending' && (
              <Button
                mode="contained"
                onPress={() => handleScheduleMeeting(item.id)}
                style={styles.actionButton}>
                Schedule Meeting
              </Button>
            )}
            {item.status === 'scheduled' && (
              <>
                <Button
                  mode="contained"
                  onPress={() => handleJoinMeeting(item.meeting_link!)}
                  style={[styles.actionButton, styles.primaryButton]}>
                  Join Meeting
                </Button>
                <Button
                  mode="outlined"
                  onPress={() => handleMarkComplete(item.id)}
                  style={styles.actionButton}>
                  Mark Complete
                </Button>
              </>
            )}
            {item.status === 'completed' && (
              <View style={styles.completedBadge}>
                <Text variant="bodyMedium" style={styles.completedText}>
                  ✓ Meeting completed
                </Text>
              </View>
            )}
          </View>
        </Card.Content>
      </Card>
    );
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color={theme.colors.primary} />
        <Text variant="bodyLarge" style={styles.loadingText}>
          Loading pairings...
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerSection}>
        <Text variant="displaySmall" style={styles.title}>
          1-on-1 Networking
        </Text>
        <Text variant="bodyLarge" style={styles.subtitle}>
          Connect with your squad members this week
        </Text>
      </View>

      <FlatList
        data={pairings}
        keyExtractor={item => item.id}
        renderItem={renderPairing}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            colors={[theme.colors.primary]}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text variant="headlineSmall" style={styles.emptyTitle}>
              No pairings yet
            </Text>
            <Text variant="bodyLarge" style={styles.emptySubtext}>
              Pairings will be created after your squad completes week one
            </Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background,
  },
  loadingText: {
    marginTop: 16,
    color: theme.colors.text,
  },
  headerSection: {
    padding: 24,
    backgroundColor: theme.colors.primary + '10',
  },
  title: {
    color: theme.colors.primary,
    marginBottom: 8,
  },
  subtitle: {
    color: theme.colors.text,
  },
  listContent: {
    padding: 16,
  },
  card: {
    marginBottom: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatar: {
    backgroundColor: theme.colors.primary,
  },
  headerInfo: {
    flex: 1,
    marginLeft: 16,
  },
  partnerName: {
    color: theme.colors.text,
    marginBottom: 4,
  },
  levelText: {
    color: theme.colors.text,
    opacity: 0.7,
  },
  statusChip: {
    height: 28,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  skillsContainer: {
    marginBottom: 16,
  },
  skillsLabel: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 8,
  },
  skillsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    backgroundColor: theme.colors.secondary + '15',
    height: 28,
  },
  skillText: {
    color: theme.colors.secondary,
    fontSize: 12,
  },
  scheduleInfo: {
    marginBottom: 16,
    padding: 12,
    backgroundColor: theme.colors.primary + '08',
    borderRadius: 8,
  },
  scheduleLabel: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 4,
  },
  scheduleTime: {
    color: theme.colors.primary,
    fontWeight: '600',
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
    flexWrap: 'wrap',
  },
  actionButton: {
    flex: 1,
    minWidth: 140,
  },
  primaryButton: {
    backgroundColor: theme.colors.primary,
  },
  completedBadge: {
    flex: 1,
    padding: 12,
    backgroundColor: theme.colors.secondary + '15',
    borderRadius: 8,
    alignItems: 'center',
  },
  completedText: {
    color: theme.colors.secondary,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    paddingHorizontal: 32,
  },
  emptyTitle: {
    color: theme.colors.text,
    marginBottom: 12,
  },
  emptySubtext: {
    color: theme.colors.text,
    opacity: 0.6,
    textAlign: 'center',
  },
});
