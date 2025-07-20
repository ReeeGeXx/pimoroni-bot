// Service Worker for Post Guardian Extension
console.log("Post Guardian service worker loaded!");

chrome.runtime.onInstalled.addListener((details) => {
    console.log('Post Guardian extension installed:', details.reason);
    chrome.storage.local.set({
        cacheStats: {
            hits: 0,
            misses: 0,
            apiCalls: 0,
            lastReset: Date.now()
        }
    });
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'ANALYZE_TEXT') {
        analyzeTextWithGemini(request.data)
            .then(analysis => sendResponse({ success: true, analysis }))
            .catch(error => {
                console.error('Analysis failed:', error);
                sendResponse({ success: false, error: error.message });
            });
        return true;
    }

    if (request.type === 'UPDATE_CACHE_STATS') {
        console.log('Cache stats updated:', request.stats);
        sendResponse({ success: true });
    }
});

async function analyzeTextWithGemini(data) {
    const { text, config } = data;

    if (!config.GEMINI_API_KEY || config.GEMINI_API_KEY === 'YOUR_GEMINI_API_KEY') {
        throw new Error('Gemini API key not configured');
    }

    let userPrompt = '';
    let riskLevelModifier = '';

    try {
        const { userCustomPrompt, riskLevel } = await new Promise((resolve) =>
            chrome.storage.local.get(['userCustomPrompt', 'riskLevel'], resolve)
        );

        if (userCustomPrompt?.trim()) {
            userPrompt = `\n\nADDITIONAL USER CONTEXT: ${userCustomPrompt.trim()}`;
        }

        const numericRisk = parseInt(riskLevel || '3', 10);
        if (numericRisk <= 2) {
            riskLevelModifier = `\n\nANALYSIS STRICTNESS: Be very lenient. Only flag things that are obviously dangerous or harmful.`;
        } else if (numericRisk === 3) {
            riskLevelModifier = `\n\nANALYSIS STRICTNESS: Be reasonably cautious. Flag clear risks but avoid being overly strict.`;
        } else if (numericRisk >= 4) {
            riskLevelModifier = `\n\nANALYSIS STRICTNESS: Be strict. If there is a high likelihood of harm or sensitive data leakage, flag it.`;
        }

    } catch (e) {
        console.warn('Could not retrieve settings from storage:', e);
    }


    const prompt = `
You are a privacy and security expert analyzing social media posts for potential privacy risks.

TEXT TO ANALYZE: "${text}"

Your task is to:
1. Identify ONLY words, phrases, or patterns that are truly sensitive, specific, and could realistically be used for harm (e.g., full addresses, SSNs, account numbers, specific medical diagnoses, full phone numbers, etc). Also include things the user maybe shouldn't say (threats, harassment, racism, sexism), but don't be super sensitive.
2. DO NOT flag general statements, feelings, vague references, or non-specific information (e.g., 'my medical life is good', 'I feel happy', 'I went to the doctor', 'my address is in New York', etc).
3. If you are not at least 90% confident that the information is a real privacy risk, DO NOT flag it.
4. For each risky element, explain WHY it is risky, HOW it could be exploited.
5. When reasonable suggest safer alternative words or phrases. Give the user an exact phrase or word, but if that doesn't make sense, tell them maybe you could remove this or that or try to exclude this from your post. Keep this relatively straight to the point so as not to bore the reader. The issue should be comprehended within the first sentence. Give a maximum of four alternatives.

IMPORTANT:
- Err on the side of caution: If you are unsure, do NOT flag.
- Only flag if the information is specific, sensitive, and could realistically be used for harm, identity theft, or fraud.
- Do NOT flag general or vague statements about health, feelings, or life.
- Do NOT flag partial or non-specific information.
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
${userPrompt} ${riskLevelModifier}
`;
    const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${config.GEMINI_MODEL}:generateContent?key=${config.GEMINI_API_KEY}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }]
        })
    });

    const indexID = '687bcbbc934487793c566db2';
    const videoID = "687bd58f61fa6d2e4d153e38";

    const tlResponse = await fetch(`https://api.twelvelabs.io/v1.2/videos/${indexID}/${videoID}?embedding_option=visual-text,audio&transcription=true`, {
        method: "GET",
        headers: {
            "x-api-key": config.TL_API_KEY,
            "Accept": "application/json"
        }
    });

    const searchQuery = prompt + "Alter this for a video, look for something along the lines of risky such as inapproriate content, car license plates, house addresses, etc.";

    const searchResponse = await fetch(`https://api.twelvelabs.io/v1/indexes/${indexID}/search`, {
        method: "POST",
        headers: {
            "x-api-key": config.TL_API_KEY,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            query: searchQuery,
            video_ids: [videoID]
        })
    });

    const searchResult = await searchResponse.json();
    console.log(searchResult);

    const tlData = await tlResponse.json();
    console.log(tlData);

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API request failed: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    const aiResponse = result.candidates[0].content.parts[0].text.trim();

    try {
        let cleaned = aiResponse;

        if (cleaned.startsWith('```json')) {
            cleaned = cleaned.replace(/^```json\s*/, '').replace(/\s*```$/, '');
        } else if (cleaned.startsWith('```')) {
            cleaned = cleaned.replace(/^```\s*/, '').replace(/\s*```$/, '');
        }

        const parsed = JSON.parse(cleaned);

        if (!parsed.riskLevel || !Array.isArray(parsed.riskyElements)) {
            throw new Error('Invalid response structure from AI');
        }

        return parsed;

    } catch (err) {
        console.error('Failed to parse AI response:', aiResponse);
        throw new Error('AI response could not be parsed as JSON');
    }
}

chrome.runtime.onStartup.addListener(() => {
    console.log('Post Guardian extension started');
});