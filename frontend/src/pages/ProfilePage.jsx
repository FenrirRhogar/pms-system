import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import '../styles/ProfilePage.css';

export default function ProfilePage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/users/me');
      setUser(response.data);
    } catch (err) {
      console.error(err.response?.data?.detail || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  if (loading) return <div className="loading">Loading profile...</div>;
  if (!user) return <div className="error-message">Profile not found</div>;

  return (
    <div className="profile-container">
      <div className="profile-card">
        <div className="profile-header">
          <div className="profile-avatar">
            {user.username.charAt(0).toUpperCase()}
          </div>
          <div className="profile-info">
            <h1>{user.username}</h1>
            <p className="email">{user.email}</p>
          </div>
        </div>

        <div className="profile-details">
          <div className="detail-section">
            <h3>Account Information</h3>

            <div className="detail-item">
              <span className="label">Email:</span>
              <span className="value">{user.email}</span>
            </div>
            <div className="detail-item">
              <span className="label">Role:</span>
              <span className={`role-badge role-${user.role.toLowerCase()}`}>
                {user.role}
              </span>
            </div>

            <div className="detail-item">
              <span className="label">Status:</span>
              <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div className="detail-item">
              <span className="label">Member Since:</span>
              <span className="value">
                {new Date(user.created_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
