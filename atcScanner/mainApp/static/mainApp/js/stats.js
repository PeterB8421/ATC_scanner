document.addEventListener("DOMContentLoaded", async function() {
    const errorContainer = document.getElementById('errors');
    errorContainer.innerHTML = '';
    try {
        const response = await fetch('/api/stats');

        // Explicitly check if the server returned a 4xx or 5xx error
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Input file deletion reason chart
        const ctxDeletions = document.getElementById('deletionsChart').getContext('2d');
        new Chart(ctxDeletions, {
            type: 'doughnut',
            data: {
                labels: data.deletions.labels,
                datasets: [{
                    data: data.deletions.data,
                    backgroundColor: [
                        '#dc3545', // Danger Red
                        '#fd7e14', // Orange
                        '#ffc107', // Warning Yellow
                        '#6c757d', // Secondary Gray
                        '#0dcaf0'  // Info Blue
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });

        // Total recordings per day and avg SNR
        const ctxTimeline = document.getElementById('timelineChart').getContext('2d');
        new Chart(ctxTimeline, {
            type: 'bar',
            data: {
                labels: data.timeline.labels,
                datasets: [
                    {
                        label: 'Average SNR (dB)',
                        type: 'line',         // Override type to line
                        data: data.timeline.snr,
                        borderColor: '#198754',
                        backgroundColor: '#198754',
                        borderWidth: 2,
                        tension: 0.3,
                        yAxisID: 'y-snr'
                    },
                    {
                        label: 'Total Recordings',
                        type: 'bar',
                        data: data.timeline.volume,
                        backgroundColor: 'rgba(13, 110, 253, 0.7)',
                        yAxisID: 'y-volume'
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    'y-volume': {
                        type: 'linear',
                        position: 'left',
                        title: { display: true, text: 'Recordings Count' },
                        beginAtZero: true
                    },
                    'y-snr': {
                        type: 'linear',
                        position: 'right',
                        title: { display: true, text: 'SNR (dB)' },
                        grid: { drawOnChartArea: false }, // Prevent grid lines from overlapping
                        beginAtZero: true
                    }
                }
            }
        });

    } catch (error) {
        console.error("Failed to load statistics:", error);
        errorContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show shadow-sm mt-3" role="alert">
                There was an error while loading statistics data.
            </div>
        `;
    }
});
