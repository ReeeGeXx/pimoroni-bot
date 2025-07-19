document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    document.getElementById('uploadStatus').textContent = 'Uploading...';
    const res = await fetch('/upload', {
        method: 'POST',
        body: formData
    });
    const data = await res.json();
    if (data.path) {
        document.getElementById('uploadStatus').textContent = 'Upload successful!';
        document.getElementById('videoPathInput').value = data.path;
    } else {
        document.getElementById('uploadStatus').textContent = 'Upload failed: ' + (data.error || 'Unknown error');
    }
});

document.getElementById('searchForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const query = this.query.value;
    const video_path = this.video_path.value;
    document.getElementById('searchResults').textContent = 'Processing (search & analysis)...';
    const res = await fetch('/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, video_path })
    });
    const data = await res.json();
    let output = '';
    if (data.results) {
        output += '<h3>Marengo (Search) Results</h3>';
        output += '<pre>' + JSON.stringify(data.results.marengo, null, 2) + '</pre>';
        output += '<h3>Pegasus (Analyze) Results</h3>';
        output += '<pre>' + JSON.stringify(data.results.pegasus, null, 2) + '</pre>';
    } else {
        output = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
    }
    document.getElementById('searchResults').innerHTML = output;
});