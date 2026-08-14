// Live Radar feed polling for Worker Dashboard

function initWorkerLiveRadar() {
    const radarContainer = document.getElementById('incoming-requests-container');
    const emptyState = document.getElementById('no-requests-msg');
    const pollInterval = 4000; // Poll every 4 seconds

    function fetchIncoming() {
        // If worker currently has active job in DOM, don't poll radar
        if (document.getElementById('active-job-section')) {
            return;
        }

        fetch('/api/worker/incoming-requests')
            .then(res => res.json())
            .then(data => {
                if (data.has_active_job) {
                    window.location.reload();
                    return;
                }

                if (!radarContainer) return;

                const requests = data.requests || [];
                if (requests.length === 0) {
                    if (emptyState) emptyState.style.display = 'block';
                    radarContainer.innerHTML = '';
                    return;
                }

                if (emptyState) emptyState.style.display = 'none';

                let html = '';
                requests.forEach(r => {
                    html += `
                    <div class="incoming-request-card" id="req-card-${r.id}">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <span class="badge bg-primary me-2">${r.service_name}</span>
                                <span class="distance-badge"><i class="fa-solid fa-location-arrow"></i> ${r.distance_km} km away</span>
                            </div>
                            <span class="text-muted small"><i class="fa-regular fa-clock me-1"></i>${r.created_time}</span>
                        </div>
                        <h5 class="fw-bold mb-1">${r.title}</h5>
                        <p class="text-muted mb-2 small">${r.description}</p>
                        
                        <div class="d-flex align-items-center justify-content-between pt-2 border-top">
                            <div>
                                <span class="text-muted small">Area: <strong>${r.location_name}</strong></span><br>
                                <span class="text-success fw-bold">Est. Budget: ₹${r.budget}</span>
                            </div>
                            <div class="d-flex gap-2">
                                <form action="/worker/reject-request/${r.id}" method="POST" class="d-inline">
                                    <button type="submit" class="btn btn-sm btn-outline-secondary">Decline</button>
                                </form>
                                <form action="/worker/accept-request/${r.id}" method="POST" class="d-inline">
                                    <button type="submit" class="btn btn-sm btn-success fw-bold px-3">
                                        <i class="fa-solid fa-check me-1"></i> Accept Job
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                    `;
                });

                radarContainer.innerHTML = html;
            })
            .catch(err => console.error('Worker radar polling error:', err));
    }

    setInterval(fetchIncoming, pollInterval);
}
