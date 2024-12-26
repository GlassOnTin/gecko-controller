import LiveDisplay from './components/LiveDisplay.jsx';
import StatusMonitor from './components/StatusMonitor.jsx';

// Configuration Management
class ConfigManager {
    static async loadConfig() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            this.updateFormFields(config);
        } catch (error) {
            console.error('Error loading config:', error);
            this.showStatus('Error loading configuration: ' + error.message, 'error');
        }
    }

    static updateFormFields(config) {
        // Temperature settings
        document.getElementById('MIN_TEMP').value = config.MIN_TEMP;
        document.getElementById('DAY_TEMP').value = config.DAY_TEMP;
        document.getElementById('TEMP_TOLERANCE').value = config.TEMP_TOLERANCE;

        // Lighting schedule
        document.getElementById('LIGHT_ON_TIME').value = config.LIGHT_ON_TIME;
        document.getElementById('LIGHT_OFF_TIME').value = config.LIGHT_OFF_TIME;

        // UV Thresholds
        document.getElementById('UVA_THRESHOLDS_low').value = config.UVA_THRESHOLDS.low;
        document.getElementById('UVA_THRESHOLDS_high').value = config.UVA_THRESHOLDS.high;
        document.getElementById('UVB_THRESHOLDS_low').value = config.UVB_THRESHOLDS.low;
        document.getElementById('UVB_THRESHOLDS_high').value = config.UVB_THRESHOLDS.high;

        // UV Sensor Configuration
        document.getElementById('SENSOR_HEIGHT').value = config.SENSOR_HEIGHT;
        document.getElementById('LAMP_DIST_FROM_BACK').value = config.LAMP_DIST_FROM_BACK;
        document.getElementById('ENCLOSURE_HEIGHT').value = config.ENCLOSURE_HEIGHT;
        document.getElementById('SENSOR_ANGLE').value = config.SENSOR_ANGLE;

        // Hardware Configuration
        const displayAddressInput = document.getElementById('DISPLAY_ADDRESS');
        displayAddressInput.value = this.formatI2CAddress(config.DISPLAY_ADDRESS);
        document.getElementById('DISPLAY_RESET').value = config.DISPLAY_RESET;
        document.getElementById('LIGHT_RELAY').value = config.LIGHT_RELAY;
        document.getElementById('HEAT_RELAY').value = config.HEAT_RELAY;
    }

    static formatI2CAddress(input) {
        let value = String(input).replace(/^0x/i, '').replace(/\s/g, '');
        value = value.replace(/[^0-9A-Fa-f]/g, '').slice(0, 2);
        return value ? `0x${value.toLowerCase()}` : '';
    }

    static showStatus(message, type) {
        const status = document.getElementById('status');
        status.textContent = message;
        status.className = `status ${type}`;
        status.style.display = 'block';
        setTimeout(() => status.style.display = 'none', 3000);
    }

    static async saveConfig(formData) {
        const config = {};

        for (const [key, value] of formData.entries()) {
            if (key.includes('.')) {
                const [mainKey, subKey] = key.split('.');
                if (!config[mainKey]) {
                    config[mainKey] = {};
                }
                config[mainKey][subKey] = parseFloat(value);
            } else if (key === 'DISPLAY_ADDRESS') {
                config[key] = parseInt(value, 16);
            } else if (document.getElementById(key).type === 'number') {
                config[key] = parseFloat(value);
            } else {
                config[key] = value;
            }
        }

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(config),
            });

            const result = await response.json();
            this.showStatus(
                result.status === 'success'
                ? 'Settings saved successfully!'
                : 'Error saving settings: ' + result.message,
                result.status === 'success' ? 'success' : 'error'
            );
        } catch (error) {
            console.error('Error:', error);
            this.showStatus('Error saving settings: ' + error.message, 'error');
        }
    }
}

// Chart Management
class ChartManager {
    static tempHumidityChart = null;
    static uvChart = null;

    static initializeCharts() {
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }

        // Register required Chart.js components
        Chart.register(
            Chart.LineController,
            Chart.LineElement,
            Chart.PointElement,
            Chart.LinearScale,
            Chart.CategoryScale,
            Chart.Legend,
            Chart.Tooltip
        );

