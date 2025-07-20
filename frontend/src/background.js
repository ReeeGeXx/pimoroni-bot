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
    // TEXT analysis branch
    if (request.type === 'ANALYZE_TEXT') {
        analyzeTextWithGemini(request.data)
            .then(analysis => sendResponse({ success: true, analysis }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // keep port open for async
    }

    // CACHE‑stats branch (sync)
    if (request.type === 'UPDATE_CACHE_STATS') {
        console.log('Cache stats updated:', request.stats);
        sendResponse({ success: true });
        return false; // sync, no async work
    }

    // VIDEO analysis branch
    if (request.type === 'ANALYZE_VIDEO') {
        const tlPrompt = " You are sending a prompt to twelvelabs telling it to find clips for inappropriate content in a video such as middle fingers, bad words (audio or visual), license plates, addresses and what not, be concise";
        (async () => {
            try {
                // 1) Call Gemini
                const geminiRes = await fetch(
                    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyCn0EamibbU1b6O0izrJF5xDCeCCoNVHLc`,
                    {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            contents: [{ parts: [{ text: tlPrompt }] }]
                        })
                    }
                );
                if (!geminiRes.ok) {
                    const t = await geminiRes.text();
                    throw new Error(`Gemini error ${geminiRes.status}: ${t}`);
                }
                const geminiJson = await geminiRes.json();
                const tlResponse = geminiJson.candidates[0].content.parts[0].text.trim();

                // 2) Call your Flask backend
                const flaskRes = await fetch("http://localhost:5000/analyze-video", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt: tlResponse })
                });
                if (!flaskRes.ok) {
                    const errText = await flaskRes.text();
                    throw new Error(`Flask error ${flaskRes.status}: ${errText}`);
                }
                const analysis = await flaskRes.json();
                sendResponse({ success: true, analysis });
            } catch (error) {
                console.error("ANALYZE_VIDEO failed:", error);
                sendResponse({ success: false, error: error.message });
            }
        })();
        return true;
    }

    // default fallback
    sendResponse({ success: false, error: "Unrecognized request type." });
    return false;
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

// chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {

// });

