import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import '../styles/MyTeamsPage.css';

export default function MyTeamsPage() {
  const navigate = useNavigate();

  const user = JSON.parse(localStorage.getItem('user'));
  
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchTeams = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/teams/mine/member');
      setTeams(response.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load teams');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  if (loading) return <div className="loading">Loading your teams...</div>;

  return (
    <div className="my-teams-container">
      <div className="teams-header">
        <h1>My Teams</h1>
        <p>Welcome back, {user?.username}! Here are your teams.</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="teams-grid">
        {teams.map((team) => (
          <div key={team.id} className="team-card">
            <div className="team-card-header">
              <h3>{team.name}</h3>
            </div>

            <p className="description">{team.description || 'No description'}</p>

            <button
              className="btn-view-team"
              onClick={() => navigate(`/teams/${team.id}`)}
            >
              View Team →
            </button>
          </div>
        ))}
      </div>

      {teams.length === 0 && (
        <div className="empty-state">
          <p>You haven't joined any teams yet</p>
        </div>
      )}
    </div>
  );
}
