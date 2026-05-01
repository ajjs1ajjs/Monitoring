/**
 * Monitoring Dashboard - Main JavaScript
 *
 * Features:
 * - Theme toggling (dark/light mode)
 * - Mobile menu navigation
 * - Interactive chart rendering with Chart.js
 * - Data polling for live updates
 * - Responsive layout adjustments
 */

(function() {
    'use strict';

    // ========================================
    // DOM Elements Cache
    // ========================================
    const elements = {
        header: document.getElementById('main-header'),
        themeToggle: document.getElementById('theme-toggle'),
        mobileMenuToggle: document.getElementById('mobile-menu-toggle'),
        dashboardGrid: document.getElementById('dashboard-grid')
    };

    // ========================================
    // Theme Management
    // ========================================
    let currentTheme = 'light'; // default

    /**
     * Initialize theme from localStorage or system preference
     */
    function initTheme() {
        const savedTheme = localStorage.getItem('monitoring_theme');
        if (savedTheme) {
            setTheme(savedTheme);
        } else {
            // Detect system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            setTheme(prefersDark ? 'dark' : 'light');
        }

        // Listen for system theme changes (for users who don't save their choice)
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
            if (!localStorage.getItem('monitoring_theme')) {
                setTheme(e.matches ? 'dark' : 'light');
            }
        });
    }

    /**
     * Set theme and update DOM
     */
    function setTheme(theme) {
        currentTheme = theme;

        // Update root attribute for CSS custom properties
        document.documentElement.setAttribute('data-theme', theme);

        // Toggle icons
        const sunIcon = elements.themeToggle?.querySelector('.sun-icon');
        const moonIcon = elements.themeToggle?.querySelector('.moon-icon');

        if (theme === 'dark') {
            sunIcon.style.display = 'none';
            moonIcon.style.display = 'block';
            document.documentElement.style.setProperty('root', '--bg-primary: #1e1e1e');
        } else {
            sunIcon.style.display = 'block';
            moonIcon.style.display = 'none';
            document.documentElement.style.setProperty('root', '--bg-primary: #f8f9fa');
        }

        // Save preference
        if (elements.themeToggle) {
            localStorage.setItem('monitoring_theme', theme);

            // Update meta tag for mobile browsers
            const metaTheme = document.querySelector('meta[name="theme-color"]');
            if (metaTheme) {
                metaTheme.setAttribute(
                    'data-' + (theme === 'light' ? 'light' : 'dark'),
                    theme === 'light' ? '#ffffff' : '#1e1e1e'
                );
            }
        }

        // Dispatch custom event for other components
        document.dispatchEvent(new CustomEvent('theme:change', { detail: { theme } }));
    }

    /**
     * Theme toggle button handler
     */
    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', () => {
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }

    // ========================================
    // Mobile Menu Handling
    // ========================================
    /**
     * Toggle mobile menu (simplified - in real app would have a dropdown)
     */
    if (elements.mobileMenuToggle && elements.header) {
        const isMobile = window.innerWidth <= 991;

        if (isMobile) {
            // For simplicity, this toggles header visibility on mobile
            elements.mobileMenuToggle.addEventListener('click', () => {
                elements.header.style.display =
                    elements.header.style.display === 'none' ? 'flex' : 'none';

                // Animate hamburger icon transformation
                const bar = elements.mobileMenuToggle.querySelector('.icon-bars');
                if (bar) {
                    bar.style.transform =
                        elements.header.style.display === 'none' ? 'rotate(45deg)' : '';
                }
            });

            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                const isClickInsideHeader = elements.header.contains(e.target);
                const isClickOnToggle = elements.mobileMenuToggle.contains(e.target);

                if (!isClickInsideHeader && !isClickOnToggle && window.innerWidth <= 991) {
                    elements.header.style.display = 'none';
                    const bar = elements.mobileMenuToggle.querySelector('.icon-bars');
                    if (bar) {
                        bar.style.transform = '';
                    }
                }
            });

            // Close on escape key
            document.addEventListener('keydown', e => {
                if (e.key === 'Escape' && window.innerWidth <= 991) {
                    elements.header.style.display = 'none';
                    const bar = elements.mobileMenuToggle.querySelector('.icon-bars');
                    if (bar) {
                        bar.style.transform = '';
                    }
                }
            });
        }

        // Prevent header from being scrollable on mobile
        if (isMobile && window.getComputedStyle(elements.header).position === 'fixed') {
            elements.header.style.position = 'sticky';
            elements.header.style.top = '0';
        }
    }

    // ========================================
    // Chart.js Integration
    // ========================================
    const charts = {}; // Store chart instances by ID

    /**
     * Create a line chart with given configuration
     */
    function createLineChart(canvasId, config) {
        return new Chart(document.getElementById(canvasId), {
            type: 'line',
            data: config.data,
            options: Object.assign({
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: config.legend !== false },
                    tooltip: {
                        enabled: true,
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('uk-UA', {
                                        style: 'decimal',
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 6
                                    }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    },
                    annotation: {
                        // Add annotations if needed
                    }
                },
                scales: config.scales || {
                    x: {
                        grid: { display: false, drawBorder: false },
                        ticks: { maxTicksLimit: 8 }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.1)' },
                        ticks: { callback: formatYAxisValue }
                    }
                },
                elements: {
                    point: {
                        radius: 3,
                        hoverRadius: 6,
                        hitRadius: 10,
                        backgroundColor: config.pointBackgroundColor || 'rgba(102, 126, 234, 1)'
                    },
                    line: {
                        tension: 0.3, // Smooth curves
                        borderWidth: 2,
                        borderColor: config.backgroundColor || getComputedStyle(document.documentElement).getPropertyValue('--chart-primary').trim(),
                        fill: false
                    }
                }
            }, config.options),
            data: config.data
        });
    }

    /**
     * Create a bar chart
     */
    function createBarChart(canvasId, config) {
        return new Chart(document.getElementById(canvasId), {
            type: 'bar',
            data: config.data,
            options: Object.assign({
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: config.legend !== false } },
                scales: config.scales || {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true }
                },
                elements: { bar: { borderRadius: 4, borderSkipped: false } }
            }, config.options),
            data: config.data
        });
    }

    /**
     * Create a doughnut chart (for metrics distribution)
     */
    function createDoughnutChart(canvasId, config) {
        return new Chart(document.getElementById(canvasId), {
            type: 'doughnut',
            data: config.data,
            options: Object.assign({
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                let fullLabel = `${label}: ${Math.round(value * 100)}%`;

                                if (context.dataset.data.length > 0) {
                                    const total = context.dataset.total ||
                                               context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    fullLabel += ` (${percentage}%)`;
                                }
                                return fullLabel;
                            }
                        }
                    }
                },
                cutout: '70%', // Thickness of the ring
            }, config.options),
            data: config.data
        });
    }

    /**
     * Create a radar chart (for performance metrics)
     */
    function createRadarChart(canvasId, config) {
        return new Chart(document.getElementById(canvasId), {
            type: 'radar',
            data: config.data,
            options: Object.assign({
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'top' } },
                scales: {
                    r: {
                        angleLines: { display: true, color: 'rgba(0,0,0,0.1)' },
                        grid: { color: 'rgba(0,0,0,0.1)' },
                        pointLabels: { font: { size: 12 } }
                    }
                }
            }, config.options),
            data: config.data
        });
    }

    /**
     * Format Y-axis value for readability (K, M, B)
     */
    function formatYAxisValue(value) {
        if (!value || value === 0) return '0';

        const units = ['', ' K', 'M', 'B'];
        let num = value;
        let unitIndex = 0;

        while (Math.abs(num) >= 1000 && unitIndex < units.length - 1) {
            num /= 1000;
            unitIndex++;
        }

        return `${num.toFixed(2)}${units[unitIndex]}`.replace(/\s/g, '');
    }

    // ========================================
    // Data Polling & Updates
    // ========================================
    /**
     * Simulate data fetching (replace with real API calls)
     */
    function fetchDashboardData() {
        return Promise.resolve({
            metrics: [
                { id: 'cpu', label: 'CPU Usage (%)', color: '#e17055', data: generateRandomData(24, 30, 60), timestamp: Date.now() },
                { id: 'memory', label: 'Memory (%)', color: '#fdcb6e', data: generateRandomData(24, 40, 80), timestamp: Date.now() },
                { id: 'disk', label: 'Disk I/O (MB/s)', color: '#74b9ff', data: generateRandomData(24, 50, 150), timestamp: Date.now() }
            ],
            stats: [
                { value: Math.floor(Math.random() * 100), label: 'Active Users' },
                { value: Math.floor(Math.random() * 50), label: 'Requests/Sec' }
            ]
        });
    }

    /**
     * Generate random time-series data for charts
     */
    function generateRandomData(hours, minVal, maxVal) {
        const points = [];
        let previousValue = Math.floor((minVal + maxVal) / 2);

        // Create smooth curve with occasional spikes
        for (let i = 0; i < hours * 4; i++) {
            const change = Math.random() * (maxVal - minVal) - (maxVal - minVal) / 2;
            previousValue += change;

            // Clamp to valid range
            previousValue = Math.max(minVal, Math.min(maxVal, previousValue));

            points.push({
                x: i / 4, // Convert to hours
                y: Number(previousValue.toFixed(1))
            });
        }

        return points;
    }

    /**
     * Initialize all charts in the DOM
     */
    function initCharts() {
        // Check for chart containers with data-attributes
        const chartContainers = document.querySelectorAll('[data-chart]');

        chartContainers.forEach(container => {
            const type = container.dataset.chart; // line, bar, doughnut, radar
            let config = {};

            if (type === 'line') {
                config = {
                    id: `chart-${container.id}`,
                    data: {
                        labels: [],
                        datasets: [{}]
                    },
                    legend: true,
                    scales: {}
                };

                // Parse attributes from container
                const colors = container.dataset.colors?.split(',');
                if (colors) {
                    config.data.datasets[0].backgroundColor = colors;
                    config.data.datasets[0].borderColor = colors.map(c =>
                        c.replace('#', '').match(/.{1,2}/g).join('') + '80' // Add transparency
                    );
                }

                const pointRadius = container.dataset.pointRadius || 4;
                config.data.datasets[0].pointRadius = parseInt(pointRadius);

                // Create chart
                charts[container.id] = createLineChart(container.id, config);
            } else if (type === 'bar') {
                config = {
                    id: `chart-${container.id}`,
                    data: {},
                    legend: true
                };

                const labels = container.dataset.labels?.split(',');
                if (labels) {
                    config.data.labels = labels;
                    const values = container.dataset.values?.split(',').map(Number);
                    if (values) {
                        config.data.datasets = [{
                            data: values,
                            backgroundColor: container.dataset.color || '#667eea'
                        }];
                    }
                }

                charts[container.id] = createBarChart(container.id, config);
            } else if (type === 'doughnut') {
                config = {
                    id: `chart-${container.id}`,
                    data: {},
                    legend: true
                };

                const labels = container.dataset.labels?.split(',');
                const values = container.dataset.values?.split(',').map(Number);

                if (labels && values) {
                    config.data.labels = labels;
                    config.data.datasets = [{
                        data: values,
                        backgroundColor: ['#e17055', '#fdcb6e', '#74b9ff', '#a29bfe']
                    }];
                }

                charts[container.id] = createDoughnutChart(container.id, config);
            } else if (type === 'radar') {
                // Similar implementation for radar charts
                console.warn('Radar chart support not fully implemented in this demo');
            }
        });
    }

    /**
     * Update live data in charts every 5 seconds
     */
    function updateLiveCharts() {
        const newMetrics = fetchDashboardData().then(data => {

            // Update line chart datasets if they exist
            document.querySelectorAll('[data-chart="line"]').forEach(container => {
                if (charts[container.id]) {
                    charts[container.id].data.datasets.forEach((dataset, index) => {
                        const oldPoints = dataset.data;

                        // Create new points with updated values
                        const newPoints = [];
                        for (let i = 0; i < Math.min(oldPoints.length - 1, data.metrics[index]?.data?.length || 0); i++) {
                            newPoints.push({
                                x: oldPoints[i + 1].x,
                                y: Number(data.metrics[index]?.data[i]?.y.toFixed(1))
                            });
                        }

                        // Add current point
                        const lastX = oldPoints[oldPoints.length - 1].x;
                        newPoints.push({
                            x: lastX + 0.25, // Next time slot (4 points per hour)
                            y: data.metrics[index]?.data[data.metrics[index]?.data?.length - 1]?.y || 0
                        });

                        dataset.data = newPoints;

                        // Update tooltip label
                        if (container.dataset.label) {
                            chartInstance.plugins.tooltip.update({
                                title: container.dataset.label,
                                labels: [{ value: data.metrics[index].timestamp }],
                                body: [{ content: 'Updated: ' + new Date(data.metrics[index].timestamp).toLocaleTimeString() }]
                            });
                        }
                    });

                    // Auto-resize chart to maintain aspect ratio
                    charts[container.id].resize();
                }
            });
        });

        return newMetrics;
    }

    // ========================================
    // Initialization
    // ========================================
    function init() {
        console.log('Monitoring Dashboard JS initialized');

        // Initialize theme
        initTheme();

        // Wait for DOM to be fully loaded, then initialize charts
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initCharts);
        } else {
            requestAnimationFrame(initCharts);
        }

        // Set up live updates every 5 seconds
        setInterval(updateLiveCharts, 5000);

        // Handle window resize for responsive charts
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);

            // Debounce resize events to avoid excessive chart resizing
            resizeTimeout = setTimeout(() => {
                Object.values(charts).forEach(chart => {
                    if (chart) {
                        chart.resize();
                    }
                });
            }, 150);
        });

        // Accessibility: announce theme change to screen readers
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('role', 'status');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.style.position = 'absolute';
        liveRegion.style.clip = 'rect(0, 0, 0, 0)';
        liveRegion.style.overflow = 'hidden';

        document.body.appendChild(liveRegion);

        if (elements.themeToggle) {
            elements.themeToggle.addEventListener('keydown', e => {
                // Add keyboard support for theme toggle
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setTheme(currentTheme === 'light' ? 'dark' : 'light');
                    liveRegion.textContent = `Theme changed to ${currentTheme === 'light' ? 'dark' : 'light'} mode`;
                }
            });
        }

        // Add custom CSS for chart tooltips in dark theme
        const style = document.createElement('style');
        style.textContent = `
            .chartjs-tooltip {
                opacity: 0.9;
                border-radius: var(--spacing-sm);
                box-shadow: var(--shadow-md);
                font-family: var(--font-family-sans) !important;
                color: var(--text-primary);
                background-color: var(--bg-card);
            }

            .chartjs-tooltip-body {
                padding-bottom: 0.5em;
            }
        `;
        document.head.appendChild(style);

        console.log('Monitoring Dashboard JS initialized');
    }

    // Run initialization when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        requestAnimationFrame(init);
    }

})();
