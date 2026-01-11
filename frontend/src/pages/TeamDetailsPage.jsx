import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import api from '../api';
import '../styles/TeamDetailsPage.css';
import '../styles/Charts.css';

export default function TeamDetailsPage() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const [team, setTeam] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [availableMembers, setAvailableMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddMember, setShowAddMember] = useState(false);
  const [selectedMember, setSelectedMember] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({ name: '', description: '' });
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [isRemovingMember, setIsRemovingMember] = useState(null);

  const user = JSON.parse(localStorage.getItem('user'));

  const isLeader = team?.leader?.id === user?.id;
  const isAdmin = user?.role === 'ADMIN';
  const canEdit = isLeader || isAdmin;

  const fetchTeamDetails = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/teams/${teamId}`);
      setTeam(response.data);
      setEditData({
        name: response.data.name,
        description: response.data.description,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load team');
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  const fetchAvailableMembers = useCallback(async () => {
    try {
      const response = await api.get('/api/teams/available-members');
      setAvailableMembers(response.data);
    } catch (err) {
      console.error('Failed to fetch available members', err);
    }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const response = await api.get(`/api/tasks/team/${teamId}`);
      setTasks(response.data);
    } catch (err) {
      console.error('Failed to fetch tasks', err);
    }
  }, [teamId]);

  useEffect(() => {
    fetchTeamDetails();
    fetchAvailableMembers();
    fetchTasks();
  }, [fetchTeamDetails, fetchAvailableMembers, fetchTasks]);

  const filteredAvailableMembers = team
    ? availableMembers.filter(
        member => !team.members.some(m => m.id === member.id)
      )
    : availableMembers;

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!selectedMember) return;

    try {
      setIsAddingMember(true);
      await api.post(`/api/teams/${teamId}/members`, { user_id: selectedMember });

      const memberToAdd = availableMembers.find(m => m.id === selectedMember);
      if (memberToAdd) {
        setTeam(prev => ({
          ...prev,
          members: [...prev.members, memberToAdd],
        }));
        setAvailableMembers(prev =>
          prev.filter(m => m.id !== selectedMember)
        );
      }

      setSelectedMember('');
      setShowAddMember(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add member');
    } finally {
      setIsAddingMember(false);
    }
  };

  const handleRemoveMember = async (userId) => {
    if (!window.confirm('Are you sure you want to remove this member?')) return;

    try {
      setIsRemovingMember(userId);
      await api.delete(`/api/teams/${teamId}/members/${userId}`);

      let removed;
      setTeam(prev => {
        const remaining = prev.members.filter(m => {
          if (m.id === userId) removed = m;
          return m.id !== userId;
        });
        return { ...prev, members: remaining };
      });

      if (removed && removed.role === 'MEMBER') {
        setAvailableMembers(prev => [...prev, removed]);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove member');
    } finally {
      setIsRemovingMember(null);
    }
  };

  const handleUpdateTeam = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/api/teams/${teamId}`, editData);
      setEditMode(false);
      fetchTeamDetails();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update team');
    }
  };

  const handleDeleteTeam = async () => {
    if (window.confirm('Are you sure you want to delete this team? This action cannot be undone.')) {
      try {
        await api.delete(`/api/teams/${teamId}`);
        navigate('/teams');
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to delete team');
      }
    }
  };

  const handleUpdateTaskStatus = async (taskId, newStatus) => {
    try {
      await api.patch(`/api/tasks/${taskId}`, {
        status: newStatus
      });
      fetchTasks();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update task');
    }
  };

  const handleDeleteTask = async (taskId, taskTitle) => {
    if (!window.confirm(`Delete task "${taskTitle}"?`)) return;

    try {
      await api.delete(`/api/tasks/${taskId}`);
      fetchTasks();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete task');
    }
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditData((prev) => ({ ...prev, [name]: value }));
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

  // Prepare Chart Data
  const getTaskStatusData = () => {
    const counts = { TODO: 0, IN_PROGRESS: 0, COMPLETED: 0, ON_HOLD: 0 };
    tasks.forEach(t => {
      if (counts[t.status] !== undefined) counts[t.status]++;
    });
    return [
      { name: 'To Do', value: counts.TODO, color: '#999' },
      { name: 'In Progress', value: counts.IN_PROGRESS, color: '#FFD93D' },
      { name: 'Completed', value: counts.COMPLETED, color: '#6BCF7F' },
      { name: 'On Hold', value: counts.ON_HOLD, color: '#FF6B6B' },
    ].filter(d => d.value > 0);
  };

  const getTasksPerMemberData = () => {
    if (!team || !team.members) return [];
    
    // Initialize with 0 for all members
    const memberCounts = {};
    team.members.forEach(m => memberCounts[m.id] = { name: m.username, count: 0 });
    
    // Also include tasks assigned to users who might have left the team or are just IDs
    tasks.forEach(t => {
      if (t.assigned_to) {
        if (memberCounts[t.assigned_to]) {
          memberCounts[t.assigned_to].count++;
        }
      }
    });

    return Object.values(memberCounts).map(m => ({
      name: m.name,
      tasks: m.count,
      color: '#4ECDC4'
    })).filter(m => m.tasks > 0).sort((a, b) => b.tasks - a.tasks).slice(0, 10);
  };

  const taskStatusData = getTaskStatusData();
  const tasksPerMemberData = getTasksPerMemberData();

  if (loading) return <div className="loading">Loading team details...</div>;
  if (!team) return <div className="error-message">Team not found</div>;

  return (
    <div className="team-details-container">
      {error && <div className="error-message">{error}</div>}

      <div className="team-header-section">
        {!editMode ? (
          <>
            <div className="team-info">
              <h1>{team.name}</h1>
              <p className="description">{team.description || 'No description'}</p>
              <div className="team-meta">
                <span>Leader: <strong>{team.leader?.username || 'Unknown'}</strong></span>
                <span>Members: <strong>{team.members.length}</strong></span>
              </div>
            </div>
            {canEdit && (
              <div className="team-actions">
                <button className="btn-edit" onClick={() => setEditMode(true)}>
                  Edit Team
                </button>
                {isAdmin && (
                  <button className="btn-danger" onClick={handleDeleteTeam}>
                    Delete Team
                  </button>
                )}
              </div>
            )}
          </>
        ) : (
          <form onSubmit={handleUpdateTeam} className="edit-form">
            <div className="form-group">
              <label>Team Name</label>
              <input
                type="text"
                name="name"
                value={editData.name}
                onChange={handleEditChange}
                required
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={editData.description}
                onChange={handleEditChange}
                rows="4"
              />
            </div>
            <div className="form-actions">
              <button type="submit" className="btn-primary">
                Save Changes
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setEditMode(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Visualizations Section */}
      {tasks.length > 0 && (
        <div className="charts-container" style={{ marginBottom: '40px' }}>
          <div className="chart-card">
            <h3>Task Status</h3>
            <div className="chart-wrapper">
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={taskStatusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {taskStatusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                    itemStyle={{ color: 'var(--color-text)' }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="chart-card">
            <h3>Tasks per Member</h3>
            <div className="chart-wrapper">
              <ResponsiveContainer>
                <BarChart data={tasksPerMemberData} layout="vertical">
                  <XAxis type="number" allowDecimals={false} stroke="var(--color-text-secondary)" fontSize={12} />
                  <YAxis dataKey="name" type="category" width={100} stroke="var(--color-text-secondary)" fontSize={12} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(var(--color-brown-600-rgb), 0.05)' }}
                    contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                    itemStyle={{ color: 'var(--color-text)' }}
                  />
                  <Bar dataKey="tasks" fill="var(--color-primary)" radius={[0, 4, 4, 0]}>
                    {tasksPerMemberData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Tasks Section */}
      <div className="tasks-section">
        <div className="tasks-header">
          <h2>Tasks ({tasks.length})</h2>
          {canEdit && (
            <button className="btn-create-task" onClick={() => navigate(`/teams/${teamId}/tasks`)}>
              View Tasks
            </button>
          )}
        </div>

        <div className="tasks-grid">
          {tasks.length > 0 ? (
            tasks.map(task => (
              <div key={task.id} className="task-card">
                <div className="task-card-header">
                  <h3>{task.title}</h3>
                  <div className="task-badges">
                    <span
                      className="priority-badge"
                      style={{ backgroundColor: getPriorityColor(task.priority) }}
                    >
                      {task.priority}
                    </span>
                    <span
                      className="status-badge"
                      style={{ backgroundColor: getStatusColor(task.status) }}
                    >
                      {task.status.replace('_', ' ')}
                    </span>
                  </div>
                </div>

                {task.description && (
                  <p className="task-description">{task.description}</p>
                )}

                <div className="task-info">
                  <span><strong>Assigned:</strong> {task.assigned_to_user?.username || 'Unassigned'}</span>
                  {task.due_date && (
                    <span><strong>Due:</strong> {new Date(task.due_date).toLocaleDateString()}</span>
                  )}
                  <span><strong>Created by:</strong> {task.created_by_user?.username}</span>
                </div>

                <div className="task-actions">
                  <select
                    value={task.status}
                    onChange={(e) => handleUpdateTaskStatus(task.id, e.target.value)}
                    className="status-select"
                  >
                    <option value="TODO">To Do</option>
                    <option value="IN_PROGRESS">In Progress</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="ON_HOLD">On Hold</option>
                  </select>

                  <button
                    className="btn-view-details"
                    onClick={() => navigate(`/teams/${teamId}/tasks/${task.id}`)}
                  >
                    View Details
                  </button>

                  {canEdit && (
                    <button
                      className="btn-delete"
                      onClick={() => handleDeleteTask(task.id, task.title)}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">No tasks yet</div>
          )}
        </div>
      </div>

      <div className="members-section">
        <div className="members-header">
          <h2>Team Members ({team.members?.length || 0})</h2>
          {isLeader && (
            <button
              className="btn-primary-sm"
              onClick={() => setShowAddMember(!showAddMember)}
            >
              {showAddMember ? '✕ Cancel' : '+ Add Member'}
            </button>
          )}
        </div>

        <div className={`add-member-wrapper ${showAddMember ? 'open' : ''}`}>
          <form onSubmit={handleAddMember} className="add-member-form">
            <div className="form-group">
              <label>Select Member</label>
              <select
                value={selectedMember}
                onChange={(e) => setSelectedMember(e.target.value)}
                required
              >
                <option value="">Select a member</option>
                {filteredAvailableMembers.length === 0 && (
                  <option value="" disabled>No members available</option>
                )}
                {filteredAvailableMembers.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.username} ({member.email})
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn-primary" disabled={isAddingMember}>
              {isAddingMember ? 'Adding...' : 'Add Member'}
            </button>
          </form>
        </div>

        <div className="members-list">
          {(team.members || []).map((member) => (
            <div key={member.id} className={`member-card ${isRemovingMember === member.id ? 'removing' : ''}`}>
              <div className="member-info">
                <h3>{member.username}</h3>
                <p>{member.email}</p>
                <span className={`role-badge role-${member.role.toLowerCase()}`}>
                  {member.role}
                </span>
              </div>
              {isLeader && member.id !== team.leader.id && (
                <button
                  className="btn-remove"
                  onClick={() => handleRemoveMember(member.id)}
                  disabled={isRemovingMember === member.id}
                >
                  {isRemovingMember === member.id ? '...' : 'Remove'}
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
