import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import '../styles/AdminPanel.css';

export default function AdminPanel() {
  const navigate = useNavigate();
  const token = localStorage.getItem('access_token');

  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [allTasks, setAllTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tabLoading, setTabLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreateTeamForm, setShowCreateTeamForm] = useState(false);
  const [teamFormData, setTeamFormData] = useState({
    name: '',
    description: '',
    leader_id: ''
  });
  const [filterTeamId, setFilterTeamId] = useState('ALL');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');
  const [filterCreatedAfter, setFilterCreatedAfter] = useState('');
  const [filterDueBy, setFilterDueBy] = useState('');

  useEffect(() => {
    // Φόρτωσε ΟΛΑ τα δεδομένα αμέσως κατά την εκκίνηση
    fetchAllData();
  }, []);

  // Φόρτωσε όλα τα δεδομένα παράλληλα
  const fetchAllData = async () => {
    try {
      setLoading(true);

      // Ζήτησε όλα τα δεδομένα παράλληλα
      const [usersRes, teamsRes] = await Promise.all([
        api.get('/api/users', { params: { token } }),
        api.get('/api/admin/teams', { params: { token } })
      ]);

      setUsers(usersRes.data);
      setTeams(teamsRes.data);

      // Φόρτωσε τα tasks από όλα τα teams
      let tasks = [];
      for (const team of teamsRes.data) {
        try {
          const tasksRes = await api.get(`/api/teams/${team.id}/tasks`, {
            params: { token },
          });

          tasks = [
            ...tasks,
            ...tasksRes.data.map(task => ({
              ...task,
              team_name: team.name,
              team_id: team.id
            }))
          ];
        } catch (err) {
          console.error(`Failed to fetch tasks for team ${team.id}:`, err);
        }
      }

      tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setAllTasks(tasks);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'users') {
      fetchUsers();
    } else if (activeTab === 'teams') {
      fetchTeams();
    } else if (activeTab === 'tasks') {
      fetchAllTasks();
    }
  }, [activeTab]);

  const fetchUsers = async () => {
    try {
      setTabLoading(true);
      const response = await api.get('/api/users', {
        params: { token },
      });
      setUsers(response.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load users');
    } finally {
      setTabLoading(false);
    }
  };

  const fetchTeams = async () => {
    try {
      setTabLoading(true);
      const response = await api.get('/api/admin/teams', {
        params: { token },
      });
      setTeams(response.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load teams');
    } finally {
      setTabLoading(false);
    }
  };

  const fetchAllTasks = async () => {
    try {
      setTabLoading(true);
      let tasks = [];

      for (const team of teams) {
        const tasksResponse = await api.get(`/api/teams/${team.id}/tasks`, {
          params: { token },
        });

        tasks = [
          ...tasks,
          ...tasksResponse.data.map(task => ({
            ...task,
            team_name: team.name,
            team_id: team.id
          }))
        ];
      }

      tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setAllTasks(tasks);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tasks');
    } finally {
      setTabLoading(false);
    }
  };

  // ... υπόλοιπος κώδικας παραμένει ίδιος ...

  const handleToggleUserStatus = async (userId, currentStatus) => {
    const action = currentStatus ? 'deactivate' : 'activate';
    const confirmMsg = currentStatus
      ? 'Are you sure you want to deactivate this user?'
      : 'Are you sure you want to activate this user?';

    if (!window.confirm(confirmMsg)) return;

    try {
      await api.patch(`/api/users/${userId}/activate`, {}, {
        params: { token },
      });

      setUsers((prevUsers) =>
        prevUsers.map((user) =>
          user.id === userId ? { ...user, is_active: !user.is_active } : user
        )
      );

      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to ${action} user`);
    }
  };

  const handleChangeRole = async (userId, newRole) => {
    try {
      await api.patch(`/api/users/${userId}/role`, { role: newRole }, {
        params: { token },
      });
      fetchUsers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (window.confirm(`Are you sure you want to delete ${username}?`)) {
      try {
        await api.delete(`/api/users/${userId}`, {
          params: { token },
        });
        fetchUsers();
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to delete user');
      }
    }
  };

  const handleTeamFormChange = (e) => {
    const { name, value } = e.target;
    setTeamFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!teamFormData.name || !teamFormData.leader_id) {
      setError('Please fill in all required fields');
      return;
    }

    try {
      await api.post('/api/teams', teamFormData, {
        params: { token },
      });
      setTeamFormData({ name: '', description: '', leader_id: '' });
      setShowCreateTeamForm(false);
      setError('');
      fetchTeams();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create team');
    }
  };

  const handleDeleteTeam = async (teamId, teamName) => {
    if (window.confirm(`Are you sure you want to delete "${teamName}"?`)) {
      try {
        await api.delete(`/api/teams/${teamId}`, {
          params: { token },
        });
        fetchTeams();
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to delete team');
      }
    }
  };

  const teamLeaders = users.filter(user => user.role === 'TEAM_LEADER');

  const filteredTasks = allTasks.filter(task => {
    const teamMatch = filterTeamId === 'ALL' || task.team_id === filterTeamId;
    const statusMatch = filterStatus === 'ALL' || task.status === filterStatus;
    const priorityMatch = filterPriority === 'ALL' || task.priority === filterPriority;
    const createdMatch = !filterCreatedAfter || new Date(task.created_at) >= new Date(filterCreatedAfter);
    const dueMatch = !filterDueBy || (task.due_date && new Date(task.due_date) <= new Date(filterDueBy));
    return teamMatch && statusMatch && priorityMatch && createdMatch && dueMatch;
  });

  const getStatusColor = (status) => {
    switch (status) {
      case 'TODO':
        return '#999';
      case 'IN_PROGRESS':
        return '#FFD93D';
      case 'COMPLETED':
        return '#6BCF7F';
      case 'ON_HOLD':
        return '#FF6B6B';
      default:
        return '#999';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'URGENT':
        return '#FF6B6B';
      case 'HIGH':
        return '#FFA500';
      case 'MEDIUM':
        return '#4ECDC4';
      case 'LOW':
        return '#95E1D3';
      default:
        return '#999';
    }
  };

const handleClearFilters = () => {
  setFilterTeamId('ALL');
  setFilterStatus('ALL');
  setFilterPriority('ALL');
  setFilterCreatedAfter('');
  setFilterDueBy('');
};


  if (loading) return <div className="loading">Loading admin panel...</div>;

  return (
    <div className="admin-panel-container">
      <div className="admin-header">
        <h1>Admin Panel</h1>
        <p>Manage users, teams and tasks</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Tabs - Αριθμοί φορτώνονται ήδη */}
      <div className="admin-tabs">
        <button
          className={`tab ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          👥 Users ({users.length})
        </button>
        <button
          className={`tab ${activeTab === 'teams' ? 'active' : ''}`}
          onClick={() => setActiveTab('teams')}
        >
          🏢 Teams ({teams.length})
        </button>
        <button
          className={`tab ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          📋 Tasks ({allTasks.length})
        </button>
      </div>

      {/* Loading indicator for tab */}
      {tabLoading && <div className="loading">Loading...</div>}

      {/* Users Tab */}
      {!tabLoading && activeTab === 'users' && (
        <div className="admin-content">
          <div className="users-grid">
            {users.map((user) => (
              <div key={user.id} className="user-card">
                <div className="user-header">
                  <h3>{user.username}</h3>
                  <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>

                <div className="user-details">
                  <p><strong>Email:</strong> {user.email}</p>
                  <p><strong>Role:</strong> {user.role}</p>
                  <p><strong>Created:</strong> {new Date(user.created_at).toLocaleDateString()}</p>
                </div>

                <div className="user-actions">
                  <button
                    className={user.is_active ? 'btn-deactivate' : 'btn-activate'}
                    onClick={() => handleToggleUserStatus(user.id, user.is_active)}
                  >
                    {user.is_active ? 'Deactivate' : 'Activate'}
                  </button>

                  <select
                    value={user.role}
                    onChange={(e) => handleChangeRole(user.id, e.target.value)}
                    className="role-select"
                  >
                    <option value="MEMBER">Member</option>
                    <option value="TEAM_LEADER">Team Leader</option>
                    <option value="ADMIN">Admin</option>
                  </select>

                  <button
                    className="btn-delete"
                    onClick={() => handleDeleteUser(user.id, user.username)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          {users.length === 0 && (
            <div className="empty-state">No users found</div>
          )}
        </div>
      )}

      {/* Teams Tab */}
      {!tabLoading && activeTab === 'teams' && (
        <div className="admin-content">
          <div className="teams-header-admin">
            <h2>Teams</h2>
            <button
              className="btn-primary-sm"
              onClick={() => setShowCreateTeamForm(!showCreateTeamForm)}
            >
              {showCreateTeamForm ? 'Cancel' : '+ Create Team'}
            </button>
          </div>

          {showCreateTeamForm && (
            <div className="create-team-form-admin">
              <form onSubmit={handleCreateTeam}>
                <div className="form-group">
                  <label>Team Name *</label>
                  <input
                    type="text"
                    name="name"
                    value={teamFormData.name}
                    onChange={handleTeamFormChange}
                    placeholder="Enter team name"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Description</label>
                  <textarea
                    name="description"
                    value={teamFormData.description}
                    onChange={handleTeamFormChange}
                    placeholder="Enter team description"
                    rows="3"
                  />
                </div>

                <div className="form-group">
                  <label>Team Leader *</label>
                  <select
                    name="leader_id"
                    value={teamFormData.leader_id}
                    onChange={handleTeamFormChange}
                    required
                  >
                    <option value="">-- Select a leader --</option>
                    {teamLeaders.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.username} ({user.email})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-actions">
                  <button type="submit" className="btn-primary">
                    Create Team
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowCreateTeamForm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          <div className="teams-grid">
            {teams.map((team) => (
              <div key={team.id} className="team-card-admin">
                <div className="team-header-admin">
                  <h3>{team.name}</h3>
                </div>

                <p className="description">{team.description || 'No description'}</p>

                <div className="team-details-admin">
                  <p><strong>Leader:</strong> {team.leader_info?.username || 'Unknown'}</p>
                  <p><strong>Created:</strong> {new Date(team.created_at).toLocaleDateString()}</p>
                </div>

                <div className="team-actions-admin">
                  <button
                    className="btn-view"
                    onClick={() => navigate(`/teams/${team.id}`)}
                  >
                    View
                  </button>
                  <button
                    className="btn-delete"
                    onClick={() => handleDeleteTeam(team.id, team.name)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          {teams.length === 0 && (
            <div className="empty-state">No teams found</div>
          )}
        </div>
      )}

      {/* Tasks Tab */}
{!tabLoading && activeTab === 'tasks' && (
  <div className="admin-content">
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
      <h2 style={{ margin: 0 }}>All Tasks</h2>
      <button
        onClick={handleClearFilters}
        className="btn-clear-filters"
      >
        ✕ Clear Filters
      </button>
    </div>

    <div className="tasks-filters-admin">
      <div className="filter-group">
        <label>Team:</label>
        <select value={filterTeamId} onChange={(e) => setFilterTeamId(e.target.value)}>
          <option value="ALL">All Teams</option>
          {teams.map(team => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
        </select>
      </div>
      
      <div className="filter-group">
        <label>Status:</label>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
          <option value="ALL">All</option>
          <option value="TODO">To Do</option>
          <option value="IN_PROGRESS">In Progress</option>
          <option value="COMPLETED">Completed</option>
          <option value="ON_HOLD">On Hold</option>
        </select>
      </div>
      
      <div className="filter-group">
        <label>Priority:</label>
        <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)}>
          <option value="ALL">All</option>
          <option value="LOW">Low</option>
          <option value="MEDIUM">Medium</option>
          <option value="HIGH">High</option>
          <option value="URGENT">Urgent</option>
        </select>
      </div>
      
      <div className="filter-group">
        <label>Created After:</label>
        <input
          type="date"
          value={filterCreatedAfter}
          onChange={(e) => setFilterCreatedAfter(e.target.value)}
        />
      </div>
      
      <div className="filter-group">
        <label>Due By:</label>
        <input
          type="date"
          value={filterDueBy}
          onChange={(e) => setFilterDueBy(e.target.value)}
        />
      </div>
    </div>

          <div className="tasks-list-admin">
            {filteredTasks.length > 0 ? (
              filteredTasks.map(task => (
                <div key={task.id} className="task-item-admin">
                  <div className="task-header-admin">
                    <div className="task-title-admin">
                      <h4>{task.title}</h4>
                      <span className="team-badge-admin">{task.team_name}</span>
                    </div>
                    <div className="task-badges-admin">
                      <span
                        className="priority-badge-admin"
                        style={{ backgroundColor: getPriorityColor(task.priority) }}
                      >
                        {task.priority}
                      </span>
                      <span
                        className="status-badge-admin"
                        style={{ backgroundColor: getStatusColor(task.status) }}
                      >
                        {task.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  {task.description && (
                    <p className="task-description-admin">{task.description}</p>
                  )}

                  <div className="task-info-admin">
                    <div>
                      <strong>Created by:</strong> {task.created_by_user?.username}
                    </div>
                    <div>
                      <strong>Assigned to:</strong> {task.assigned_to_user?.username || 'Unassigned'}
                    </div>
                    {task.created_at && (
                      <div>
                        <strong>Created:</strong> {new Date(task.created_at).toLocaleDateString()}
                      </div>
                    )}
                    {task.due_date && (
                      <div>
                        <strong>Due:</strong> {new Date(task.due_date).toLocaleDateString()}
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">No tasks found</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
