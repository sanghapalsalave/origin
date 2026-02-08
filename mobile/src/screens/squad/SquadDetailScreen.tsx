/**
 * Squad detail screen with member list
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView, FlatList} from 'react-native';
import {Text, Avatar, Card, Button, Chip, Divider} from 'react-native-paper';
import {useNavigation, useRoute, RouteProp} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {ProfileSkeleton} from '../../components/skeletons';
import {TouchableCard} from '../../components/touchable';
import {theme} from '../../theme';

type SquadDetailScreenNavigationProp = StackNavigationProp<RootStackParamList, 'SquadDetail'>;
type SquadDetailScreenRouteProp = RouteProp<RootStackParamList, 'SquadDetail'>;

interface SquadMember {
  id: string;
  name: string;
  avatar_url?: string;
  level: number;
  reputation_points: number;
  is_facilitator: boolean;
}

interface Squad {
  id: string;
  name: string;
  guild_name: string;
  created_at: string;
  member_count: number;
  is_active: boolean;
  members: SquadMember[];
}

// Mock data
const MOCK_SQUAD: Squad = {
  id: '1',
  name: 'Squad Alpha',
  guild_name: 'Web Development Masters',
  created_at: '2024-01-15',
  member_count: 13,
  is_active: true,
  members: [
    {
      id: '1',
      name: 'Alice Johnson',
      level: 5,
      reputation_points: 1250,
      is_facilitator: true,
    },
    {
      id: '2',
      name: 'Bob Smith',
      level: 4,
      reputation_points: 890,
      is_facilitator: false,
    },
    {
      id: '3',
      name: 'Carol Davis',
      level: 4,
      reputation_points: 920,
      is_facilitator: false,
    },
  ],
};

export const SquadDetailScreen: React.FC = () => {
  const navigation = useNavigation<SquadDetailScreenNavigationProp>();
  const route = useRoute<SquadDetailScreenRouteProp>();
  const [loading, setLoading] = useState(false);
  const [squad, setSquad] = useState<Squad>(MOCK_SQUAD);

  const handleViewSyllabus = () => {
    navigation.navigate('SyllabusView', {squadId: squad.id});
  };

  const handleOpenChat = () => {
    navigation.navigate('Chat', {squadId: squad.id});
  };

  const handleMemberPress = (member: SquadMember) => {
    navigation.navigate('Profile', {userId: member.id});
  };

  if (loading) {
    return <ProfileSkeleton />;
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text variant="headlineMedium" style={styles.squadName}>
          {squad.name}
        </Text>
        <Text variant="bodyMedium" style={styles.guildName}>
          {squad.guild_name}
        </Text>
        
        <View style={styles.statusContainer}>
          <Chip
            icon={squad.is_active ? 'check-circle' : 'clock'}
            style={[styles.statusChip, squad.is_active && styles.activeChip]}>
            {squad.is_active ? 'Active' : 'Forming'}
          </Chip>
          <Text variant="bodySmall" style={styles.memberCountText}>
            {squad.member_count}/15 members
          </Text>
        </View>
      </View>

      <View style={styles.actionsContainer}>
        <Button
          mode="contained"
          onPress={handleViewSyllabus}
          icon="book-open-variant"
          style={styles.actionButton}>
          View Syllabus
        </Button>
        <Button
          mode="outlined"
          onPress={handleOpenChat}
          icon="chat"
          style={styles.actionButton}>
          Open Chat
        </Button>
      </View>

      <Divider style={styles.divider} />

      <View style={styles.section}>
        <Text variant="titleLarge" style={styles.sectionTitle}>
          Squad Members ({squad.members.length})
        </Text>
        
        <FlatList
          data={squad.members}
          keyExtractor={(item) => item.id}
          scrollEnabled={false}
          renderItem={({item}) => (
            <TouchableCard onPress={() => handleMemberPress(item)} style={styles.memberCard}>
              <Card>
                <Card.Content>
                  <View style={styles.memberRow}>
                    <Avatar.Text
                      size={48}
                      label={item.name.split(' ').map(n => n[0]).join('')}
                      style={styles.avatar}
                    />
                    
                    <View style={styles.memberInfo}>
                      <View style={styles.memberHeader}>
                        <Text variant="titleMedium" style={styles.memberName}>
                          {item.name}
                        </Text>
                        {item.is_facilitator && (
                          <Chip
                            icon="star"
                            style={styles.facilitatorBadge}
                            textStyle={styles.facilitatorText}>
                            Facilitator
                          </Chip>
                        )}
                      </View>
                      
                      <View style={styles.memberStats}>
                        <View style={styles.stat}>
                          <Text variant="bodySmall" style={styles.statLabel}>
                            Level
                          </Text>
                          <Text variant="bodyMedium" style={styles.statValue}>
                            {item.level}
                          </Text>
                        </View>
                        <View style={styles.stat}>
                          <Text variant="bodySmall" style={styles.statLabel}>
                            Reputation
                          </Text>
                          <Text variant="bodyMedium" style={styles.statValue}>
                            {item.reputation_points}
                          </Text>
                        </View>
                      </View>
                    </View>
                  </View>
                </Card.Content>
              </Card>
            </TouchableCard>
          )}
        />
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    padding: 16,
    backgroundColor: theme.colors.primary + '10',
  },
  squadName: {
    color: theme.colors.primary,
    marginBottom: 4,
  },
  guildName: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 12,
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  statusChip: {
    backgroundColor: theme.colors.surface,
  },
  activeChip: {
    backgroundColor: theme.colors.secondary + '20',
  },
  memberCountText: {
    color: theme.colors.text,
  },
  actionsContainer: {
    padding: 16,
    gap: 12,
  },
  actionButton: {
    marginBottom: 8,
  },
  divider: {
    marginVertical: 8,
  },
  section: {
    padding: 16,
  },
  sectionTitle: {
    color: theme.colors.primary,
    marginBottom: 16,
  },
  memberCard: {
    marginBottom: 12,
  },
  memberRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  avatar: {
    backgroundColor: theme.colors.primary,
  },
  memberInfo: {
    flex: 1,
    marginLeft: 12,
  },
  memberHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  memberName: {
    flex: 1,
    color: theme.colors.text,
  },
  facilitatorBadge: {
    backgroundColor: theme.colors.secondary + '20',
    height: 24,
  },
  facilitatorText: {
    color: theme.colors.secondary,
    fontSize: 10,
  },
  memberStats: {
    flexDirection: 'row',
    gap: 24,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statLabel: {
    color: theme.colors.text,
    opacity: 0.6,
  },
  statValue: {
    color: theme.colors.primary,
    fontWeight: '600',
  },
});
