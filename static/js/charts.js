/* MyMediFile - Chart.js Bindings & Configurations */

const HealthCharts = {
    // 1. Category Distribution (Pie/Doughnut)
    renderCategoryChart(canvasId, labels, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#0F4C81', // Deep Blue
                        '#2EC4B6', // Teal
                        '#4CAF50', // Green
                        '#F59E0B', // Amber
                        '#F43F5E', // Rose
                        '#8B5CF6', // Purple
                        '#64748B'  // Slate
                    ],
                    borderWidth: 2,
                    borderColor: getComputedStyle(document.documentElement).getPropertyValue('--bg-secondary')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary'),
                            font: { family: 'Inter', size: 11 }
                        }
                    }
                }
            }
        });
    },

    // 2. Monthly Activities (Bar)
    renderActivityChart(canvasId, labels, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Entries Created',
                    data: data,
                    backgroundColor: '#2EC4B6',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted') },
                        grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--border-color') }
                    },
                    x: {
                        ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted') },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    },

    // 3. Vaccination Progress (Doughnut)
    renderVaccinationProgress(canvasId, taken, due) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Upcoming/Due'],
                datasets: [{
                    data: [taken, due],
                    backgroundColor: ['#4CAF50', '#F59E0B'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12 } }
                }
            }
        });
    },

    // 4. Vitals Trend (Line)
    renderTrendChart(canvasId, labels, datasets) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        
        const chartDatasets = datasets.map(ds => ({
            label: ds.label,
            data: ds.data,
            borderColor: ds.color || '#0F4C81',
            backgroundColor: ds.bgColor || 'transparent',
            tension: 0.3,
            fill: !!ds.bgColor,
            pointBackgroundColor: ds.color || '#0F4C81'
        }));

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: chartDatasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted') },
                        grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--border-color') }
                    },
                    x: {
                        ticks: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-muted') },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: getComputedStyle(document.documentElement).getPropertyValue('--text-primary') }
                    }
                }
            }
        });
    }
};
