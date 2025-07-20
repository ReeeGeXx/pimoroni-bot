import { LRUCache } from './cache-manager.js';

console.log("Post Guardian content script loaded!");

// Get config from global window object (loaded by manifest.json)
let config;
if (window.PostGuardianConfig) {
    config = window.PostGuardianConfig;
} else {
    // Fallback configuration if config file not loaded
    config = {
        GEMINI_API_KEY: 'AIzaSyAQQHZosNLZsF5QUzRc3NonigEecOGybFE',
        GEMINI_MODEL: 'gemini-1.5-flash',
        DEBOUNCE_DELAY: 1000,
        CONFIDENCE_THRESHOLD: 70,
        BANNER_COLORS: {
            'LOW': '#28a745',
            'MEDIUM': '#ffc107',
            'HIGH': '#dc3545',
            'UNKNOWN': '#6c757d'
        }
    };
}

// Initialize cache manager
const cacheManager = new LRUCache(20); // Store last 20 analyses

// Smart caching system
// Replace contextCache with LRUCache
const textCache = new LRUCache(20); // Store last 20 analyses
let lastAnalyzedText = '';

function jaccardSimilarity(a, b) {
    const setA = new Set(a.toLowerCase().split(/\s+/));
    const setB = new Set(b.toLowerCase().split(/\s+/));
    const intersection = new Set([...setA].filter(x => setB.has(x)));
    const union = new Set([...setA, ...setB]);
    return intersection.size / union.size;
}

function shouldAnalyze(newText, lastText, cache) {
    const hash = generateTextHash(newText);
    if (cache.has(hash)) return false;
    if (lastText && jaccardSimilarity(newText, lastText) > 0.9) return false;
    return true;
}

// Cache structure:
// textCache: { textHash: { analysis, timestamp, riskyElements } }

function generateTextHash(text) {
    // Simple hash for text comparison
    return text.toLowerCase().replace(/\s+/g, ' ').trim();
}

function isContextSignificantlyDifferent(newText, oldText) {
    if (!oldText) return true;

    const newHash = generateTextHash(newText);
    const oldHash = generateTextHash(oldText);

    // Check if context changed significantly (more than just adding/removing words)
    const newWords = new Set(newText.toLowerCase().split(/\s+/));
    const oldWords = new Set(oldText.toLowerCase().split(/\s+/));

    // If more than 30% of words changed, consider it significant
    const totalWords = new Set([...newWords, ...oldWords]);
    const changedWords = Math.abs(newWords.size - oldWords.size) +
        [...newWords].filter(w => !oldWords.has(w)).length;

    return (changedWords / totalWords.size) > 0.3 || newHash !== oldHash;
}

function getCachedAnalysis(text) {
    const textHash = generateTextHash(text);
    const cached = textCache.get(textHash);

    if (!cached) {
        return null;
    }

    // Check if cache is still valid (within 1 hour)
    const cacheAge = Date.now() - cached.timestamp;
    if (cacheAge > 3600000) { // 1 hour
        textCache.delete(textHash);
        return null;
    }

    return cached.analysis;
}

function cacheAnalysis(text, analysis) {
    const textHash = generateTextHash(text);
    textCache.set(textHash, {
        analysis,
        timestamp: Date.now(),
        riskyElements: analysis.riskyElements || []
    });
}

async function analyzeTextWithGemini(text) {
    if (!config.GEMINI_API_KEY || config.GEMINI_API_KEY === 'YOUR_GEMINI_API_KEY') {
        console.warn('Gemini API key not configured. Please set your API key in config.js');
        return null;
    }

    // Check cache first
    const cachedAnalysis = getCachedAnalysis(text);
    if (cachedAnalysis) {
        console.log('Using cached analysis');
        return cachedAnalysis;
    }

    cacheManager.stats.apiCalls++;
    console.log(`Making API call #${cacheManager.stats.apiCalls} to Gemini via service worker`);

    try {
        // Send message to service worker for API call
        const response = await chrome.runtime.sendMessage({
            type: 'ANALYZE_TEXT',
            data: {
                text,
                config
            }

        });

        console.log(text);

        if (response.success && response.analysis) {
            // Cache the analysis
            cacheAnalysis(text, response.analysis);

            // Update cache stats in service worker
            chrome.runtime.sendMessage({
                type: 'UPDATE_CACHE_STATS',
                stats: cacheManager.getStats()
            });

            return response.analysis;
        } else {
            console.error('Service worker analysis failed:', response.error);
            return null;
        }
    } catch (error) {
        console.error('Failed to communicate with service worker:', error);
        return null;
    }
}

