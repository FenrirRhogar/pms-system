import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Navbar.css';

export default function Navbar({ setIsAuthenticated }) {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user'));
  const leaderTeamId = localStorage.getItem('leaderTeamId');

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    localStorage.removeItem('leaderTeamId');
    setIsAuthenticated(false);
    navigate('/login');
  };

  const getNavItems = () => {
    if (!user) return [];

    const role = user.role;
    const items = [];

    if (role === 'ADMIN') {
      items.push({ label: '⚙️ Admin Panel', path: '/admin' });
    } else if (role === 'TEAM_LEADER') {
      items.push({ 
        label: '🏢 My Team', 
        path: leaderTeamId ? `/teams/${leaderTeamId}` : '/my-teams' 
      });
      items.push({ label: '📋 Tasks', path: `/teams/${leaderTeamId}/tasks` });
    } else if (role === 'MEMBER') {
      items.push({ label: '🏢 My Teams', path: '/my-teams' });
      items.push({ label: '📋 My Tasks', path: '/my-tasks' });
    }

    items.push({ label: '👤 Profile', path: '/profile' });

    return items;
  };

  const navItems = getNavItems();

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <div className="navbar-left">
          <h1 className="navbar-logo">
            Project Management System
          </h1>
        </div>

        <div className="navbar-center">
          {navItems.map((item) => (
            <button
              key={item.path}
              className="nav-link"
              onClick={() => navigate(item.path)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className="navbar-right">
          {user && (
            <>
              <span className="user-info">
                {user.username}
                <span className="role-badge">{user.role}</span>
              </span>
              <button 
                className="btn-logout"
                onClick={handleLogout}
              >
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
