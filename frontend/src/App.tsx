import React, { useEffect, useState } from 'react';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import type { User } from './types';
import { Activity } from 'lucide-react';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log("App mounted");
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      // In dev, backend is on port 8000. 
      // Ensure backend CORS allows origin and credentials.
      const response = await fetch('http://localhost:8000/api/auth/me', {
        credentials: 'include' // Send cookies
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error("Auth check failed:", error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-4">
          <Activity className="w-10 h-10 text-orange-600 animate-pulse" />
          <p className="text-gray-500">Loading Strava Insight...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      {user ? (
        <Dashboard user={user} />
      ) : (
        <LandingPage />
      )}
    </div>
  );
}

export default App;