// Inject custom CSS for modern UI, animations, and dark mode
function injectPostGuardianStyles() {
    if (document.getElementById('post-guardian-styles')) return;
    const style = document.createElement('style');
    style.id = 'post-guardian-styles';
    style.innerHTML = `
    .post-guardian-scorebar {
        width: 100%;
        max-width: 500px;
        margin: 0 auto 8px auto;
        height: 18px;
        border-radius: 9px;
        background: linear-gradient(90deg, #e0e7ef 0%, #f3f4f6 100%);
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        overflow: hidden;
        position: relative;
        transition: background 0.3s;
    }
    .post-guardian-scorebar-inner {
        height: 100%;
        border-radius: 9px;
        background: linear-gradient(90deg, #28a745 0%, #ffc107 50%, #dc3545 100%);
        transition: width 0.5s cubic-bezier(.4,2,.6,1), background 0.3s;
    }
    .post-guardian-scorebar-label {
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        font-size: 12px;
        font-weight: 500;
        color: #222;
        text-shadow: none;
        pointer-events: none;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    }
    .post-guardian-banner-animated {
        animation: fadeInBanner 0.7s;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
        border-radius: 8px;
        transition: background 0.3s, color 0.3s;
    }
    @keyframes fadeInBanner {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .risky-word {
        animation: riskyPulse 1.5s infinite alternate;
        transition: border-color 0.3s;
    }
    @keyframes riskyPulse {
        0% { border-bottom-width: 2px; }
        100% { border-bottom-width: 4px; }
    }
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .post-guardian-scorebar {
            background: linear-gradient(90deg, #23272f 0%, #2d3748 100%);
        }
        .post-guardian-scorebar-label {
            color: #eee;
        }
        .post-guardian-banner-animated {
            background: #23272f !important;
            color: #eee !important;
        }
        #post-guardian-tooltip {
            background: #23272f !important;
            color: #eee !important;
            border: 1px solid #444 !important;
        }
    }
    `;
    document.head.appendChild(style);
}

// Inject styles on load
injectPostGuardianStyles();

// Add privacy score bar above tweet box
// Remove privacy score bar and related logic
// Remove lastPrivacyScore, updatePrivacyScoreBar, updatePrivacyScore, maybeShowConfetti, and all confetti/score logic
// Remove all console.log('You deleted text'), 'typed something', and confetti logs
// Only keep minimal banner and tooltip

// In checkForRiskyWords, remove updatePrivacyScore and maybeShowConfetti calls
// Only show banner if there is a real risk (analysis.riskLevel !== 'LOW')

