/**
 * User profile screen with reputation display
 */
import React, {useState} from 'react';
import {View, StyleSheet, ScrollView} from 'react-native';
import {Text, Avatar, Card, Chip, ProgressBar, Divider, Button} from 'react-native-paper';
import {useRoute, RouteProp} from '@react-navigation/native';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {ProfileSkeleton} from '../../components/skeletons';
import {theme} from '../../theme';

type ProfileScreenRouteProp = RouteProp<RootStackParamList, 'Profile'>;

interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatar_url?: string;
  level: number;
  reputation_points: number;
  total_reviews_given: number;
  total_reviews_received: number;
  current_squad?: string;
  current_guild?: string;
  skills: string[];
  certificates: Certificate[];
  is_premium: boolean;
}

interface Certificate {
  id: string;
  name: string;
  issued_date: string;
  guild_name: string;
  is_premium: boolean;
}

// Mock data
const MOCK_PROFILE: UserProfile = {
  id: '1',
  name: 'John Doe',
  email: 'john.doe@example.com',
  level: 5,
  reputation_points: 1250,
  total_reviews_given: 15,
  total_reviews_received: 12,
  current_squad: 'Squad Alpha',
  current_guild: 'Web Development Masters',
  skills: ['React Native', 'TypeScript', 'Node.js', 'REST APIs', 'Git'],
  certificates: [
    {
      id: '1',
      name: 'React Native Fundamentals',
      issued_date: '2024-01-15',
      guild_name: 'Mobile Dev Pro',
      is_premium: true,
    },
    {
      id: '2',
      name: 'TypeScript Advanced',
      issued_date: '2023-12-10',
      guild_name: 'Web Development Masters',
      is_premium: false,
    },
  ],
  is_premium: true,
};

