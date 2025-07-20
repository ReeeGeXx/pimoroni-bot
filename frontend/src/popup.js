// Popup script for Post Guardian extension
document.addEventListener('DOMContentLoaded', function () {
    console.log('Post Guardian popup loaded');

    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.textContent = 'Post Guardian is active!';
    }

    const textarea = document.getElementById('userPrompt');
    const saveButton = document.getElementById('savePrompt');

    if (textarea && saveButton) {
        // Load saved custom prompt
        chrome.storage.local.get(['userCustomPrompt'], (result) => {
            if (result.userCustomPrompt) {
                textarea.value = result.userCustomPrompt;
            }
        });

        // Save button click
        saveButton.addEventListener('click', () => {
            const prompt = textarea.value.trim();
            chrome.storage.local.set({ userCustomPrompt: prompt }, () => {
                statusElement.textContent = 'Custom instruction saved!';
                setTimeout(() => {
                    statusElement.textContent = 'Post Guardian is active!';
                }, 2000);
            });
        });
    }
    document.getElementById("analyzeBtn").addEventListener("click", () => {
        chrome.runtime.sendMessage({ type: 'ANALYZE_VIDEO' }, (response) => {
            if (response.success) {
                document.getElementById("result").innerText = JSON.stringify(response.analysis, null, 2);
            } else {
                document.getElementById("result").innerText = "Error: " + response.error;
            }
        });
    });
});