        this.initializeTempHumidityChart();
        this.initializeUVChart();
    }

    static initializeTempHumidityChart() {
        const ctx = document.getElementById('tempHumidityChart');
        if (!ctx) return;

        this.tempHumidityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Temperature (°C)',
                                           borderColor: 'rgb(255, 99, 132)',
                                           yAxisID: 'y',
                                           tension: 0.1,
                                           data: []
                    },
                    {
                        label: 'Humidity (%)',
                                           borderColor: 'rgb(54, 162, 235)',
                                           yAxisID: 'y1',
                                           tension: 0.1,
                                           data: []
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        type: 'category',
                        display: true
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }

    static initializeUVChart() {
        const ctx = document.getElementById('uvChart');
        if (!ctx) return;

        this.uvChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'UVA (μW/cm²)',
                                 borderColor: 'rgb(255, 159, 64)',
                                 yAxisID: 'y',
                                 tension: 0.1,
                                 data: []
                    },
                    {
                        label: 'UVB (μW/cm²)',
                                 borderColor: 'rgb(75, 192, 192)',
                                 yAxisID: 'y1',
                                 tension: 0.1,
                                 data: []
                    },
                    {
                        label: 'UVC (μW/cm²)',
                                 borderColor: 'rgb(153, 102, 255)',
                                 yAxisID: 'y1',
                                 tension: 0.1,
                                 data: []
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        type: 'category',
                        display: true
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'UVA (μW/cm²)'
                        },
                        beginAtZero: true,
                        min: 0,
                        suggestedMax: 200
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'UVB/UVC (μW/cm²)'
                        },
                        beginAtZero: true,
                        min: 0,
                        suggestedMax: 10,
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }

    static async updateCharts() {
        try {
            const response = await fetch('/api/logs');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (this.tempHumidityChart) {
                this.tempHumidityChart.data.labels = data.timestamps;
                this.tempHumidityChart.data.datasets[0].data = data.temperature;
                this.tempHumidityChart.data.datasets[1].data = data.humidity;
                this.tempHumidityChart.update();
            }

            if (this.uvChart) {
                this.uvChart.data.labels = data.timestamps;
                this.uvChart.data.datasets[0].data = data.uva;
                this.uvChart.data.datasets[1].data = data.uvb;
                this.uvChart.data.datasets[2].data = data.uvc;
                this.uvChart.update();
            }
        } catch (error) {
            console.error('Error updating charts:', error);
        }
    }
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Charts
    ChartManager.initializeCharts();
    ChartManager.updateCharts();
    setInterval(() => ChartManager.updateCharts(), 60000);

    // Load Configuration
    ConfigManager.loadConfig();

    // Initialize React Components
    const liveDisplayContainer = document.getElementById('liveDisplay');
    if (liveDisplayContainer) {
        ReactDOM.render(React.createElement(LiveDisplay), liveDisplayContainer);
    }

    const statusContainer = document.getElementById('statusContainer');
    if (statusContainer) {
        ReactDOM.render(React.createElement(StatusMonitor), statusContainer);
    }

    // Setup Form Handlers
    const configForm = document.getElementById('configForm');
    if (configForm) {
        configForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await ConfigManager.saveConfig(new FormData(e.target));
        });
    }

    // Setup I2C Address Formatting
    const i2cInput = document.getElementById('DISPLAY_ADDRESS');
    if (i2cInput) {
        i2cInput.addEventListener('change', () => {
            i2cInput.value = ConfigManager.formatI2CAddress(i2cInput.value);
        });
    }
});

// Prevent caching of API responses
fetch = (function(fetch) {
    return function(...args) {
        if (typeof args[0] === 'string' && args[0].startsWith('/api/')) {
            if (!args[1]) args[1] = {};
            if (!args[1].headers) args[1].headers = {};
            args[1].headers['Cache-Control'] = 'no-store, no-cache, must-revalidate';
            args[1].headers['Pragma'] = 'no-cache';
        }
        return fetch.apply(this, args);
    };
})(fetch);
