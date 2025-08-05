const CHART_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6'];

function doughnutChart(id, labels, data, colors) {
    const el = document.getElementById(id);
    if (!el) return;
    new Chart(el, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: colors || CHART_COLORS, borderWidth: 0 }] },
        options: { maintainAspectRatio: false, cutout: '60%', plugins: { legend: { position: 'bottom' } } },
    });
}

function barChart(id, labels, datasets) {
    const el = document.getElementById(id);
    if (!el) return;
    datasets.forEach((d, i) => { d.backgroundColor = d.backgroundColor || CHART_COLORS[i]; d.borderRadius = 6; });
    new Chart(el, {
        type: 'bar',
        data: { labels, datasets },
        options: {
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: {
                y: { beginAtZero: true },
                // Second axis on the right when one dataset has a different unit (e.g. rupees).
                ...(datasets.some(d => d.yAxisID === 'y1') && { y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false } } }),
            },
        },
    });
}
