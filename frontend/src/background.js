// Service Worker for Post Guardian Extension
console.log("Post Guardian service worker loaded!");

// Handle extension installation
chrome.runtime.onInstalled.addListener((details) => {
    console.log('Post Guardian extension installed:', details.reason);

    // Set up initial storage if needed
    chrome.storage.local.set({
        cacheStats: {
            hits: 0,
            misses: 0,
            apiCalls: 0,
            lastReset: Date.now()
        }
    });
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'ANALYZE_TEXT') {
        analyzeTextWithGemini(request.data)
            .then(analysis => {
                sendResponse({ success: true, analysis });
            })
            .catch(error => {
                console.error('Analysis failed:', error);
                sendResponse({ success: false, error: error.message });
            });
        return true; // Keep message channel open for async response
    }

    if (request.type === 'UPDATE_CACHE_STATS') {
        // Update cache stats (for monitoring purposes)
        console.log('Cache stats updated:', request.stats);
        sendResponse({ success: true });
        return false;
    }
});

async function analyzeTextWithGemini(data) {
    const { text, config } = data;

    if (!config.GEMINI_API_KEY || config.GEMINI_API_KEY === 'YOUR_GEMINI_API_KEY') {
        throw new Error('Gemini API key not configured');
    }
    let userPrompt = '';
    try {
        const storage = await new Promise((resolve) =>
            chrome.storage.local.get(['userCustomPrompt'], resolve)
        );
        if (storage.userCustomPrompt && storage.userCustomPrompt.trim() !== '') {
            userInstruction = `\n\nADDITIONAL USER CONTEXT: ${storage.userCustomPrompt.trim()}`;
        }
    } catch (e) {
        console.warn('Could not retrieve user prompt:', e);
    }

    const prompt = `
You are a privacy and security expert analyzing social media posts for potential privacy risks.

TEXT TO ANALYZE: "${text}"

Your task is to:
1. Identify ONLY words, phrases, or patterns that are truly sensitive, specific, and could realistically be used for harm (e.g., full addresses, SSNs, account numbers, specific medical diagnoses, full phone numbers, etc). Also include things the user maybe shouldn't say (threats, harrasment, racism, sexism), but don't be super sensitive.
2. DO NOT flag general statements, feelings, vague references, or non-specific information (e.g., 'my medical life is good', 'I feel happy', 'I went to the doctor', 'my address is in New York', etc).
3. If you are not at least 90% confident that the information is a real privacy risk, DO NOT flag it.
4. For each risky element, explain WHY it is risky, HOW it could be exploited.
5. When reasonable suggest safer alternative words or phrases. Give the user an exact phrase or word, but if that doesn't make sense, tell them maybe you could remove this or that or try to exclude this from your post. Keep this relatively straight to the point so as not to bore the reader. The issue should be comprehended within the first sentence. Give a maximum of four alternatives.

IMPORTANT:
- Err on the side of caution: If you are unsure, do NOT flag.
- Only flag if the information is specific, sensitive, and could realistically be used for harm, identity theft, or fraud.
- Do NOT flag general or vague statements about health, feelings, or life (e.g., 'my medical life is good', 'I feel happy', 'I have a condition', etc).
- Do NOT flag partial or non-specific information (e.g., 'my address is 66' is NOT risky unless it is a full address).
- Justify each risk with clear, concrete and concise reasoning and concise real-world examples of misuse.
- DO NOT ADD THE RISK TO THE ALTERNATIVES, JUST ALTERNATIVE 1 AND 2, PLEASE DON'T CONCATENATE THEM TOGETHER

Please respond with this EXACT JSON format (no additional text):
{
    "riskLevel": "LOW|MEDIUM|HIGH",
    "confidence": 90,
    "riskyElements": [
        {
            "text": "the risky word or phrase",
            "type": "PERSONAL_INFO|FINANCIAL|MEDICAL|LOCATION|EMPLOYMENT|FAMILY|DATES|CREDENTIALS|CRITICAL|OTHER",
            "risk": "Concise explanation of why this is risky and how it could be exploited",
            "alternatives": ["safer alternative 1", "safer alternative 2", "safer alternative 3", "safer alternative 4"],
            "severity": "LOW|MEDIUM|HIGH"
        }
    ],
    "overallConcerns": ["short list of main privacy concerns"],
    "recommendations": ["short list of general recommendations"],
    "detectedKeywords": ["short list of all risky words/phrases found"]
}

If no risks are found, return:
{
    "riskLevel": "LOW",
    "confidence": 95,
    "riskyElements": [],
    "overallConcerns": [],
    "recommendations": ["Your post appears safe to share"],
    "detectedKeywords": []
}
    ${userPrompt}
`;



    try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${config.GEMINI_MODEL}:generateContent?key=${config.GEMINI_API_KEY}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: prompt
                    }]
                }]
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API request failed: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        const aiResponse = result.candidates[0].content.parts[0].text;

        // Try to parse the JSON response
        try {
            // Clean the response - remove markdown code blocks if present
            let cleanedResponse = aiResponse.trim();

            // Remove markdown code blocks (```json ... ```)
            if (cleanedResponse.startsWith('```json')) {
                cleanedResponse = cleanedResponse.replace(/^```json\s*/, '').replace(/\s*```$/, '');
            } else if (cleanedResponse.startsWith('```')) {
                cleanedResponse = cleanedResponse.replace(/^```\s*/, '').replace(/\s*```$/, '');
            }

            const analysis = JSON.parse(cleanedResponse);

            // Validate the response structure
            if (!analysis.riskLevel || !analysis.riskyElements) {
                throw new Error('Invalid response structure from AI');
            }

            return analysis;
        } catch (parseError) {
            console.error('Failed to parse AI response:', aiResponse);
            console.error('Parse error:', parseError);
            throw new Error('AI response could not be parsed as JSON');
        }
    } catch (error) {
        console.error('Gemini API error:', error);
        throw error;
    }
}

// Handle extension startup
chrome.runtime.onStartup.addListener(() => {
    console.log('Post Guardian extension started');
});