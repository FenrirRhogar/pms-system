import { useNavigate, Link } from 'react-router-dom';
import React, { useState, useEffect, useCallback } from 'react';
import { 
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
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
      case 'URGENT': return '#FF6B6B';
      case 'HIGH': return '#FFA500';
      case 'MEDIUM': return '#4ECDC4';
      case 'LOW': return '#95E1D3';
      default: return '#999';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'TODO': return '#999';
      case 'IN_PROGRESS': return '#FFD93D';
      case 'COMPLETED': return '#6BCF7F';
      case 'ON_HOLD': return '#FF6B6B';
      default: return '#999';
    }
  };

  // Prepare Data for Charts
  const getStatusData = () => {
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

  const getPriorityData = () => {
    const counts = { URGENT: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    tasks.forEach(t => {
      if (counts[t.priority] !== undefined) counts[t.priority]++;
    });
    return [
      { name: 'Urgent', value: counts.URGENT, color: '#FF6B6B' },
      { name: 'High', value: counts.HIGH, color: '#FFA500' },
      { name: 'Medium', value: counts.MEDIUM, color: '#4ECDC4' },
      { name: 'Low', value: counts.LOW, color: '#95E1D3' },
    ];
  };

  const statusData = getStatusData();
  const priorityData = getPriorityData();

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

      {/* Visualizations Section */}
      <div className="charts-container" style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', marginBottom: '30px' }}>
        
        {/* Status Chart */}
        <div className="chart-card" style={{ flex: 1, minWidth: '300px', backgroundColor: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Task Status Distribution</h3>
          <div style={{ width: '100%', height: 250 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Priority Chart */}
        <div className="chart-card" style={{ flex: 1, minWidth: '300px', backgroundColor: '#fff', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Tasks by Priority</h3>
          <div style={{ width: '100%', height: 250 }}>
            <ResponsiveContainer>
              <BarChart data={priorityData}>
                <XAxis dataKey="name" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="value" fill="#8884d8">
                  {priorityData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
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

      {/* Tasks List */}
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
