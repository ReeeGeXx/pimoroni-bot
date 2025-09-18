// Post Guardian Configuration
// Copy this file to dist/ and update with your actual API key
const PostGuardianConfig = {
    // Your Gemini API key - get one from https://makersuite.google.com/app/apikey
    //The API key will be injected by webpack during build
    GEMINI_API_KEY: "GEMINI_API_KEY_HERE",

    // Gemini model to use
    GEMINI_MODEL: 'gemini-1.5-flash',

    // Debounce delay for API calls (milliseconds)
    DEBOUNCE_DELAY: 500,

    // Confidence threshold for displaying risk levels
    CONFIDENCE_THRESHOLD: 70,

    // Banner colors for different risk levels
    BANNER_COLORS: {
        'LOW': '#28a745',
        'MEDIUM': '#ffc107',
        'HIGH': '#dc3545',
        'UNKNOWN': '#6c757d'
    }

    // Note: Risky words are now detected by AI instead of being hardcoded
};

// Make config available globally
if (typeof window !== 'undefined') {
    window.PostGuardianConfig = PostGuardianConfig;
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PostGuardianConfig;
} 