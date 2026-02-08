# Firebase Cloud Messaging Setup

The ORIGIN app uses Firebase Cloud Messaging (FCM) for push notifications on both Android and iOS.

## Prerequisites

1. Create a Firebase project at https://console.firebase.google.com/
2. Add your Android and iOS apps to the Firebase project

## Android Setup

### 1. Download google-services.json

1. In Firebase Console, go to Project Settings
2. Download `google-services.json` for your Android app
3. Place it in `android/app/google-services.json`

### 2. Update build.gradle files

Add to `android/build.gradle`:
```gradle
buildscript {
  dependencies {
    classpath 'com.google.gms:google-services:4.3.15'
  }
}
```

Add to `android/app/build.gradle`:
```gradle
apply plugin: 'com.google.gms.google-services'
```

### 3. Update AndroidManifest.xml

The necessary permissions and services are already configured in the app.

## iOS Setup

### 1. Download GoogleService-Info.plist

1. In Firebase Console, go to Project Settings
2. Download `GoogleService-Info.plist` for your iOS app
3. Open `ios/OriginMobile.xcworkspace` in Xcode
4. Drag `GoogleService-Info.plist` into the project (make sure "Copy items if needed" is checked)

### 2. Enable Push Notifications

1. In Xcode, select your project
2. Go to "Signing & Capabilities"
3. Click "+ Capability"
4. Add "Push Notifications"
5. Add "Background Modes" and enable "Remote notifications"

### 3. Upload APNs Certificate

1. Generate an APNs certificate in Apple Developer Portal
2. Upload it to Firebase Console under Project Settings > Cloud Messaging > iOS app configuration

### 4. Update AppDelegate

The necessary Firebase initialization code should be added to `ios/OriginMobile/AppDelegate.mm`:

```objc
#import <Firebase.h>

- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)launchOptions
{
  [FIRApp configure];
  // ... rest of the code
}
```

## Testing Notifications

### Test from Firebase Console

1. Go to Firebase Console > Cloud Messaging
2. Click "Send your first message"
3. Enter notification title and text
4. Select your app
5. Send test message

### Test from Backend

The backend should send notifications using the FCM Admin SDK:

```python
from firebase_admin import messaging

message = messaging.Message(
    notification=messaging.Notification(
        title='Test Notification',
        body='This is a test message',
    ),
    data={
        'type': 'mention',
        'squadId': '123',
    },
    token=device_token,
)

response = messaging.send(message)
```

## Notification Types

The app handles these notification types:

1. **mention**: User mentioned in chat
   - Navigates to Chat screen
   - Data: `{type: 'mention', squadId: string}`

2. **syllabus_unlock**: New syllabus day unlocked
   - Navigates to SyllabusView screen
   - Data: `{type: 'syllabus_unlock', squadId: string}`

3. **peer_review**: Peer review request
   - Navigates to ReviewScreen
   - Data: `{type: 'peer_review', reviewId: string}`

4. **audio_standup**: New audio standup available
   - Navigates to SquadDetail screen
   - Data: `{type: 'audio_standup', squadId: string}`

## Troubleshooting

### Android

- Make sure `google-services.json` is in the correct location
- Rebuild the app after adding Firebase configuration
- Check logcat for Firebase initialization errors

### iOS

- Ensure APNs certificate is valid and uploaded to Firebase
- Check that Push Notifications capability is enabled
- Verify `GoogleService-Info.plist` is added to the Xcode project
- Check Xcode console for Firebase initialization errors

### Both Platforms

- Verify device token is being registered with backend
- Check Firebase Console for delivery status
- Ensure app has notification permissions
- Test on physical devices (push notifications don't work on simulators)

## Production Considerations

1. Use different Firebase projects for development and production
2. Implement proper error handling for token refresh
3. Handle notification permission denial gracefully
4. Implement notification preferences in user settings
5. Monitor notification delivery rates in Firebase Console
6. Set up notification analytics and tracking
