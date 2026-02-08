# Montserrat Font Setup

The ORIGIN app uses the Montserrat font family for all typography. Follow these steps to set up the fonts:

## Download Fonts

1. Download Montserrat from Google Fonts: https://fonts.google.com/specimen/Montserrat
2. You need the following font files:
   - Montserrat-Regular.ttf (400 weight)
   - Montserrat-Medium.ttf (500 weight)
   - Montserrat-Bold.ttf (700 weight)

## iOS Setup

1. Create a `fonts` directory in `ios/` if it doesn't exist
2. Copy the font files to `ios/fonts/`
3. Add the fonts to your Xcode project:
   - Open `ios/OriginMobile.xcodeproj` in Xcode
   - Right-click on the project and select "Add Files to..."
   - Select all font files from the `fonts` directory
   - Make sure "Copy items if needed" is checked
   - Make sure your target is selected

4. Update `ios/OriginMobile/Info.plist`:
```xml
<key>UIAppFonts</key>
<array>
  <string>Montserrat-Regular.ttf</string>
  <string>Montserrat-Medium.ttf</string>
  <string>Montserrat-Bold.ttf</string>
</array>
```

## Android Setup

1. Create directory: `android/app/src/main/assets/fonts/`
2. Copy all font files to this directory
3. The fonts will be automatically available in your app

## Verify Installation

Run the following command to link assets:
```bash
npx react-native-asset
```

Or manually link fonts in `react-native.config.js`:
```javascript
module.exports = {
  project: {
    ios: {},
    android: {},
  },
  assets: ['./assets/fonts/'],
};
```

## Usage

The fonts are configured in `src/theme/index.ts` and will be automatically applied through React Native Paper components:

```typescript
import {Text} from 'react-native-paper';

<Text variant="displaySmall">Uses Montserrat Bold</Text>
<Text variant="bodyLarge">Uses Montserrat Regular</Text>
```

## Fallback

If fonts are not loaded, the app will fall back to system fonts. Check the console for font loading errors during development.
