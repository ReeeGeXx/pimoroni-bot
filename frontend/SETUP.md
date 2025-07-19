# Post Guardian Setup Guide

This guide will help you set up the Post Guardian extension with the official Google GenAI SDK.

## Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- Google Gemini API key

## Step 1: Install Dependencies

```bash
npm install
```

This will install:
- `@google/genai` - Official Google GenAI SDK
- Webpack and build tools
- Babel for JavaScript transpilation
- Required polyfills for browser compatibility

## Step 2: Configure API Key

1. Get your Gemini API key from [Google AI Studio](https://ai.google.dev/api)
2. Open `src/config.js`
3. Replace `'YOUR_GEMINI_API_KEY'` with your actual API key:

```javascript
const config = {
    GEMINI_API_KEY: 'your_actual_api_key_here',
    // ... other settings
};
```

## Step 3: Build the Extension

```bash
# For production build
npm run build

# For development with watch mode
npm run dev
```

This will:
- Bundle the content script with the GenAI SDK
- Transpile modern JavaScript for browser compatibility
- Copy static files (manifest.json, popup.html, config.js) to the `dist` folder
- Create the final extension files in the `dist` directory

## Step 4: Load the Extension

### Chrome/Edge:
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top-right toggle)
3. Click "Load unpacked"
4. Select the `dist` folder (not the root project folder)

### Firefox:
1. Open Firefox and go to `about:debugging`
2. Click "This Firefox"
3. Click "Load Temporary Add-on"
4. Select the `manifest.json` file from the `dist` folder

## Step 5: Test the Extension

1. Navigate to X (Twitter) - `https://x.com`
2. Look for the Post Guardian icon in your browser toolbar
3. Try typing risky words like "password", "ssn", "credit card"
4. You should see:
   - Green underlines on risky words
   - AI-powered banner feedback below the tweet box

## Project Structure

```
post-guardian/
├── src/                    # Source files
│   ├── content.js         # Main content script (uses GenAI SDK)
│   ├── config.js          # Configuration file
│   └── popup.js           # Popup script
├── dist/                   # Built extension (created after build)
│   ├── content.js         # Bundled content script
│   ├── popup.js           # Bundled popup script
│   ├── config.js          # Configuration file
│   ├── manifest.json      # Extension manifest
│   └── popup.html         # Popup HTML
├── package.json           # Dependencies and scripts
├── webpack.config.js      # Build configuration
├── .babelrc              # Babel configuration
├── manifest.json         # Extension manifest
├── popup.html            # Popup HTML
└── README.md             # Project documentation
```

## Development Workflow

1. **Make changes** to files in the `src/` directory
2. **Build** with `npm run build` or `npm run dev` (watch mode)
3. **Reload** the extension in `chrome://extensions/`
4. **Refresh** the X page to see changes

## Troubleshooting

### Build Issues
- Ensure Node.js version is 18 or higher
- Delete `node_modules` and run `npm install` again
- Check that all dependencies are installed

### API Issues
- Verify your API key is correct in `src/config.js`
- Check that you have sufficient API quota
- Ensure the API key has access to Gemini Pro model

### Extension Not Working
- Make sure you're loading from the `dist` folder, not the root
- Check browser console for error messages
- Verify the extension is properly loaded

### Performance Issues
- Increase `DEBOUNCE_DELAY` to reduce API calls
- Check your internet connection
- Monitor API usage in Google AI Studio

## Features

- ✅ **Official Google GenAI SDK** - More reliable than raw API calls
- ✅ **Modern JavaScript** - ES6+ features with Babel transpilation
- ✅ **Webpack bundling** - Optimized for browser extensions
- ✅ **Real-time analysis** - AI-powered privacy risk assessment
- ✅ **Visual feedback** - Underlines and color-coded banners
- ✅ **Performance optimized** - Debounced API calls and caching

## Next Steps

- Customize the risky words list in `src/config.js`
- Adjust the AI prompt in `src/content.js`
- Add more social media platforms to `manifest.json`
- Enhance the popup interface in `popup.html` and `src/popup.js` 