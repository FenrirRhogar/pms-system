import { useNavigate, Link } from 'react-router-dom';
import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import '../styles/MyTasksPage.css';

export default function MyTasksPage() {

  const user = JSON.parse(localStorage.getItem('user'));

  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');

  const navigate = useNavigate();

  const fetchMyTasks = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch all teams of the member
      const teamsResponse = await api.get('/api/teams/mine/member');

      // Fetch tasks from each team
      let allTasks = [];
      for (const team of teamsResponse.data) {
        const tasksResponse = await api.get(`/api/tasks/team/${team.id}`);
        
        // Add team info to each task
        allTasks = [
          ...allTasks,
          ...tasksResponse.data.map(task => ({
            ...task,
            team_name: team.name,
            team_id: team.id
          }))
        ];
      }

      // Sort by created_at descending
      allTasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setTasks(allTasks);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  }, [user.id]);

  useEffect(() => {
    fetchMyTasks();
  }, [fetchMyTasks]);

  const handleUpdateTaskStatus = async (taskId, newStatus) => {
    try {
      await api.patch(`/api/tasks/${taskId}`, {
        status: newStatus
      });
      fetchMyTasks();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update task');
    }
  };

  const filteredTasks = tasks.filter(task => {
    const statusMatch = filterStatus === 'ALL' || task.status === filterStatus;
    const priorityMatch = filterPriority === 'ALL' || task.priority === filterPriority;
    return statusMatch && priorityMatch;
  });

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

  const getCompletionStats = () => {
    const total = tasks.length;
    const completed = tasks.filter(t => t.status === 'COMPLETED').length;
    const inProgress = tasks.filter(t => t.status === 'IN_PROGRESS').length;
    return { total, completed, inProgress };
  };

  const stats = getCompletionStats();
  
  if (loading) return <div className="loading">Loading your tasks...</div>;

  return (
    <div className="my-tasks-page-container">
      {error && <div className="error-message">{error}</div>}

      <div className="my-tasks-header">
        <div>
          <h1>My Tasks</h1>
          <p className="subtitle">Tasks assigned to you</p>
        </div>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{stats.total}</div>
          <div className="stat-label">Total Tasks</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.inProgress}</div>
          <div className="stat-label">In Progress</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.completed}</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats.total - stats.completed}</div>
          <div className="stat-label">Remaining</div>
        </div>
      </div>

      {/* Filters */}
      <div className="tasks-filters">
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
      </div>

      {/* Tasks */}
      <div className="tasks-list">
        {filteredTasks.length > 0 ? (
          filteredTasks.map(task => (
            <div key={task.id} className="task-item">
              <div className="task-item-header">
                <div className="task-title-section">
                  <h3>
                    <Link to={`/teams/${task.team_id}/tasks/${task.id}`} className="task-title-link">
                      {task.title}
                    </Link>
                  </h3>
                  <Link to={`/teams/${task.team_id}`} className="team-badge-link">
                    <span className="team-badge">{task.team_name}</span>
                  </Link>
                </div>
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

              <div className="task-meta-row">
                <div className="task-meta">
                  <span className="meta-label">Created by:</span>
                  <span className="meta-value">{task.created_by_user?.username}</span>
                </div>
                {task.due_date && (
                  <div className="task-meta">
                    <span className="meta-label">Due:</span>
                    <span className="meta-value">{new Date(task.due_date).toLocaleDateString()}</span>
                  </div>
                )}
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
    onClick={() => navigate(`/teams/${task.team_id}/tasks/${task.id}`)}
  >
    View Details
  </button>
</div>

            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No tasks assigned to you</p>
          </div>
        )}
      </div>
    </div>
  );
}
