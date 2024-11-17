// Declare chart variables globally so we can access them in updateCharts
let tempHumidityChart = null;
let uvChart = null;

console.log('Script loaded');

// Create status monitor container element and styling
const statusStyles = `
.status-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 1000;
}

.status-icon {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    transition: transform 0.2s ease;
}

.status-icon:hover {
    transform: scale(1.05);
}

.status-icon.running::after {
    content: '';
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #4CAF50;
    border: 2px solid white;
    box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.status-icon.stopped::after {
    content: '';
    position: absolute;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #f44336;
    border: 2px solid white;
    box-shadow: 0 0 0 2px rgba(244, 67, 54, 0.2);
}

.status-details-card {
    position: absolute;
    top: 50px;
    right: 0;
    width: 300px;
    background: white;
    border-radius: 8px;
    padding: 15px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: none;
    animation: fadeIn 0.2s ease;
}

.status-details-card.visible {
    display: block;
}

.status-details-card.running {
    border-left: 4px solid #4CAF50;
}

.status-details-card.stopped {
    border-left: 4px solid #f44336;
}

.status-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-weight: bold;
}

.status-details {
    font-size: 0.9em;
    color: #666;
    margin-top: 8px;
}

.status-timestamp {
    font-size: 0.8em;
    color: #999;
    margin-top: 5px;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Add pulse animation for initial attention */
@keyframes pulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.1); }
    100% { transform: scale(1); }
}

.status-icon.pulse {
    animation: pulse 2s ease infinite;
}
.status-controls {
    position: absolute;
    top: 5px;
    left: -95px;
    display: flex;
    flex-direction: row;
    gap: 10px;
}

.control-indicator {
    width: 35px;
    height: 35px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.control-indicator i {
    font-size: 18px;
    color: #666;
}

.control-indicator::after {
    content: '';
    position: absolute;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    bottom: 2px;
    right: 2px;
    border: 2px solid white;
}

.control-indicator.active::after {
    background: #4CAF50;
    box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.2);
}

.control-indicator.inactive::after {
    background: #666;
    box-shadow: 0 0 0 2px rgba(102, 102, 102, 0.2);
}

@keyframes fade {
    0% { opacity: 0.4; }
    50% { opacity: 1; }
    100% { opacity: 0.4; }
}

.control-indicator.active i {
    color: #ff9800;
    animation: fade 2s infinite;
}

.control-indicator .tooltip {
    position: absolute;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    white-space: nowrap;
    left: -100px;
    opacity: 0;
    transition: opacity 0.2s;
    pointer-events: none;
}

.control-indicator:hover .tooltip {
    opacity: 1;
}
`;

// Add styles to document
const styleSheet = document.createElement("style");
styleSheet.textContent = statusStyles;
document.head.appendChild(styleSheet);

// Status monitor functionality
let statusCheckInterval = null;

// Add these SVG icons for light and heat
const ICONS = {
    light: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"></circle>
        <line x1="12" y1="1" x2="12" y2="3"></line>
        <line x1="12" y1="21" x2="12" y2="23"></line>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
        <line x1="1" y1="12" x2="3" y2="12"></line>
        <line x1="21" y1="12" x2="23" y2="12"></line>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
    </svg>`,
    heat: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2v20M8 6l8 4-8 4 8 4"></path>
    </svg>`
};

// Update the status monitoring functions
let lastLightStatus = false;
let lastHeatStatus = false;

async function updateControlStatus() {
    try {
        const response = await fetch('/api/logs');
        if (!response.ok) throw new Error('Failed to fetch control status');
        const data = await response.json();
        
        // Get the most recent status
        const lastIndex = data.light.length - 1;
        if (lastIndex >= 0) {
            lastLightStatus = Boolean(data.light[lastIndex]);
            lastHeatStatus = Boolean(data.heat[lastIndex]);
            
            updateControlIndicators();
        }
    } catch (error) {
        console.error('Error updating control status:', error);
    }
}

function updateControlIndicators() {
    const controlsContainer = document.querySelector('.status-controls');
    if (!controlsContainer) return;
    
    // Update light indicator
    const lightIndicator = controlsContainer.querySelector('.control-indicator.light-indicator');
    if (lightIndicator) {
        lightIndicator.className = `control-indicator light ${lastLightStatus ? 'active' : 'inactive'}`;
        lightIndicator.querySelector('.tooltip').textContent = `Light: ${lastLightStatus ? 'ON' : 'OFF'}`;
    }
    
    // Update heat indicator
    const heatIndicator = controlsContainer.querySelector('.control-indicator.heat-indicator');
    if (heatIndicator) {
        heatIndicator.className = `control-indicator heat ${lastHeatStatus ? 'active' : 'inactive'}`;
        heatIndicator.querySelector('.tooltip').textContent = `Heat: ${lastHeatStatus ? 'ON' : 'OFF'}`;
    }
}

