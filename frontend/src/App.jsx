import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import AdminPanel from './pages/AdminPanel';
import TeamDetailsPage from './pages/TeamDetailsPage';
import MyTeamsPage from './pages/MyTeamsPage';
import ProfilePage from './pages/ProfilePage';
import TasksPage from './pages/TasksPage';
import MyTasksPage from './pages/MyTasksPage';
import TaskDetailsPage from './pages/TaskDetailsPage';
import Navbar from './components/Navbar';
import './App.css';

function ProtectedRoute({ children, isAuthenticated }) {
  return isAuthenticated ? children : <Navigate to="/login" />;
}

function AppLayout({ children, isAuthenticated, setIsAuthenticated }) {
  return (
    <>
      <Navbar setIsAuthenticated={setIsAuthenticated} />
      {children}
    </>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userRole, setUserRole] = useState(null);
  const [leaderTeamId, setLeaderTeamId] = useState(null);
  const [key, setKey] = useState(0);

  useEffect(() => {
    checkAuthStatus();
    setLoading(false);
  }, []);

  useEffect(() => {
    const handleStorageChange = () => {
      checkAuthStatus();
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const checkAuthStatus = () => {
    const token = localStorage.getItem('access_token');
    const user = JSON.parse(localStorage.getItem('user'));
    const teamId = localStorage.getItem('leaderTeamId');

    setIsAuthenticated(!!token);
    setUserRole(user?.role || null);
    setLeaderTeamId(teamId || null);
    setKey((prev) => prev + 1);
  };

  const handleSetUserRole = (role) => {
    setUserRole(role);
    setKey((prev) => prev + 1);
  };

  const handleSetLeaderTeamId = (teamId) => {
    setLeaderTeamId(teamId);
    if (teamId) {
      localStorage.setItem('leaderTeamId', teamId);
    } else {
      localStorage.removeItem('leaderTeamId');
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <Router key={key}>
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate
                to={userRole === 'ADMIN' ? "/admin" : userRole === 'TEAM_LEADER' ? leaderTeamId ? `/teams/${leaderTeamId}` : "/my-teams" : "/my-teams"
                }
              />
            ) : (
              <LoginPage
                setIsAuthenticated={setIsAuthenticated}
                setUserRole={handleSetUserRole}
                setLeaderTeamId={handleSetLeaderTeamId}
              />
            )
          }
        />

        <Route
          path="/signup"
          element={
            isAuthenticated ? (
              <Navigate
                to={
                  userRole === 'ADMIN'
                    ? "/admin"
                    : userRole === 'TEAM_LEADER'
                      ? leaderTeamId ? `/teams/${leaderTeamId}` : "/my-teams"
                      : "/my-teams"
                }
              />
            ) : (
              <SignupPage setIsAuthenticated={setIsAuthenticated} />
            )
          }
        />

        <Route
          path="/profile"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated}>
                <ProfilePage />
              </AppLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated}>
                <AdminPanel />
              </AppLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/my-teams"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated}>
                <MyTeamsPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/teams/:teamId"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated}>
                <TeamDetailsPage setLeaderTeamId={handleSetLeaderTeamId} />
              </AppLayout>
            </ProtectedRoute>
          }
        />

        <Route
          path="/teams/:teamId/tasks"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated}>
                <TasksPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/my-tasks"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated}>
                <MyTasksPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/teams/:teamId/tasks/:taskId"
          element={
            <ProtectedRoute isAuthenticated={isAuthenticated}>
              <AppLayout isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated}>
                <TaskDetailsPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/"
          element={
            <Navigate
              to={
                isAuthenticated
                  ? userRole === 'ADMIN'
                    ? "/admin"
                    : userRole === 'TEAM_LEADER'
                      ? leaderTeamId ? `/teams/${leaderTeamId}` : "/my-teams"
                      : "/my-teams"
                  : "/login"
              }
            />
          }
        />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}

export default App;
