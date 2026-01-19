import { useEffect, useState } from 'react';
import LandingPage from './components/LandingPage';
import Dashboard from './components/Dashboard';
import type { User } from './types';
import { Activity } from 'lucide-react';
import { API_ENDPOINTS } from './config';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    console.log("App mounted");
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await fetch(API_ENDPOINTS.AUTH.ME, {
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
