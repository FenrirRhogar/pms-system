import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { authAPI } from '../api';
import '../styles/AuthPage.css';

export default function LoginPage({ setIsAuthenticated, setUserRole, setLeaderTeamId }) {
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    console.log("Login form submitted");
    setError('');
    setLoading(true);

    try {
      console.log("Sending login request...", formData);
      const response = await authAPI.login(formData.email, formData.password);
      console.log("Login response received:", response);
      
      // Save token and user data
      const token = response.data.access_token;
      const user = response.data.user;
      
      localStorage.setItem('access_token', token);
      localStorage.setItem('user', JSON.stringify(user));
      
      // Update parent state
      setIsAuthenticated(true);
      setUserRole(user.role);
      
      console.log("Redirecting based on role:", user.role);
      
      // Navigate based on role
      if (user.role === 'ADMIN') {
        navigate('/admin');
      } else if (user.role === 'TEAM_LEADER') {
        // Fetch team ID for the leader and then navigate
        try {
            const teamResponse = await api.get('/api/teams/mine/leader');
            if (teamResponse.data && teamResponse.data.id) {
                const teamId = teamResponse.data.id;
                setLeaderTeamId(teamId);
                navigate(`/teams/${teamId}`);
            } else {
                navigate('/my-teams');
            }
        } catch (err) {
            console.error('Failed to fetch leader team ID', err);
            navigate('/my-teams');
        }
      } else if (user.role === 'MEMBER') {
        navigate('/my-teams');
      }
    } catch (err) {
      console.error("Login caught error:", err);
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      console.log("Login finally block reached, setting loading false");
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>Login</h2>
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email"
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              required
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        <p>
          Don't have an account? <a href="/signup">Sign Up</a>
        </p>
      </div>
    </div>
  );
}
