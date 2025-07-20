document.addEventListener('DOMContentLoaded', function () {
    console.log('Post Guardian popup loaded');

    const statusElement = document.getElementById('status');
    const textarea = document.getElementById('userPrompt');
    const saveButton = document.getElementById('savePrompt');
    const riskSlider = document.getElementById('riskLevel');
    const riskLabel = document.getElementById('riskLevelValue');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultDisplay = document.getElementById('result');

    // Initial status
    if (statusElement) {
        statusElement.textContent = 'Post Guardian is active!';
    }

    // Load saved values
    chrome.storage.local.get(['userCustomPrompt', 'riskLevel'], (result) => {
        if (result.userCustomPrompt) {
            textarea.value = result.userCustomPrompt;
        }

        const savedRisk = parseInt(result.riskLevel || '3', 10);
        riskSlider.value = savedRisk;
        updateRiskLabel(savedRisk);
    });

    // Update label on slider change
    riskSlider.addEventListener('input', (e) => {
        updateRiskLabel(parseInt(e.target.value, 10));
    });

    // Save config to local storage
    saveButton.addEventListener('click', () => {
        const prompt = textarea.value.trim();
        const risk = parseInt(riskSlider.value, 10);

        chrome.storage.local.set({
            userCustomPrompt: prompt,
            riskLevel: risk
        }, () => {
            statusElement.textContent = 'Configuration saved!';
            setTimeout(() => {
                statusElement.textContent = 'Post Guardian is active!';
            }, 2000);
        });
    });

    // Trigger analysis
    analyzeBtn.addEventListener('click', () => {
        chrome.runtime.sendMessage({ type: 'ANALYZE_VIDEO' }, (response) => {
            if (response.success) {
                resultDisplay.innerText = JSON.stringify(response.analysis, null, 2);
            } else {
                resultDisplay.innerText = "Error: " + response.error;
            }
        });
    });

    // Label formatter
    function updateRiskLabel(value) {
        let label = '';
        switch (value) {
            case 1: label = '1 - Very Lenient'; break;
            case 2: label = '2 - Lenient'; break;
            case 3: label = '3 - Balanced'; break;
            case 4: label = '4 - Strict'; break;
            case 5: label = '5 - Very Strict'; break;
            default: label = `${value}`; break;
        }
        riskLabel.textContent = label;
    }
});
