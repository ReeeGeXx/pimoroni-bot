# Post Guardian - AI-Powered Privacy Protection

Post Guardian is a browser extension that uses AI to protect your privacy when posting on social media. It analyzes your text in real-time and provides intelligent feedback about potential privacy risks.

## Features

- Real-time Text Analysis: Monitors your posts as you type
- AI-Powered Risk Assessment: Uses Google's Gemini API for intelligent privacy analysis
- Smart Keyword Detection: Identifies potentially risky words and phrases
- Visual Risk Indicators: Color-coded banners show risk levels (LOW/MEDIUM/HIGH)
- Actionable Recommendations: Provides specific suggestions for safer alternatives
- Performance Optimized: Debounced API calls to minimize requests

## Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure API Key
1. Get your Gemini API key from [Google AI Studio](https://ai.google.dev/api)
2. Open `src/config.js`
3. Replace `'YOUR_GEMINI_API_KEY'` with your actual API key

### 3. Build the Extension
```bash
npm run build
```

### 4. Load in Browser
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `dist` folder

### 5. Test on X (Twitter)
1. Go to `https://x.com`
2. Try typing risky words like "password", "ssn", "credit card"
3. Watch for green underlines and AI feedback banners

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
└── README.md             # This file
```

## Development

### Build Commands
```bash
# Production build
npm run build

# Development with watch mode
npm run dev

# Clean build directory
npm run clean
```

### Making Changes
1. Edit files in the `src/` directory
2. Run `npm run build` (or `npm run dev` for watch mode)
3. Reload the extension in `chrome://extensions/`
4. Refresh the X page to see changes

## Configuration

### API Settings
```javascript
// src/config.js
const config = {
    GEMINI_API_KEY: 'your_api_key_here',
    GEMINI_MODEL: 'gemini-pro',
    DEBOUNCE_DELAY: 1000,        // Milliseconds between API calls
    CONFIDENCE_THRESHOLD: 70,    // Minimum confidence to show percentage
    // ... other settings
};
```

### Customizing Risky Words
Edit the `RISKY_WORDS` array in `src/config.js`:
```javascript
RISKY_WORDS: [
    // Personal Information
    'password', 'ssn', 'credit', 'card',
    // Financial
    'bank', 'account', 'routing',
    // Medical
    'diagnosis', 'prescription',
    // Add your own keywords here
]
```

## How it works ........

### Text Analysis Process
1. **Keyword Detection**: Scans text for predefined risky words
2. **AI Analysis**: Sends context to Gemini API for intelligent assessment
3. **Risk Assessment**: AI evaluates privacy risks and provides recommendations
4. **Visual Feedback**: Updates banners with color-coded risk levels and AI insights

### Visual Feedback
- **Green Banner**: No privacy risks detected
- **Yellow Banner**: Medium risk detected
- **Red Banner**: High risk detected
- **Blue Banner**: Analysis in progress or configuration needed

## API Response Format

The Gemini API returns structured JSON responses:

```json
{
    "riskLevel": "MEDIUM",
    "concerns": [
        "Contains personal financial information"
    ],
    "recommendations": [
        "Consider removing specific account details"
    ],
    "confidence": 85,
    "keywords": ["bank", "account", "routing"]
}
```

## Privacy & Security

- **Local Processing**: Text analysis happens locally before sending to API
- **Minimal Data**: Only detected keywords and context are sent to Gemini
- **No Storage**: Analysis results are not stored permanently
- **Secure API**: Uses Google's secure Gemini API endpoints

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
- Verify the extension is enabled in `chrome://extensions/`

### Performance Issues
- Increase `DEBOUNCE_DELAY` to reduce API calls
- Check your internet connection
- Monitor API usage in Google AI Studio

---

> [!IMPORTANT]
This tool is designed to help protect your privacy, but it's not a substitute for good judgment. Always review your posts before sharing!
