import React from 'react';

const TripSummary = ({ summary, route }) => {
    if (!summary) return null;

    return (
        <div className="card">
            <h2>Trip Summary</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                    <strong>Total Distance:</strong>
                    <div>{route.total_distance.toFixed(1)} miles</div>
                </div>
                <div>
                    <strong>Total Duration:</strong>
                    <div>{summary.total_trip_hours.toFixed(1)} hours</div>
                </div>
                <div>
                    <strong>Available Cycle Hours Remaining:</strong>
                    <div style={{ color: summary.available_hours < 10 ? '#d32f2f' : 'inherit', fontWeight: 'bold' }}>
                        {summary.available_hours.toFixed(1)} hours
                    </div>
                </div>
                <div>
                    <strong>Route Legs:</strong>
                    <div>2 (Pickup + Dropoff)</div>
                </div>
            </div>
        </div>
    );
};

export default TripSummary;
