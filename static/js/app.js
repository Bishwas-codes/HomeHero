// Global Application JS Helpers

document.addEventListener('DOMContentLoaded', () => {
    // Auto dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // Handle Demo Location Dropdown Selector in Booking & Registration Forms
    const locationSelect = document.getElementById('demo-location-select');
    if (locationSelect) {
        locationSelect.addEventListener('change', function() {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption && selectedOption.value) {
                const lat = selectedOption.getAttribute('data-lat');
                const lng = selectedOption.getAttribute('data-lng');
                const name = selectedOption.getAttribute('data-name');
                
                const latInput = document.getElementById('latitude-input');
                const lngInput = document.getElementById('longitude-input');
                const locNameInput = document.getElementById('location-name-input');
                const addressInput = document.getElementById('address-input');

                if (latInput) latInput.value = lat;
                if (lngInput) lngInput.value = lng;
                if (locNameInput) locNameInput.value = name;
                if (addressInput && !addressInput.value) {
                    addressInput.value = name;
                }
            }
        });
    }

    // Handle "Use My Current GPS" button if available
    const gpsBtn = document.getElementById('btn-get-gps');
    if (gpsBtn) {
        gpsBtn.addEventListener('click', function() {
            if (navigator.geolocation) {
                gpsBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i> Detecting GPS...';
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        const lat = position.coords.latitude.toFixed(4);
                        const lng = position.coords.longitude.toFixed(4);
                        
                        const latInput = document.getElementById('latitude-input');
                        const lngInput = document.getElementById('longitude-input');
                        const locNameInput = document.getElementById('location-name-input');

                        if (latInput) latInput.value = lat;
                        if (lngInput) lngInput.value = lng;
                        if (locNameInput) locNameInput.value = `Current Location (${lat}, ${lng})`;

                        gpsBtn.innerHTML = '<i class="fa-solid fa-check text-success me-1"></i> GPS Detected';
                    },
                    (error) => {
                        alert('Could not retrieve GPS coordinates. Please select a preset demo location from the dropdown.');
                        gpsBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs me-1"></i> Use My GPS';
                    }
                );
            } else {
                alert('Geolocation is not supported by your browser.');
            }
        });
    }
});