export const ProfileScreen: React.FC = () => {
  const route = useRoute<ProfileScreenRouteProp>();
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<UserProfile>(MOCK_PROFILE);

  // Calculate progress to next level (assuming 300 points per level)
  const pointsPerLevel = 300;
  const currentLevelPoints = profile.reputation_points % pointsPerLevel;
  const progressToNextLevel = currentLevelPoints / pointsPerLevel;

  if (loading) {
    return <ProfileSkeleton />;
  }

  return (
    <ScrollView style={styles.container}>
      {/* Header Section */}
      <View style={styles.header}>
        <Avatar.Text
          size={80}
          label={profile.name.split(' ').map(n => n[0]).join('')}
          style={styles.avatar}
        />
        <Text variant="headlineMedium" style={styles.name}>
          {profile.name}
        </Text>
        <Text variant="bodyMedium" style={styles.email}>
          {profile.email}
        </Text>

        {profile.is_premium && (
          <Chip icon="crown" style={styles.premiumBadge} textStyle={styles.premiumText}>
            Premium Member
          </Chip>
        )}
      </View>

      {/* Level and Reputation Section */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleLarge" style={styles.sectionTitle}>
            Level & Reputation
          </Text>

          <View style={styles.levelContainer}>
            <View style={styles.levelBadge}>
              <Text variant="displaySmall" style={styles.levelNumber}>
                {profile.level}
              </Text>
              <Text variant="bodySmall" style={styles.levelLabel}>
                Level
              </Text>
            </View>

            <View style={styles.levelInfo}>
              <View style={styles.progressHeader}>
                <Text variant="bodyMedium">Progress to Level {profile.level + 1}</Text>
                <Text variant="bodyMedium" style={styles.pointsText}>
                  {currentLevelPoints}/{pointsPerLevel}
                </Text>
              </View>
              <ProgressBar
                progress={progressToNextLevel}
                color={theme.colors.secondary}
                style={styles.progressBar}
              />
            </View>
          </View>

          <View style={styles.statsGrid}>
            <View style={styles.statItem}>
              <Text variant="headlineSmall" style={styles.statValue}>
                {profile.reputation_points}
              </Text>
              <Text variant="bodySmall" style={styles.statLabel}>
                Reputation Points
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text variant="headlineSmall" style={styles.statValue}>
                {profile.total_reviews_given}
              </Text>
              <Text variant="bodySmall" style={styles.statLabel}>
                Reviews Given
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text variant="headlineSmall" style={styles.statValue}>
                {profile.total_reviews_received}
              </Text>
              <Text variant="bodySmall" style={styles.statLabel}>
                Reviews Received
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* Current Squad/Guild Section */}
      {profile.current_squad && (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleLarge" style={styles.sectionTitle}>
              Current Learning
            </Text>
            <View style={styles.currentLearning}>
              <View style={styles.learningItem}>
                <Text variant="bodySmall" style={styles.learningLabel}>
                  Squad
                </Text>
                <Text variant="bodyLarge" style={styles.learningValue}>
                  {profile.current_squad}
                </Text>
              </View>
              <View style={styles.learningItem}>
                <Text variant="bodySmall" style={styles.learningLabel}>
                  Guild
                </Text>
                <Text variant="bodyLarge" style={styles.learningValue}>
                  {profile.current_guild}
                </Text>
              </View>
            </View>
          </Card.Content>
        </Card>
      )}

      {/* Skills Section */}
      <Card style={styles.card}>
        <Card.Content>
          <Text variant="titleLarge" style={styles.sectionTitle}>
            Skills
          </Text>
          <View style={styles.skillsContainer}>
            {profile.skills.map((skill, index) => (
              <Chip key={index} style={styles.skillChip} textStyle={styles.skillText}>
                {skill}
              </Chip>
            ))}
          </View>
        </Card.Content>
      </Card>

      {/* Certificates Section */}
      {profile.certificates.length > 0 && (
        <Card style={styles.card}>
          <Card.Content>
            <Text variant="titleLarge" style={styles.sectionTitle}>
              Certificates
            </Text>
            {profile.certificates.map((cert) => (
              <View key={cert.id} style={styles.certificateItem}>
                <View style={styles.certificateHeader}>
                  <Text variant="titleMedium" style={styles.certificateName}>
                    {cert.name}
                  </Text>
                  {cert.is_premium && (
                    <Chip
                      icon="crown"
                      style={styles.certPremiumBadge}
                      textStyle={styles.certPremiumText}>
                      Premium
                    </Chip>
                  )}
                </View>
                <Text variant="bodySmall" style={styles.certificateGuild}>
                  {cert.guild_name}
                </Text>
                <Text variant="bodySmall" style={styles.certificateDate}>
                  Issued: {new Date(cert.issued_date).toLocaleDateString()}
                </Text>
                <Divider style={styles.certificateDivider} />
              </View>
            ))}
          </Card.Content>
        </Card>
      )}

      {/* Actions */}
      <View style={styles.actions}>
        <Button mode="outlined" style={styles.actionButton}>
          Edit Profile
        </Button>
        <Button mode="outlined" style={styles.actionButton}>
          Settings
        </Button>
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
    alignItems: 'center',
    padding: 24,
    backgroundColor: theme.colors.primary + '10',
  },
  avatar: {
    backgroundColor: theme.colors.primary,
    marginBottom: 16,
  },
  name: {
    color: theme.colors.primary,
    marginBottom: 4,
  },
  email: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 12,
  },
  premiumBadge: {
    backgroundColor: theme.colors.secondary + '20',
  },
  premiumText: {
    color: theme.colors.secondary,
  },
  card: {
    margin: 16,
    marginBottom: 0,
  },
  sectionTitle: {
    color: theme.colors.primary,
    marginBottom: 16,
  },
  levelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  levelBadge: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: theme.colors.secondary,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  levelNumber: {
    color: theme.colors.onSecondary,
    fontWeight: 'bold',
  },
  levelLabel: {
    color: theme.colors.onSecondary,
  },
  levelInfo: {
    flex: 1,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  pointsText: {
    color: theme.colors.primary,
    fontWeight: '600',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    color: theme.colors.primary,
    fontWeight: 'bold',
  },
  statLabel: {
    color: theme.colors.text,
    opacity: 0.6,
    marginTop: 4,
    textAlign: 'center',
  },
  currentLearning: {
    gap: 16,
  },
  learningItem: {
    gap: 4,
  },
  learningLabel: {
    color: theme.colors.text,
    opacity: 0.6,
  },
  learningValue: {
    color: theme.colors.text,
    fontWeight: '600',
  },
  skillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillChip: {
    backgroundColor: theme.colors.primary + '10',
  },
  skillText: {
    color: theme.colors.primary,
  },
  certificateItem: {
    marginBottom: 16,
  },
  certificateHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  certificateName: {
    flex: 1,
    color: theme.colors.text,
  },
  certPremiumBadge: {
    backgroundColor: theme.colors.secondary + '20',
    height: 24,
  },
  certPremiumText: {
    color: theme.colors.secondary,
    fontSize: 10,
  },
  certificateGuild: {
    color: theme.colors.text,
    opacity: 0.7,
    marginBottom: 2,
  },
  certificateDate: {
    color: theme.colors.text,
    opacity: 0.5,
  },
  certificateDivider: {
    marginTop: 12,
  },
  actions: {
    padding: 16,
    gap: 12,
  },
  actionButton: {
    marginBottom: 8,
  },
});
