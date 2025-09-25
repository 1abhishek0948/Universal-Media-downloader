document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('download-form');
    const urlInput = document.getElementById('media-url');
    const resultsSection = document.getElementById('results-section');
    const loadingDiv = document.getElementById('loading');
    const errorMessageDiv = document.getElementById('error-message');
    const mediaDetailsDiv = document.getElementById('media-details');
    const mediaTypeSelector = document.getElementById('media-type-selector');
    const downloadProgressDiv = document.getElementById('download-progress');
    const downloadSpeedText = document.getElementById('download-speed-text');
    const downloadStatusSpan = document.getElementById('download-status');
    const downloadSpinner = document.querySelector('.download-spinner');

    let selectedType = 'video';

    mediaTypeSelector.addEventListener('click', (e) => {
        if (e.target.classList.contains('media-btn')) {
            selectedType = e.target.dataset.type;
            let placeholderText;
            switch(selectedType) {
                case 'video':
                    placeholderText = 'Paste Video URL here';
                    break;
                case 'audio':
                    placeholderText = 'Paste Audio URL here';
                    break;
                case 'image':
                    placeholderText = 'Paste Image URL here';
                    break;
                case 'playlist':
                    placeholderText = 'Paste YouTube Playlist URL here';
                    break;
                default:
                    placeholderText = 'Paste URL here';
            }
            urlInput.placeholder = placeholderText;
            document.querySelectorAll('.media-btn').forEach(btn => {
                btn.classList.remove('btn-primary-custom', 'btn-outline-secondary');
                if (btn === e.target) {
                    btn.classList.add('btn-primary-custom');
                } else {
                    btn.classList.add('btn-outline-secondary');
                }
            });
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const mediaUrl = urlInput.value.trim();
        if (!mediaUrl) { showError('Please enter a URL.'); return; }
        
        resetUIState(true);

        try {
            const response = await fetch('/get_media_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: mediaUrl }),
            });
            if (!response.ok) throw new Error((await response.json()).error || 'Failed to fetch media details.');
            const data = await response.json();
            displayMediaDetails(data, mediaUrl);
            
        } catch (error) { showError(error.message); }
        finally { loadingDiv.classList.add('d-none'); }
    });

    function resetUIState(showResultsSection = false) {
        hideError();
        mediaDetailsDiv.classList.add('d-none');
        mediaDetailsDiv.innerHTML = '';
        downloadProgressDiv.classList.add('d-none');
        if (showResultsSection) {
            resultsSection.classList.remove('d-none');
            loadingDiv.classList.remove('d-none');
        } else {
            resultsSection.classList.add('d-none');
        }
    }

    function displayMediaDetails(data, mediaUrl) {
        let detailsHtml = createVideoDetailsHtml(data);
        mediaDetailsDiv.innerHTML = detailsHtml;
        mediaDetailsDiv.classList.remove('d-none');
        document.querySelectorAll('.download-btn').forEach(button => {
            button.addEventListener('click', () => {
                triggerDownload(mediaUrl, button.dataset.formatId);
            });
        });
    }

    function createVideoDetailsHtml(data) {
        let formatsHtml = '';
        const qualityOrder = ['Best Quality', '4K', '2K', '1080p', '720p', '480p', '360p', 'Best Quality (Audio)'];
        qualityOrder.forEach(quality => {
            if (data.formats[quality]) {
                const f = data.formats[quality];
                const size = f.filesize ? (f.filesize / 1024 / 1024).toFixed(2) + ' MB' : 'N/A';
                formatsHtml += `<li class="list-group-item d-flex justify-content-between align-items-center">
                    <div><strong>${quality}</strong> <span class="badge bg-secondary">${f.ext}</span></div>
                    <div><span class="me-3 text-muted">${size}</span>
                    <button class="btn btn-sm btn-success download-btn" data-format-id="${f.format_id}">Download</button></div>
                </li>`;
            }
        });
        if (!formatsHtml) formatsHtml = '<li class="list-group-item">No standard formats found.</li>';
        return `<div class="row align-items-center">
            <div class="col-md-4"><img src="${data.thumbnail}" class="img-fluid rounded shadow-sm"></div>
            <div class="col-md-8"><h4 class="fw-bold">${data.title}</h4><ul class="list-group">${formatsHtml}</ul></div>
        </div>`;
    }

    async function triggerDownload(mediaUrl, formatId = null) {
        mediaDetailsDiv.classList.add('d-none');
        downloadProgressDiv.classList.remove('d-none');
        downloadStatusSpan.textContent = 'Preparing download...';
        
        const startTime = Date.now();
        const interval = setInterval(() => {
            const elapsedTime = (Date.now() - startTime) / 1000;
            const speed = (2 + Math.sin(elapsedTime * 2) * 1.5).toFixed(2);
            downloadSpeedText.textContent = `${speed} MB/s`;
            downloadSpinner.classList.add('active'); // Add animation class
        }, 500);

        try {
            const response = await fetch('/download_media', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: mediaUrl, type: selectedType, format_id: formatId })
            });
            clearInterval(interval);
            downloadSpinner.classList.remove('active'); // Remove animation class
            const data = await response.json();
            if (response.ok && data.download_url) {
                downloadStatusSpan.textContent = 'Download complete. Redirecting...';
                downloadSpeedText.textContent = '100%';
                setTimeout(() => {
                    window.location.href = data.download_url;
                    resetUIState(false);
                    form.reset();
                }, 1000);
            } else {
                throw new Error(data.error || 'Failed to download media.');
            }
        } catch (error) {
            clearInterval(interval);
            downloadSpinner.classList.remove('active'); // Remove animation class
            showError(error.message);
            downloadProgressDiv.classList.add('d-none');
        }
    }

    function showError(msg) {
        errorMessageDiv.textContent = msg;
        errorMessageDiv.classList.remove('d-none');
        loadingDiv.classList.add('d-none');
    }
    function hideError() { errorMessageDiv.classList.add('d-none'); }
});