// In event listeners, update overlays instantly on every keystroke (no debounce for underlines)
function updateOverlay(tweetBox, overlay, analysis) {
    // Get plain text from the tweet box
    const plainText = tweetBox.innerText;
    let html = '';

    // Vibrant color palette by risk type
    const typeColors = {
        'CRITICAL': '#ff0000ff',
        'CREDENTIALS': '#dc3545',
        'FINANCIAL': '#d63384',
        'MEDICAL': '#e83e8c',
        'LOCATION': '#fd7e14',
        'PERSONAL_INFO': '#ffc107',
        'FAMILY': '#17a2b8',
        'DATES': '#6c757d',
        'OTHER': '#6c757d',
        'DEFAULT': '#bdbdbd'
    };

    if (analysis && analysis.riskyElements && analysis.riskyElements.length > 0) {
        // Find all risky element matches and their indices
        let matches = [];
        analysis.riskyElements.forEach(element => {
            if (!element.text) return;
            // Pick color by type, fallback to default
            let color = typeColors[element.type] || typeColors['DEFAULT'];
            //ILove ReGEXXXX!!!!
            const regex = new RegExp(element.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
            let match;
            while ((match = regex.exec(plainText)) !== null) {
                matches.push({
                    start: match.index,
                    end: match.index + match[0].length,
                    text: match[0],
                    color,
                    type: element.type,
                    risk: element.risk,
                    alternatives: element.alternatives ? element.alternatives.join('|') : ''
                });
                //Prevent infinite loop for zero-length matches
                if (regex.lastIndex === match.index) regex.lastIndex++;
            }
        });
        // Sort matches by start index
        matches.sort((a, b) => a.start - b.start);
        // Remove overlaps: keep the longest match at each position
        let nonOverlapping = [];
        let lastEnd = 0;
        for (let i = 0; i < matches.length; i++) {
            if (matches[i].start >= lastEnd) {
                nonOverlapping.push(matches[i]);
                lastEnd = matches[i].end;
            }
        }
        // Build the HTML
        let cursor = 0;
        for (let i = 0; i < nonOverlapping.length; i++) {
            const m = nonOverlapping[i];
            // Add text before the match
            if (cursor < m.start) {
                html += escapeHtml(plainText.slice(cursor, m.start));
            }
            // Add the highlighted span
            html += `<span class="risky-word" style="border-bottom: 4px solid ${m.color}; padding-bottom: 2px; background: none; color: inherit; cursor: help; pointer-events: auto; display: inline; box-decoration-break: clone;" data-risk-type="${m.type}" data-risk-explanation="${escapeHtml(m.risk)}" data-alternatives="${escapeHtml(m.alternatives)}${escapeHtml(m.risk)}">${escapeHtml(m.text)}</span>`;
            cursor = m.end;
        }
        // Add any remaining text
        if (cursor < plainText.length) {
            html += escapeHtml(plainText.slice(cursor));
        }
    } else {
        // No risks: show text unmodified, no placeholder, no flicker
        html = escapeHtml(plainText);
    }
    overlay.innerHTML = html;

    // Add hover event listeners to risky words
    const riskyWords = overlay.querySelectorAll('.risky-word');
    riskyWords.forEach(wordSpan => {
        wordSpan.removeEventListener('mouseenter', showTooltip);
        wordSpan.removeEventListener('mouseleave', hideTooltip);
        wordSpan.addEventListener('mouseenter', showTooltip);
        wordSpan.addEventListener('mouseleave', hideTooltip);
    });
}

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function toTitleCase(str) {
    return str
        .toLowerCase()
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

// Tooltip functionality (professional tone)
function showTooltip(event) {
    const word = event.target;
    const rect = word.getBoundingClientRect();
    // Remove existing tooltip
    const existingTooltip = document.getElementById('post-guardian-tooltip');
    if (existingTooltip) existingTooltip.remove();
    // Get risk data from the span
    const riskType = word.dataset.riskType || 'OTHER';
    const riskExplanation = word.dataset.riskExplanation || 'This word may contain sensitive information.';
    const alternatives = word.dataset.alternatives ? word.dataset.alternatives.split('|') : [];
    //let riskLevel = word.dataset.riskLevel || 'LOW';
    // Severity color accent
    let accentColor = '#6c757d';
    if (['CRITICAL'].includes(riskType)) accentColor = '#ff0000ff';
    else if (['CREDENTIALS'].includes(riskType)) accentColor = '#dc3545';
    else if (['FINANCIAL'].includes(riskType)) accentColor = '#d63384';
    else if (['MEDICAL'].includes(riskType)) accentColor = '#e83e8c';
    else if (['LOCATION'].includes(riskType)) accentColor = '#fd7e14';
    else if (['PERSONAL_INFO'].includes(riskType)) accentColor = '#ffc107';
    else if (['FAMILY'].includes(riskType)) accentColor = '#17a2b8';
    else if (['DATES'].includes(riskType)) accentColor = '#6c757d';
    else if (['OTHER'].includes(riskType)) accentColor = '#6c757d';

    let riskTypeDisplay = toTitleCase(riskType);
    //let riskLevelDisplay = toTitleCase(riskLevel);
    //if (riskTypeDisplay === 'personal_info') riskTypeDisplay = 'Personal Info';
    // Create tooltip
    const tooltip = document.createElement('div');
    tooltip.id = 'post-guardian-tooltip';
    tooltip.style = `
        position: fixed;
        top: ${rect.bottom + 8}px;
        left: ${Math.min(rect.left, window.innerWidth - 360)}px;
        background: #fff;
        color: #222;
        padding: 20px 24px 18px 20px;
        border-radius: 14px;
        font-size: 15px;
        z-index: 10000;
        max-width: 340px;
        min-width: 220px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.18);
        border: 1.5px solid #ff0000ff;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        display: flex;
        flex-direction: column;
        gap: 8px;
        animation: fadeInBanner 0.3s;
    `;
    // Accent dot and close button
    const accentDot = `<span style="display:inline-block;width:13px;height:13px;border-radius:50%;background:${accentColor};margin-right:10px;vertical-align:middle;"></span>`;
    const closeBtn = `<span id="pg-tooltip-close" style="position:absolute;top:8px;right:12px;font-size:18px;cursor:pointer;color:#888;">&times;</span>`;
    // Shorten risk explanation to 1-2 lines
    let shortRisk = riskExplanation.split('. ').slice(0, 2).join('. ') + (riskExplanation.endsWith('.') ? '' : '.');
    // Tooltip content
    let tooltipContent = `
        ${closeBtn}
        <div style="display:flex;align-items:center;margin-bottom:6px;">
            ${accentDot}
            <span style="font-weight:600;font-size:16px;color:${accentColor}; text-transform: lowercase; text-transform: capitalize;">${riskTypeDisplay} Risk</span>
        </div>
        <div style="margin-bottom:6px;font-weight:600;">"${word.textContent}"</div>
        <div style="margin-bottom:8px;font-size:14px;color:${accentColor};"><strong>Why this is risky:</strong> ${shortRisk}</div>
    `;
    if (alternatives.length > 0 && alternatives[0].trim() !== '') {
        tooltipContent += `
            <div style="font-size: 14px; color: #2563eb; margin-top: 2px; text-transform: capitalize">
                <strong>How to rephrase:</strong><br>
                ${alternatives.map(alt => `• ${alt}`).join('<br>').split(riskExplanation)}
            </div>
        `;
    }
    tooltip.innerHTML = tooltipContent;
    document.body.appendChild(tooltip);
    // Close button event
    tooltip.querySelector('#pg-tooltip-close').onclick = () => tooltip.remove();
    // Adjust position if tooltip goes off screen
    const tooltipRect = tooltip.getBoundingClientRect();
    if (tooltipRect.right > window.innerWidth) {
        tooltip.style.left = `${window.innerWidth - tooltipRect.width - 10}px`;
    }
    if (tooltipRect.bottom > window.innerHeight) {
        tooltip.style.top = `${rect.top - tooltipRect.height - 8}px`;
    }
}

function hideTooltip() {
    const tooltip = document.getElementById('post-guardian-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

function checkTweetBox() {
    const tweetBoxes = document.querySelectorAll('[aria-label="Post text"]');
    tweetBoxes.forEach((tweetBox, index) => {
        tweetBox.style.position = "relative";
        createOverlay(tweetBox, index);
    });
}

// Debounce function to limit API calls
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const debouncedCheckForRiskyWords = debounce(checkForRiskyWords, 900);

const observer = new MutationObserver(() => {
    insertPostGuardian?.();
    checkTweetBox(); //Finds tweetbox and sets dimensions/style accordingly (differs based on screen size)
});

document.addEventListener('input', (e) => {
    if (e.target.closest('[contenteditable="true"]')) {
        const tweetBoxes = document.querySelectorAll('[aria-label="Post text"]');
        tweetBoxes.forEach((tweetBox, index) => {
            const overlay = tweetBox.parentElement?.querySelector(`#post-guardian-overlay-${index}`);
            if (overlay) {
                // Use the latest analysis if available, else null
                const text = tweetBox.innerText;
                const analysis = getCachedAnalysis(text);
                updateOverlay(tweetBox, overlay, analysis);
            }
        });
        debouncedCheckForRiskyWords();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.target.closest('[contenteditable="true"]')) {
        if (['Backspace', 'Delete'].includes(e.key)) {
            setTimeout(() => {
                const tweetBoxes = document.querySelectorAll('[aria-label="Post text"]');
                tweetBoxes.forEach((tweetBox, index) => {
                    const overlay = tweetBox.parentElement?.querySelector(`#post-guardian-overlay-${index}`);
                    if (overlay) {
                        const text = tweetBox.innerText;
                        const analysis = getCachedAnalysis(text);
                        updateOverlay(tweetBox, overlay, analysis);
                    }
                });
            }, 0);
        }
        debouncedCheckForRiskyWords();
    }
});

document.addEventListener('paste', (e) => {
    if (e.target.closest('[contenteditable="true"]')) {
        setTimeout(() => {
            const tweetBoxes = document.querySelectorAll('[aria-label="Post text"]');
            tweetBoxes.forEach((tweetBox, index) => {
                const overlay = tweetBox.parentElement?.querySelector(`#post-guardian-overlay-${index}`);
                if (overlay) {
                    const text = tweetBox.innerText;
                    const analysis = getCachedAnalysis(text);
                    updateOverlay(tweetBox, overlay, analysis);
                }
            });
            debouncedCheckForRiskyWords();
        }, 0);

    }
});

observer.observe(document.body, {
    childList: true,
    subtree: true,
});

// Update banner to use professional, friendly microcopy
function updateBannerWithAI(banner, analysis) {
    if (!analysis || !analysis.riskyElements || analysis.riskyElements.length === 0) {
        banner.style.display = 'none';
        banner.innerHTML = '';
        return;
    }
    const color = config.BANNER_COLORS[analysis.riskLevel] || config.BANNER_COLORS['UNKNOWN'];
    banner.classList.add('post-guardian-banner-animated');
    banner.style = `
        background: ${color}10;
        padding: 14px 18px;
        margin-top: 8px;
        font-size: 14px;
        color: ${color};
        border-left: 4px solid ${color};
        border-radius: 8px;
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    `;
    let bannerText = `<strong>${analysis.riskyElements.length} privacy risk${analysis.riskyElements.length > 1 ? 's' : ''} detected.</strong> <span style="font-size:13px;color:#555;">Click underlined words for details.</span>`;
    if (analysis.confidence > config.CONFIDENCE_THRESHOLD) {
        bannerText += `<div style="font-size:12px;color:#888;margin-top:8px;">Confidence: ${analysis.confidence}%</div>`;
    }
    banner.innerHTML = bannerText;
    banner.style.display = '';
}

function insertPostGuardian() {
    const tweetBoxes = document.querySelectorAll('[aria-label="Post text"]');

    tweetBoxes.forEach((tweetBox, index) => {
        // Skip if a banner already exists next to this box
        if (tweetBox.parentElement?.querySelector(`#post-guardian-banner-${index}`)) return;

        const banner = document.createElement("div");
        banner.id = `post-guardian-banner-${index}`; // unique ID for each
        banner.style = `
            background: rgba(0, 123, 255, 0.1);
            padding: 8px;
            margin-top: 5px;
            font-size: 12px;
            color: #007bff;
            border-left: 3px solid #007bff;
        `;
        banner.innerText = "🛡️ Post Guardian is watching this tweet for privacy risks...";

        // Insert post guardian banner below tweet box
        tweetBox.parentElement?.insertBefore(banner, tweetBox.nextSibling);
    });
}

async function checkForRiskyWords() {
    const spans = document.querySelectorAll('span[data-text="true"]');
    let fullText = '';

    spans.forEach((span) => {
        const text = span.textContent;
        fullText += text + ' ';
    });

    const trimmedText = fullText.trim();

    if (trimmedText.length === 0) {
        // Hide banners when no text
        const banners = document.querySelectorAll('[id^="post-guardian-banner-"]');
        banners.forEach(banner => {
            banner.style.display = 'none';
        });

        // Clear overlays
        const tweetBoxes = document.querySelectorAll('[aria-label="Post text"]');
        tweetBoxes.forEach((tweetBox, index) => {
            const overlay = tweetBox.parentElement?.querySelector(`#post-guardian-overlay-${index}`);
            if (overlay) {
                overlay.innerHTML = '';
            }
        });

        lastAnalyzedText = '';
        return null;
    }

    // Always update overlays immediately
    const tweetBoxes = document.querySelectorAll('[aria-label="Post text"]');
    tweetBoxes.forEach((tweetBox, index) => {
        const overlay = tweetBox.parentElement?.querySelector(`#post-guardian-overlay-${index}`);
        if (overlay) {
            const analysis = getCachedAnalysis(trimmedText);
            updateOverlay(tweetBox, overlay, analysis);
        }
    });

    // Check if context changed significantly
    const contextChanged = isContextSignificantlyDifferent(trimmedText, lastAnalyzedText);
    let analysis = null;

    if (contextChanged) {
        lastAnalyzedText = trimmedText;

        // Get AI analysis
        analysis = await analyzeTextWithGemini(trimmedText);

        if (analysis && analysis.riskyElements) {
            // currentRiskyElements = analysis.riskyElements; // This line is removed as per new_code
        }

        // Show/hide banner based on risk
        const banners = document.querySelectorAll('[id^="post-guardian-banner-"]');
        banners.forEach(banner => {
            if (analysis && analysis.riskLevel !== 'LOW') {
                banner.style.display = '';
                updateBannerWithAI(banner, analysis);
            } else {
                banner.style.display = 'none';
            }
        });

        // Update overlays with new risky elements
        tweetBoxes.forEach((tweetBox, index) => {
            const overlay = tweetBox.parentElement?.querySelector(`#post-guardian-overlay-${index}`);
            if (overlay) {
                updateOverlay(tweetBox, overlay, analysis);
            }
        });
    } else {
        analysis = getCachedAnalysis(trimmedText);

        if (analysis && analysis.riskyElements) {
            // currentRiskyElements = analysis.riskyElements; // This line is removed as per new_code
        }

        if (analysis) {
            // Update all banners with cached AI feedback
            const banners = document.querySelectorAll('[id^="post-guardian-banner-"]');
            banners.forEach(banner => {
                if (analysis && analysis.riskLevel !== 'LOW') {
                    banner.style.display = '';
                    updateBannerWithAI(banner, analysis);
                } else {
                    banner.style.display = 'none';
                }
            });
        }
    }

    return analysis;
}

function createOverlay(tweetBox, index) {
    const overlayId = `post-guardian-overlay-${index}`;
    if (tweetBox.parentElement?.querySelector(`#${overlayId}`)) return;

    // Lines 57-75 just style the overlay to match the twitter tweet box
    const overlay = document.createElement("div");
    overlay.id = overlayId;
    overlay.style = `
        position: absolute;
        top: ${tweetBox.offsetTop}px;
        left: ${tweetBox.offsetLeft}px;
        width: ${tweetBox.offsetWidth}px;
        height: ${tweetBox.offsetHeight}px;
        pointer-events: none;
        color: transparent;
        white-space: pre-wrap;
        overflow-wrap: break-word;
        z-index: 9999;
        font-size: ${window.getComputedStyle(tweetBox).fontSize};
        line-height: ${window.getComputedStyle(tweetBox).lineHeight};
        font-family: ${window.getComputedStyle(tweetBox).fontFamily};
        padding: ${window.getComputedStyle(tweetBox).padding};
    `;
    overlay.className = "post-guardian-overlay";

    tweetBox.parentElement?.appendChild(overlay);
    updateOverlay(tweetBox, overlay, null); // Pass null for now, will be updated after analysis
}

function watchForFileInput() {
    document.body.addEventListener("click", async (e) => {
        // Wait for user to click the media icon
        setTimeout(async () => {
            const inputs = document.querySelectorAll('input[type="file"]');

            inputs.forEach((input) => {
                if (input.dataset.pgIntercepted) return;
                input.dataset.pgIntercepted = "true";

                input.addEventListener("change", async (e) => {
                    const files = e.target.files;
                    if (!files || files.length === 0) return;

                    for (const file of files) {
                        if (file.type.startsWith("video/")) {
                            console.log("[Post Guardian] Intercepted video:", file.name);

                            const blobUrl = URL.createObjectURL(file);
                            console.log(`[Post Guardian] Blob URL: ${blobUrl}`);

                            // Optionally preview the video or upload to backend here
                        }
                    }
                });
            });

            // Now you can use await safely
            const responseTL = await chrome.runtime.sendMessage({
                type: 'ANALYZE_VIDEO',
                data: { config }
            });
            console.log('Response from listener:', responseTL);
        }, 300);
    });
}

watchForFileInput();
