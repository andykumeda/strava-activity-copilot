import React from 'react';
import { Activity } from 'lucide-react';
import { API_ENDPOINTS } from '../config';

const LandingPage: React.FC = () => {
    const handleConnect = async () => {
        try {
            const response = await fetch(API_ENDPOINTS.AUTH.START, { method: 'POST' });
            const data = await response.json();
            if (data.url) {
                window.location.href = data.url;
            } else {
                alert('Failed to get auth URL');
            }
        } catch (error) {
            console.error(error);
            alert('Failed to connect to backend');
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
            <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8 text-center">
                <div className="flex justify-center mb-6">
                    <div className="p-4 bg-orange-100 rounded-full">
                        <Activity className="w-12 h-12 text-orange-600" />
                    </div>
                </div>
                <h1 className="text-3xl font-bold text-gray-900 mb-2">Strava Insight Portal</h1>
                <p className="text-gray-600 mb-8">
                    Connect your Strava account to get AI-powered insights into your training history.
                </p>
                <button
                    onClick={handleConnect}
                    className="w-full bg-orange-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-orange-700 transition-colors flex items-center justify-center gap-2"
                >
                    Connect with Strava
                </button>
            </div>
        </div>
    );
};

export default LandingPage;
