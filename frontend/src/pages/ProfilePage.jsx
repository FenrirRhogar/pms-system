import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import '../styles/ProfilePage.css';

export default function ProfilePage() {

  const token = localStorage.getItem('access_token');
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const fetchProfile = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/users/me', {
        params: { token },
      });
      setUser(response.data);
      setEditData({
        username: response.data.username,
        email: response.data.email,
      });
    } catch (err) {
      console.error(err.response?.data?.detail || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, [token]);

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditData((prev) => ({ ...prev, [name]: value }));
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    // Αυτή τη στιγμή δεν υπάρχει update endpoint, αλλά μπορούμε να το προσθέσουμε αργότερα
    alert('Profile editing will be available soon!');
    setEditMode(false);
  };

  if (loading) return <div className="loading">Loading profile...</div>;
  if (!user) return <div className="error-message">Profile not found</div>;

  return (
    <div className="profile-container">

      <div className="profile-card">
        {!editMode ? (
          <>
            <div className="profile-header">
              <div className="profile-avatar">
                {user.username.charAt(0).toUpperCase()}
              </div>
              <div className="profile-info">
                <h1>{user.username}</h1>
                <p className="email">{user.email}</p>
              </div>
              <button 
                className="btn-edit-profile" 
                onClick={() => setEditMode(true)}
              >
                Edit Profile
              </button>
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
          </>
        ) : (
          <form onSubmit={handleEditSubmit} className="edit-profile-form">
            <h2>Edit Profile</h2>
            
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                name="username"
                value={editData.username}
                onChange={handleEditChange}
                disabled
              />
              <small>Username cannot be changed</small>
            </div>

            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                name="email"
                value={editData.email}
                onChange={handleEditChange}
                disabled
              />
              <small>Email editing will be available soon</small>
            </div>

            <div className="form-actions">
              <button type="button" className="btn-cancel" onClick={() => setEditMode(false)}>
                Cancel
              </button>
              <button type="submit" className="btn-save" disabled>
                Save Changes (Coming Soon)
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
