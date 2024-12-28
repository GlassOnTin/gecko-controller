import React, { useState, useEffect } from 'react';

const StatusMonitor = () => {
  const [status, setStatus] = useState({
    serviceRunning: false,
    configValid: false,
    backupExists: false,
    lightStatus: false,
    heatStatus: false,
    lastUpdate: null,
    error: null
  });

  useEffect(() => {
    const checkStatus = async () => {
      try {
        // Fetch service status
        const statusResponse = await fetch('/api/status');
        const statusData = await statusResponse.json();

        // Fetch latest control status from logs
        const logsResponse = await fetch('/api/logs');
        const logsData = await logsResponse.json();

        // Get most recent light/heat status
        const lastIndex = logsData.light.length - 1;
        const lightStatus = lastIndex >= 0 ? Boolean(logsData.light[lastIndex]) : false;
        const heatStatus = lastIndex >= 0 ? Boolean(logsData.heat[lastIndex]) : false;

        setStatus({
          serviceRunning: statusData.details.service_running,
          configValid: statusData.details.config_valid,
          backupExists: statusData.details.backup_exists,
          lightStatus,
          heatStatus,
          lastUpdate: new Date(),
                  error: null
        });
      } catch (error) {
        setStatus(prev => ({
          ...prev,
          error: error.message,
          lastUpdate: new Date()
        }));
      }
    };

    // Initial check
    checkStatus();

    // Check every 30 seconds
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // Create SVG icons for controls
  const icons = {
    light: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>`,
    heat: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M12 2v20M8 6l8 4-8 4 8 4"/>
    </svg>`
  };

  return (
    <div className="flex items-center space-x-4">
    {/* Light Status */}
    <div className={`control-indicator ${status.lightStatus ? 'active' : 'inactive'}`}
    dangerouslySetInnerHTML={{ __html: icons.light }}
    title={`Light: ${status.lightStatus ? 'ON' : 'OFF'}`} />

    {/* Heat Status */}
    <div className={`control-indicator ${status.heatStatus ? 'active' : 'inactive'}`}
    dangerouslySetInnerHTML={{ __html: icons.heat }}
    title={`Heat: ${status.heatStatus ? 'ON' : 'OFF'}`} />

    {/* Service Status */}
    <div className={`status-icon ${status.serviceRunning ? 'running' : 'stopped'}`}>
    <div className="status-details-card">
    <div className="status-header">
    Service: {status.serviceRunning ? 'Running' : 'Stopped'}
    </div>
    <div className="status-details">
    <div>Configuration: {status.configValid ? 'Valid' : 'Invalid'}</div>
    <div>Backup Available: {status.backupExists ? 'Yes' : 'No'}</div>
    </div>
    {status.lastUpdate && (
      <div className="status-timestamp">
      Last Updated: {status.lastUpdate.toLocaleTimeString()}
      </div>
    )}
    {status.error && (
      <div className="status-error">
      Error: {status.error}
      </div>
    )}
    </div>
    </div>
    </div>
  );
};

export default StatusMonitor;