// Single, unified initializeStatusMonitor function
function initializeStatusMonitor() {
    let container = document.getElementById('statusContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'statusContainer';
        container.className = 'status-container';
        
        // Create controls container
        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'status-controls';
        
        // Add light indicator
        const lightIndicator = document.createElement('div');
        lightIndicator.className = 'control-indicator light-indicator inactive';
        lightIndicator.innerHTML = `
            ${ICONS.light}
            <span class="tooltip">Light: OFF</span>
        `;
        controlsContainer.appendChild(lightIndicator);
        
        // Add heat indicator
        const heatIndicator = document.createElement('div');
        heatIndicator.className = 'control-indicator heat-indicator inactive';
        heatIndicator.innerHTML = `
            ${ICONS.heat}
            <span class="tooltip">Heat: OFF</span>
        `;
        controlsContainer.appendChild(heatIndicator);
        
        // Create main status icon
        const icon = document.createElement('div');
        icon.className = 'status-icon stopped pulse';
        
        // Create details card
        const detailsCard = document.createElement('div');
        detailsCard.className = 'status-details-card';
        
        // Add click handlers
        icon.addEventListener('click', () => {
            detailsCard.classList.toggle('visible');
            icon.classList.remove('pulse');
        });
        
        document.addEventListener('click', (event) => {
            if (!container.contains(event.target)) {
                detailsCard.classList.remove('visible');
            }
        });
        
        // Add all elements to container
        container.appendChild(controlsContainer);
        container.appendChild(icon);
        container.appendChild(detailsCard);
        document.body.appendChild(container);
    }

    // Start status checking
    updateStatus();
    updateControlStatus();
    
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
    statusCheckInterval = setInterval(() => {
        updateStatus();
        updateControlStatus();
    }, 30000);
}

async function updateStatus() {
    const container = document.getElementById('statusContainer');
    if (!container) return;

    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        
        const timestamp = new Date().toLocaleTimeString();
        const status = data.details.service_running ? 'running' : 'stopped';
        
        // Update the icon state
        const icon = container.querySelector('.status-icon');
        icon.className = `status-icon ${status}`;
        
        // Update the details card
        const detailsCard = container.querySelector('.status-details-card');
        if (detailsCard) {
            detailsCard.className = `status-details-card ${status}${detailsCard.classList.contains('visible') ? ' visible' : ''}`;
            detailsCard.innerHTML = `
                <div class="status-header">
                    Service: ${status === 'running' ? 'Running' : 'Stopped'}
                </div>
                <div class="status-details">
                    <div>Configuration: ${data.details.config_valid ? 'Valid' : 'Invalid'}</div>
                    <div>Backup Available: ${data.details.backup_exists ? 'Yes' : 'No'}</div>
                </div>
                <div class="status-timestamp">
                    Last Updated: ${timestamp}
                </div>
            `;
        }
    } catch (error) {
        const icon = container.querySelector('.status-icon');
        icon.className = 'status-icon stopped';
        
        const detailsCard = container.querySelector('.status-details-card');
        if (detailsCard) {
            detailsCard.className = `status-details-card stopped${detailsCard.classList.contains('visible') ? ' visible' : ''}`;
            detailsCard.innerHTML = `
                <div class="status-header">
                    Status Check Failed
                </div>
                <div class="status-details">
                    ${error.message}
                </div>
                <div class="status-timestamp">
                    ${new Date().toLocaleTimeString()}
                </div>
            `;
        }
    }
}

async function mountStatusMonitor() {
    const container = document.getElementById('statusContainer');
    const StatusMonitor = await import('./StatusMonitor.jsx');
    ReactDOM.render(React.createElement(StatusMonitor.default), container);
}

