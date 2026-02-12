import React, { useState } from 'react';

const InputForm = ({ onSubmit, isLoading }) => {
    const [formData, setFormData] = useState({
        current_location: '',
        pickup_location: '',
        dropoff_location: '',
        hours_used: ''
    });

    const handleChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        onSubmit(formData);
    };

    return (
        <div className="card">
            <h2>Trip Details</h2>
            <form onSubmit={handleSubmit}>
                <div>
                    <label htmlFor="current_location">Current Location</label>
                    <input
                        type="text"
                        id="current_location"
                        name="current_location"
                        placeholder="e.g. Chicago, IL"
                        value={formData.current_location}
                        onChange={handleChange}
                        required
                    />
                </div>

                <div>
                    <label htmlFor="pickup_location">Pickup Location</label>
                    <input
                        type="text"
                        id="pickup_location"
                        name="pickup_location"
                        placeholder="e.g. Indianapolis, IN"
                        value={formData.pickup_location}
                        onChange={handleChange}
                        required
                    />
                </div>

                <div>
                    <label htmlFor="dropoff_location">Dropoff Location</label>
                    <input
                        type="text"
                        id="dropoff_location"
                        name="dropoff_location"
                        placeholder="e.g. Nashville, TN"
                        value={formData.dropoff_location}
                        onChange={handleChange}
                        required
                    />
                </div>

                <div>
                    <label htmlFor="hours_used">Hours Used in 8-Day Cycle (0-70)</label>
                    <input
                        type="number"
                        id="hours_used"
                        name="hours_used"
                        placeholder="e.g. 50"
                        min="0"
                        max="70"
                        step="0.1"
                        value={formData.hours_used}
                        onChange={handleChange}
                        required
                    />
                </div>

                <button type="submit" disabled={isLoading}>
                    {isLoading ? (
                        <span className="loading-spinner"></span>
                    ) : (
                        'Calculate Trip & Generate Logs'
                    )}
                </button>
            </form>
        </div>
    );
};

export default InputForm;
