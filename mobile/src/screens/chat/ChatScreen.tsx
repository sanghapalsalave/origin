/**
 * Chat screen with real-time messaging
 * Supports text, code, images, file attachments, and mentions
 */
import React, {useState, useRef, useEffect} from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Image,
} from 'react-native';
import {Text, TextInput, IconButton, Avatar, Chip} from 'react-native-paper';
import {useRoute, RouteProp} from '@react-navigation/native';
import DocumentPicker from 'react-native-document-picker';
import {launchImageLibrary} from 'react-native-image-picker';
import {RootStackParamList} from '../../navigation/AppNavigator';
import {ChatSkeleton} from '../../components/skeletons';
import {TouchableCard} from '../../components/touchable';
import {theme} from '../../theme';

type ChatScreenRouteProp = RouteProp<RootStackParamList, 'Chat'>;

interface Message {
  id: string;
  user_id: string;
  user_name: string;
  user_avatar?: string;
  content: string;
  type: 'text' | 'code' | 'image' | 'file';
  attachment_url?: string;
  attachment_name?: string;
  mentions?: string[];
  timestamp: Date;
  is_own_message: boolean;
}

// Mock data
const MOCK_MESSAGES: Message[] = [
  {
    id: '1',
    user_id: '2',
    user_name: 'Alice Johnson',
    content: 'Hey everyone! How are you progressing with today\'s tasks?',
    type: 'text',
    timestamp: new Date(Date.now() - 3600000),
    is_own_message: false,
  },
  {
    id: '2',
    user_id: '1',
    user_name: 'You',
    content: 'Going well! Just finished the reading assignment.',
    type: 'text',
    timestamp: new Date(Date.now() - 3000000),
    is_own_message: true,
  },
  {
    id: '3',
    user_id: '3',
    user_name: 'Bob Smith',
    content: '@Alice Johnson I have a question about the useState hook',
    type: 'text',
    mentions: ['Alice Johnson'],
    timestamp: new Date(Date.now() - 1800000),
    is_own_message: false,
  },
];

const MAX_MESSAGE_SIZE = 10 * 1024; // 10KB text limit