// Wait for everything to be ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize status monitor
    initializeStatusMonitor();

    // Initialize charts
    try {
    
        // Test Chart.js availability
        if (typeof Chart === 'undefined') {
            console.error('Chart.js not loaded');
            return;
        }

        // Register the controllers and elements we need
        Chart.register(Chart.LineController, Chart.LineElement, Chart.PointElement, Chart.LinearScale, Chart.CategoryScale, Chart.Legend, Chart.Tooltip);

        tempHumidityChart = new Chart(
            document.getElementById('tempHumidityChart'),
            {
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
            }
        );

        uvChart = new Chart(
            document.getElementById('uvChart'),
            {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'UVA (mW/cm²)',
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
                                text: 'UVA (mW/cm²)'
                            },
                            beginAtZero: true,
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
                            grid: {
                                drawOnChartArea: false,
                            },
                        }
                    }
                }
            }
        );

        // Start updating charts
        updateCharts();
        // Update every 60 seconds
        setInterval(updateCharts, 60000);

    } catch (error) {
        console.error('Error initializing charts:', error);
    }
});

// Functions
async function updateCharts() {
    try {
        const response = await fetch('/api/logs');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update temperature/humidity chart
        if (tempHumidityChart) {
            tempHumidityChart.data.labels = data.timestamps;
            tempHumidityChart.data.datasets[0].data = data.temperature;
            tempHumidityChart.data.datasets[1].data = data.humidity;
            tempHumidityChart.update();
        }

        // Update UV chart
        if (uvChart) {
            uvChart.data.labels = data.timestamps;
            uvChart.data.datasets[0].data = data.uva;
            uvChart.data.datasets[1].data = data.uvb;
            uvChart.data.datasets[2].data = data.uvc;
            uvChart.update();
        }
        
        // Also check service status
        const statusResponse = await fetch('/api/status');
        if (statusResponse.ok) {
            const statusData = await statusResponse.json();
        }

    } catch (error) {
        console.error('Error in updateCharts:', error);
    }
}

// Function to format I2C address
function formatI2CAddress(input) {
    let value;
    // If input is an element, get its value, otherwise treat input as the value
    if (input instanceof HTMLElement) {
        value = input.value;
    } else {
        value = String(input);
    }
    
    // Remove any existing "0x" prefix and spaces
    value = value.replace(/^0x/i, '').replace(/\s/g, '');
    
    // Remove any non-hex characters
    value = value.replace(/[^0-9A-Fa-f]/g, '');
    
    // Limit to 2 characters
    value = value.slice(0, 2);
    
    // Return formatted value or set input value if element was passed
    const formattedValue = value ? `0x${value.toLowerCase()}` : '';
    if (input instanceof HTMLElement) {
        input.value = formattedValue;
    }
    return formattedValue;
}
// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    const i2cInput = document.getElementById('DISPLAY_ADDRESS');
    if (i2cInput) {
        formatI2CAddress(i2cInput);
    }
});

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        console.log('Loaded config:', config);

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
        displayAddressInput.value = formatI2CAddress(config.DISPLAY_ADDRESS);
        document.getElementById('DISPLAY_RESET').value = config.DISPLAY_RESET;
        document.getElementById('LIGHT_RELAY').value = config.LIGHT_RELAY;
        document.getElementById('HEAT_RELAY').value = config.HEAT_RELAY;

    } catch (error) {
        console.error('Error loading config:', error);
        const status = document.getElementById('status');
        status.textContent = 'Error loading configuration: ' + error.message;
        status.className = 'status error';
        status.style.display = 'block';
        setTimeout(() => {
            status.style.display = 'none';
        }, 3000);
    }
}
// Call loadConfig when the page loads
document.addEventListener('DOMContentLoaded', loadConfig);

// Handle form submission
document.getElementById('configForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const config = {};
    
    // Process form data
    for (const [key, value] of formData.entries()) {
        if (key.includes('.')) {
            // Handle threshold values
            const [mainKey, subKey] = key.split('.');
            if (!config[mainKey]) {
                config[mainKey] = {};
            }
            config[mainKey][subKey] = parseFloat(value);
        } else if (key === 'DISPLAY_ADDRESS') {
            // Convert hex string to number
            config[key] = parseInt(value, 16);
        } else if (document.getElementById(key).type === 'number') {
            // Convert numeric inputs
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
        const status = document.getElementById('status');
        
        if (result.status === 'success') {
            status.textContent = 'Settings saved successfully!';
            status.className = 'status success';
        } else {
            status.textContent = 'Error saving settings: ' + result.message;
            status.className = 'status error';
        }
        
        status.style.display = 'block';
        setTimeout(() => {
            status.style.display = 'none';
        }, 3000);
        
    } catch (error) {
        console.error('Error:', error);
    }
});