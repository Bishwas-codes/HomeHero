// Live status polling for Customer Tracking Screen

function initCustomerLiveTracking(requestId, initialStatus) {
    let currentStatus = initialStatus;
    const pollInterval = 3000; // Poll every 3 seconds

    function checkStatus() {
        // If already completed or cancelled, stop polling
        if (currentStatus === 'COMPLETED' || currentStatus === 'CANCELLED') {
            return;
        }

        fetch(`/api/request-status/${requestId}`)
            .then(response => {
                if (!response.ok) throw new Error('Network error');
                return response.json();
            })
            .then(data => {
                if (data.status && data.status !== currentStatus) {
                    console.log(`Status changed from ${currentStatus} to ${data.status}`);
                    currentStatus = data.status;
                    
                    // Reload page cleanly to update stepper, worker card, and actions
                    window.location.reload();
                }
            })
            .catch(err => console.error('Error polling request status:', err));
    }

    // Start periodic polling
    const timer = setInterval(checkStatus, pollInterval);
}
