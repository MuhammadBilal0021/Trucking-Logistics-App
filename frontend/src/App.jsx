import React, { useState } from 'react';
import axios from 'axios';
import InputForm from './components/InputForm';
import RouteMap from './components/RouteMap';
import ELDLog from './components/ELDLog';
import TripSummary from './components/TripSummary';
import './index.css';

function App() {
  const [tripData, setTripData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleTripCalculation = async (formData) => {
    setIsLoading(true);
    setError(null);
    setTripData(null);

    try {
      // Use local backend URL
      const response = await axios.post('http://127.0.0.1:8000/api/calculate-trip/', formData);
      setTripData(response.data);
    } catch (err) {
      console.error(err);
      const errorMessage = err.response?.data?.error || err.message || 'An unexpected error occurred';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header>
        <h1>Trucking Logistics App</h1>
        <p>HOS Calculation & ELD Logs</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '350px 1fr', gap: '2rem', textAlign: 'left' }}>
        <aside>
          <InputForm onSubmit={handleTripCalculation} isLoading={isLoading} />

          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          {tripData && (
            <TripSummary
              summary={{
                total_trip_hours: tripData.total_trip_hours,
                available_hours: tripData.available_hours
              }}
              route={tripData.route}
            />
          )}
        </aside>

        <main>
          {tripData ? (
            <>
              <RouteMap
                routeData={tripData.route}
                tripSegments={tripData.trip_segments}
              />
              <ELDLog segments={tripData.eld_logs} />
            </>
          ) : (
            <div className="card" style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
              <div>
                <h3>No trip calculated</h3>
                <p>Enter trip details to see route and logs</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
