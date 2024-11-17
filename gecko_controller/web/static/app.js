// Declare chart variables globally so we can access them in updateCharts
let tempHumidityChart = null;
let uvChart = null;

// Wait for everything to be ready
document.addEventListener('DOMContentLoaded', function() {
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

    } catch (error) {
        console.error('Error in updateCharts:', error);
    }
}

async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const config = await response.json();
        console.log('Loaded config:', config);
        // ... rest of your loadConfig code ...
    } catch (error) {
        console.error('Error loading config:', error);
    }
}


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