export const ChatScreen: React.FC = () => {
  const route = useRoute<ChatScreenRouteProp>();
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>(MOCK_MESSAGES);
  const [messageText, setMessageText] = useState('');
  const [isCodeMode, setIsCodeMode] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    if (messages.length > 0) {
      flatListRef.current?.scrollToEnd({animated: true});
    }
  }, [messages]);

  const handleSendMessage = () => {
    if (!messageText.trim()) return;

    // Check message size limit
    const messageSize = new Blob([messageText]).size;
    if (messageSize > MAX_MESSAGE_SIZE) {
      alert('Message exceeds 10KB limit. Please shorten your message.');
      return;
    }

    const newMessage: Message = {
      id: Date.now().toString(),
      user_id: '1',
      user_name: 'You',
      content: messageText,
      type: isCodeMode ? 'code' : 'text',
      timestamp: new Date(),
      is_own_message: true,
    };

    setMessages(prev => [...prev, newMessage]);
    setMessageText('');
    setIsCodeMode(false);
  };

  const handleImagePick = async () => {
    try {
      const result = await launchImageLibrary({
        mediaType: 'photo',
        quality: 0.8,
      });

      if (result.assets && result.assets[0]) {
        const newMessage: Message = {
          id: Date.now().toString(),
          user_id: '1',
          user_name: 'You',
          content: 'Shared an image',
          type: 'image',
          attachment_url: result.assets[0].uri,
          timestamp: new Date(),
          is_own_message: true,
        };

        setMessages(prev => [...prev, newMessage]);
      }
    } catch (error) {
      console.error('Image picker error:', error);
    }
  };

  const handleFilePick = async () => {
    try {
      const result = await DocumentPicker.pick({
        type: [DocumentPicker.types.allFiles],
      });

      // Check file size (10MB limit)
      if (result[0].size && result[0].size > 10 * 1024 * 1024) {
        alert('File size exceeds 10MB limit');
        return;
      }

      const newMessage: Message = {
        id: Date.now().toString(),
        user_id: '1',
        user_name: 'You',
        content: 'Shared a file',
        type: 'file',
        attachment_name: result[0].name,
        timestamp: new Date(),
        is_own_message: true,
      };

      setMessages(prev => [...prev, newMessage]);
    } catch (error) {
      if (!DocumentPicker.isCancel(error)) {
        console.error('File picker error:', error);
      }
    }
  };

  const formatTimestamp = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  const renderMessage = ({item}: {item: Message}) => {
    const isOwnMessage = item.is_own_message;

    return (
      <View
        style={[
          styles.messageContainer,
          isOwnMessage ? styles.ownMessageContainer : styles.otherMessageContainer,
        ]}>
        {!isOwnMessage && (
          <Avatar.Text
            size={32}
            label={item.user_name.split(' ').map(n => n[0]).join('')}
            style={styles.avatar}
          />
        )}

        <View
          style={[
            styles.messageBubble,
            isOwnMessage ? styles.ownMessageBubble : styles.otherMessageBubble,
            item.type === 'code' && styles.codeBubble,
          ]}>
          {!isOwnMessage && (
            <Text variant="labelSmall" style={styles.senderName}>
              {item.user_name}
            </Text>
          )}

          {item.mentions && item.mentions.length > 0 && (
            <View style={styles.mentionsContainer}>
              {item.mentions.map((mention, index) => (
                <Chip key={index} style={styles.mentionChip} textStyle={styles.mentionText}>
                  @{mention}
                </Chip>
              ))}
            </View>
          )}

          {item.type === 'image' && item.attachment_url && (
            <Image source={{uri: item.attachment_url}} style={styles.imageAttachment} />
          )}

          {item.type === 'file' && (
            <View style={styles.fileAttachment}>
              <IconButton icon="file-document" size={24} />
              <Text variant="bodySmall">{item.attachment_name}</Text>
            </View>
          )}

          <Text
            variant="bodyMedium"
            style={[
              styles.messageText,
              isOwnMessage ? styles.ownMessageText : styles.otherMessageText,
              item.type === 'code' && styles.codeText,
            ]}>
            {item.content}
          </Text>

          <Text
            variant="labelSmall"
            style={[
              styles.timestamp,
              isOwnMessage ? styles.ownTimestamp : styles.otherTimestamp,
            ]}>
            {formatTimestamp(item.timestamp)}
          </Text>
        </View>

        {isOwnMessage && (
          <Avatar.Text
            size={32}
            label="You"
            style={[styles.avatar, styles.ownAvatar]}
          />
        )}
      </View>
    );
  };

  if (loading) {
    return <ChatSkeleton />;
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}>
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={item => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messagesList}
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({animated: true})}
      />

      <View style={styles.inputContainer}>
        {isCodeMode && (
          <View style={styles.codeModeIndicator}>
            <IconButton icon="code-braces" size={16} />
            <Text variant="labelSmall">Code Mode</Text>
            <IconButton
              icon="close"
              size={16}
              onPress={() => setIsCodeMode(false)}
            />
          </View>
        )}

        <View style={styles.inputRow}>
          <IconButton
            icon="image"
            size={24}
            onPress={handleImagePick}
            style={styles.attachButton}
          />
          <IconButton
            icon="paperclip"
            size={24}
            onPress={handleFilePick}
            style={styles.attachButton}
          />
          <IconButton
            icon="code-braces"
            size={24}
            onPress={() => setIsCodeMode(!isCodeMode)}
            style={[styles.attachButton, isCodeMode && styles.activeCodeButton]}
          />

          <TextInput
            value={messageText}
            onChangeText={setMessageText}
            placeholder={isCodeMode ? 'Enter code snippet...' : 'Type a message...'}
            multiline
            maxLength={10240} // 10KB approximate character limit
            style={[styles.input, isCodeMode && styles.codeInput]}
            mode="outlined"
          />

          <IconButton
            icon="send"
            size={24}
            onPress={handleSendMessage}
            disabled={!messageText.trim()}
            style={styles.sendButton}
            iconColor={messageText.trim() ? theme.colors.primary : theme.colors.text}
          />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  messagesList: {
    padding: 16,
  },
  messageContainer: {
    flexDirection: 'row',
    marginBottom: 16,
    alignItems: 'flex-end',
  },
  ownMessageContainer: {
    justifyContent: 'flex-end',
  },
  otherMessageContainer: {
    justifyContent: 'flex-start',
  },
  avatar: {
    backgroundColor: theme.colors.primary,
  },
  ownAvatar: {
    backgroundColor: theme.colors.secondary,
  },
  messageBubble: {
    maxWidth: '70%',
    padding: 12,
    borderRadius: 16,
    marginHorizontal: 8,
  },
  ownMessageBubble: {
    backgroundColor: theme.colors.primary,
    borderBottomRightRadius: 4,
  },
  otherMessageBubble: {
    backgroundColor: theme.colors.surface,
    borderBottomLeftRadius: 4,
  },
  codeBubble: {
    backgroundColor: '#2d2d2d',
  },
  senderName: {
    color: theme.colors.primary,
    marginBottom: 4,
    fontWeight: '600',
  },
  mentionsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  mentionChip: {
    height: 24,
    marginRight: 4,
    marginBottom: 4,
    backgroundColor: theme.colors.secondary + '20',
  },
  mentionText: {
    fontSize: 10,
    color: theme.colors.secondary,
  },
  messageText: {
    marginBottom: 4,
  },
  ownMessageText: {
    color: theme.colors.onPrimary,
  },
  otherMessageText: {
    color: theme.colors.text,
  },
  codeText: {
    fontFamily: 'monospace',
    color: '#00ff00',
    fontSize: 12,
  },
  timestamp: {
    fontSize: 10,
  },
  ownTimestamp: {
    color: theme.colors.onPrimary,
    opacity: 0.7,
  },
  otherTimestamp: {
    color: theme.colors.text,
    opacity: 0.5,
  },
  imageAttachment: {
    width: 200,
    height: 200,
    borderRadius: 8,
    marginBottom: 8,
  },
  fileAttachment: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    marginBottom: 8,
  },
  inputContainer: {
    backgroundColor: theme.colors.background,
    borderTopWidth: 1,
    borderTopColor: theme.colors.surface,
    padding: 8,
  },
  codeModeIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.secondary + '10',
    paddingHorizontal: 8,
    borderRadius: 8,
    marginBottom: 8,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  attachButton: {
    margin: 0,
  },
  activeCodeButton: {
    backgroundColor: theme.colors.secondary + '20',
  },
  input: {
    flex: 1,
    maxHeight: 100,
    marginHorizontal: 8,
  },
  codeInput: {
    fontFamily: 'monospace',
    fontSize: 12,
  },
  sendButton: {
    margin: 0,
  },
});
