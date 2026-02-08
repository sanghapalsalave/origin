/**
 * Guild list screen with filtering
 */
import React, {useState} from 'react';
import {View, StyleSheet, FlatList} from 'react-native';
import {Text, Searchbar, Chip, Card, IconButton} from 'react-native-paper';
import {useNavigation} from '@react-navigation/native';
import {StackNavigationProp} from '@react-navigation/stack';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {GuildListSkeleton} from '../../components/skeletons';
import {TouchableCard} from '../../components/touchable';
import {theme} from '../../theme';

type GuildListScreenNavigationProp = StackNavigationProp<RootStackParamList, 'GuildList'>;

interface Guild {
  id: string;
  name: string;
  description: string;
  interest_area: string;
  member_count: number;
  is_premium: boolean;
  is_private: boolean;
}

// Mock data - will be replaced with API call
const MOCK_GUILDS: Guild[] = [
  {
    id: '1',
    name: 'Web Development Masters',
    description: 'Learn modern web development with React, Node.js, and TypeScript',
    interest_area: 'web-development',
    member_count: 245,
    is_premium: false,
    is_private: false,
  },
  {
    id: '2',
    name: 'Mobile Dev Pro',
    description: 'Master React Native and build cross-platform mobile apps',
    interest_area: 'mobile-development',
    member_count: 189,
    is_premium: true,
    is_private: false,
  },
  {
    id: '3',
    name: 'Data Science Academy',
    description: 'Python, ML, and data analysis for aspiring data scientists',
    interest_area: 'data-science',
    member_count: 312,
    is_premium: false,
    is_private: false,
  },
];

const INTEREST_FILTERS = [
  'All',
  'Web Development',
  'Mobile Development',
  'Data Science',
  'Machine Learning',
  'DevOps',
];

export const GuildListScreen: React.FC = () => {
  const navigation = useNavigation<GuildListScreenNavigationProp>();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('All');
  const [loading, setLoading] = useState(false);
  const [guilds, setGuilds] = useState<Guild[]>(MOCK_GUILDS);

  const handleGuildPress = (guild: Guild) => {
    navigation.navigate('GuildDetail', {guildId: guild.id});
  };

  const filteredGuilds = guilds.filter((guild) => {
    const matchesSearch = guild.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         guild.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = selectedFilter === 'All' || 
                         guild.interest_area === selectedFilter.toLowerCase().replace(' ', '-');
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return <GuildListSkeleton />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text variant="headlineMedium" style={styles.title}>
          Discover Guilds
        </Text>
        <Searchbar
          placeholder="Search guilds..."
          onChangeText={setSearchQuery}
          value={searchQuery}
          style={styles.searchBar}
        />
        
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={INTEREST_FILTERS}
          keyExtractor={(item) => item}
          renderItem={({item}) => (
            <Chip
              selected={selectedFilter === item}
              onPress={() => setSelectedFilter(item)}
              style={styles.filterChip}
              textStyle={styles.filterChipText}>
              {item}
            </Chip>
          )}
          contentContainerStyle={styles.filterList}
        />
      </View>

      <FlatList
        data={filteredGuilds}
        keyExtractor={(item) => item.id}
        renderItem={({item}) => (
          <TouchableCard onPress={() => handleGuildPress(item)} style={styles.guildCard}>
            <Card>
              <Card.Content>
                <View style={styles.cardHeader}>
                  <Text variant="titleLarge" style={styles.guildName}>
                    {item.name}
                  </Text>
                  {item.is_premium && (
                    <Chip icon="crown" style={styles.premiumBadge} textStyle={styles.premiumText}>
                      Premium
                    </Chip>
                  )}
                  {item.is_private && (
                    <Chip icon="lock" style={styles.privateBadge}>
                      Private
                    </Chip>
                  )}
                </View>
                
                <Text variant="bodyMedium" style={styles.description}>
                  {item.description}
                </Text>
                
                <View style={styles.cardFooter}>
                  <View style={styles.memberCount}>
                    <IconButton icon="account-group" size={16} />
                    <Text variant="bodySmall">{item.member_count} members</Text>
                  </View>
                  <IconButton icon="chevron-right" size={20} />
                </View>
              </Card.Content>
            </Card>
          </TouchableCard>
        )}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text variant="bodyLarge">No guilds found</Text>
            <Text variant="bodyMedium" style={styles.emptySubtext}>
              Try adjusting your search or filters
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
  header: {
    padding: 16,
    backgroundColor: theme.colors.background,
  },
  title: {
    color: theme.colors.primary,
    marginBottom: 16,
  },
  searchBar: {
    marginBottom: 16,
  },
  filterList: {
    paddingVertical: 8,
  },
  filterChip: {
    marginRight: 8,
  },
  filterChipText: {
    fontSize: 12,
  },
  listContent: {
    padding: 16,
  },
  guildCard: {
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    flexWrap: 'wrap',
  },
  guildName: {
    flex: 1,
    color: theme.colors.primary,
  },
  premiumBadge: {
    backgroundColor: theme.colors.secondary + '20',
    marginLeft: 8,
  },
  premiumText: {
    color: theme.colors.secondary,
    fontSize: 10,
  },
  privateBadge: {
    backgroundColor: theme.colors.surface,
    marginLeft: 8,
  },
  description: {
    marginBottom: 12,
    color: theme.colors.text,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  memberCount: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
  },
  emptySubtext: {
    marginTop: 8,
    color: theme.colors.text,
    opacity: 0.6,
  },
});
