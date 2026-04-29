/*
Author: Bc. Petr Balok
 */
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

        const ctxCombined = document.getElementById('totalFilesChart').getContext('2d');

        new Chart(ctxCombined, {
            type: 'bar',
            data: {
                // Two labels on the X-axis
                labels: ['Processed Files', 'Deleted Files'],

                datasets: [{
                    label: 'Total files',
                    // Pass BOTH numbers into a single array
                    data: [data.total.processed, data.total.deleted],

                    // Pass BOTH colors so the first bar is blue and the second is red
                    backgroundColor: [
                        'rgba(13, 110, 253, 0.8)', // Blue for Processed
                        'rgba(220, 53, 69, 0.8)'   // Red for Deleted
                    ],
                    borderColor: [
                        '#0d6efd',
                        '#dc3545'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false // Turn this off, the X-axis labels already explain it!
                    }
                }
            }
        });

        const ctxAirport = document.getElementById('recsPerCodeChart').getContext('2d');

        new Chart(ctxAirport, {
            type: 'bar',
            data: {
                labels: data.airports.airport_labels,
                datasets: [{
                    data: data.airports.airport_counts,

                    // A nice array of distinct Bootstrap-style colors for the slices
                    backgroundColor: [
                        'rgba(13, 110, 253, 0.8)',  // Primary Blue
                        'rgba(25, 135, 84, 0.8)',   // Success Green
                        'rgba(255, 193, 7, 0.8)',   // Warning Yellow
                        'rgba(220, 53, 69, 0.8)',   // Danger Red
                        'rgba(13, 202, 240, 0.8)',  // Info Cyan
                        'rgba(102, 16, 242, 0.8)'   // Indigo
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff' // Adds a clean white line between slices
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                // Adds a nice bounce effect when the page loads
                animation: {
                    animateScale: true,
                    animateRotate: true
                }
            }
        });

        const ctxDuration = document.getElementById('totalDurationChart').getContext('2d');

        new Chart(ctxDuration, {
            type: 'bar',
            data: {
                labels: data.duration.labels,
                datasets: [{
                    label: 'Total Audio (Hours)',
                    data: data.duration.duration,
                    backgroundColor: 'rgba(25, 135, 84, 0.8)',
                    borderColor: '#198754',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            // Just append "hrs" to whatever number Django sent
                            label: function(context) {
                                return `Total Time: ${context.parsed.y} hrs`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            // Just append "hrs" to the Y-axis numbers
                            callback: function(value) {
                                return value + ' hrs';
                            }
                        }
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
