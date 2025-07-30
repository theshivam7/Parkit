// Charts Configuration and Initialization
function initializeAdminCharts(occupancyData, statsData) {
    try {
        // Occupancy Doughnut Chart
        const occupancyCtx = document.getElementById('occupancyChart');
        if (occupancyCtx && occupancyData) {
            new Chart(occupancyCtx, {
            type: 'doughnut',
            data: {
                labels: ['Occupied', 'Available'],
                datasets: [{
                    data: [occupancyData.occupied, occupancyData.available],
                    backgroundColor: [
                        '#f59e0b', // warning color
                        '#22c55e'  // success color
                    ],
                    borderWidth: 0,
                    cutout: '60%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Statistics Bar Chart
    const statsCtx = document.getElementById('statsChart');
    if (statsCtx && statsData) {
        new Chart(statsCtx, {
            type: 'bar',
            data: {
                labels: ['Parking Lots', 'Users', 'Active Reservations'],
                datasets: [{
                    label: 'Count',
                    data: [statsData.lots, statsData.users, statsData.reservations],
                    backgroundColor: [
                        '#3b82f6', // primary
                        '#22c55e', // success
                        '#f59e0b'  // warning
                    ],
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        titleFont: {
                            size: 14
                        },
                        bodyFont: {
                            size: 13
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    } catch (error) {
        console.error('Error initializing admin charts:', error);
    }
}

// User Dashboard Charts
function initializeUserCharts(userData) {
    try {
        const userStatsCtx = document.getElementById('userStatsChart');
        if (userStatsCtx && userData) {
        new Chart(userStatsCtx, {
            type: 'line',
            data: {
                labels: userData.months,
                datasets: [{
                    label: 'Monthly Spending',
                    data: userData.spending,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                return `Spent: ₹${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value;
                            },
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            font: {
                                size: 12
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    } catch (error) {
        console.error('Error initializing user charts:', error);
    }
}

// Real-time chart updates
function updateChartData(chartId, newData) {
    try {
        const chart = Chart.getChart(chartId);
        if (chart && newData && Array.isArray(newData)) {
            chart.data.datasets[0].data = newData;
            chart.update('active');
        }
    } catch (error) {
        console.error('Error updating chart:', error);
    }
}

// Auto-refresh charts every 30 seconds for admin dashboard
if (window.location.pathname.includes('/admin')) {
    setInterval(() => {
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data && !data.error) {
                    // Update occupancy chart
                    updateChartData('occupancyChart', [data.occupied_spots || 0, (data.total_spots || 0) - (data.occupied_spots || 0)]);
                    
                    // Update stats chart
                    updateChartData('statsChart', [data.total_lots || 0, data.total_users || 0, data.active_reservations || 0]);
                }
            })
            .catch(error => console.log('Chart refresh failed:', error));
    }, 30000);
}

// Chart.js default configuration
Chart.defaults.font.family = "'Inter', system-ui, -apple-system, sans-serif";
Chart.defaults.font.size = 13;
Chart.defaults.color = '#64748b';
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;
