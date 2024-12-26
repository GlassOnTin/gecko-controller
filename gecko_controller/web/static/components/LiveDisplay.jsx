import React, { useState, useEffect } from 'react';

const LiveDisplay = () => {
  const [displayImage, setDisplayImage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDisplay = async () => {
      try {
        const response = await fetch('/api/display');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (data.status === 'success') {
          setDisplayImage(data.image);
          setError(null);
        } else {
          throw new Error(data.message || 'Failed to fetch display image');
        }
      } catch (error) {
        console.error('Error fetching display:', error);
        setError(error.message);
      }
    };

    // Initial fetch
    fetchDisplay();

    // Update every 1 second
    const interval = setInterval(fetchDisplay, 1000);

    return () => clearInterval(interval);
  }, []);

  // Scaled dimensions matching OLED display
  const scale = 4; // Scale factor for better visibility
  const width = 128 * scale;
  const height = 64 * scale;

  if (error) {
    return (
      <div className="w-full max-w-md mx-auto p-4 text-red-500 text-center">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto p-4">
      {displayImage ? (
        <div
          className="bg-black rounded-lg p-4 flex items-center justify-center"
          style={{
            width: `${width}px`,
            height: `${height}px`,
            margin: '0 auto'
          }}
        >
          <img
            src={`data:image/png;base64,${displayImage}`}
            alt="OLED Display"
            style={{
              width: '100%',
              height: '100%',
              imageRendering: 'pixelated'  // Keep pixels sharp when scaling
            }}
          />
        </div>
      ) : (
        <div className="w-full h-32 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-gray-900"></div>
        </div>
      )}
    </div>
  );
};

export default LiveDisplay;
