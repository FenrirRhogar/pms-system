import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import api from '../api';
import CommentsList from '../components/CommentsList';
import CommentForm from '../components/CommentForm';
import '../styles/TasksPage.css';
import '../styles/Charts.css';

export default function TasksPage() {
  const { teamId } = useParams();

  const user = JSON.parse(localStorage.getItem('user'));

  const [team, setTeam] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    priority: 'MEDIUM',
    assigned_to: '',
    due_date: ''
  });

  const [teamMembers, setTeamMembers] = useState([]);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [filterPriority, setFilterPriority] = useState('ALL');

  const isLeader = team && team.leader.id === user?.id;
  const isAdmin = user?.role === 'ADMIN';
  const canCreateTask = isLeader;

  const fetchTeamDetails = useCallback(async () => {
    try {
      const response = await api.get(`/api/teams/${teamId}`);
      setTeam(response.data);
      setTeamMembers(response.data.members);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load team');
    }
  }, [teamId]);

  const fetchTasks = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/tasks/team/${teamId}`);
      setTasks(response.data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    fetchTeamDetails();
    fetchTasks();
  }, [fetchTeamDetails, fetchTasks]);

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!formData.title.trim()) {
      setError('Task title is required');
      return;
    }

    try {
      await api.post(`/api/tasks/team/${teamId}`, {
        title: formData.title,
        description: formData.description,
        priority: formData.priority,
        assigned_to: formData.assigned_to || null,
        due_date: formData.due_date || null,
        team_id: teamId
      });

      setFormData({
        title: '',
        description: '',
        priority: 'MEDIUM',
        assigned_to: '',
        due_date: ''
      });
      setShowCreateForm(false);
      setError('');
      fetchTasks();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create task');
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

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm('Are you sure you want to delete this task?')) return;

    try {
      await api.delete(`/api/tasks/${taskId}`);
      fetchTasks();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete task');
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

  // Prepare Chart Data
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

  if (loading) return <div className="loading">Loading tasks...</div>;

  return (
    <div className="tasks-page-container">
      {error && <div className="error-message">{error}</div>}

      <div className="tasks-header">
        <h1>{team?.name} - Tasks</h1>
        {canCreateTask && (
          <button
            className="btn-primary-sm"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? '✕ Cancel' : '+ Create Task'}
          </button>
        )}
      </div>

      {/* Visualizations Section */}
      {tasks.length > 0 && (
        <div className="charts-container" style={{ marginBottom: '30px' }}>
          <div className="chart-card">
            <h3>Status Overview</h3>
            <div className="chart-wrapper">
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
            <h3>Priority Levels</h3>
            <div className="chart-wrapper">
              <ResponsiveContainer>
                <BarChart data={priorityData}>
                  <XAxis dataKey="name" stroke="var(--color-text-secondary)" fontSize={12} />
                  <YAxis allowDecimals={false} stroke="var(--color-text-secondary)" fontSize={12} />
                  <Tooltip 
                    cursor={{ fill: 'rgba(var(--color-brown-600-rgb), 0.05)' }}
                    contentStyle={{ backgroundColor: 'var(--color-surface)', borderColor: 'var(--color-border)', color: 'var(--color-text)' }}
                    itemStyle={{ color: 'var(--color-text)' }}
                  />
                  <Bar dataKey="value" fill="var(--color-primary)" radius={[4, 4, 0, 0]}>
                    {priorityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {showCreateForm && (
        <div className="create-task-form">
          <form onSubmit={handleCreateTask}>
            <div className="form-row">
              <div className="form-group">
                <label>Title *</label>
                <input
                  type="text"
                  name="title"
                  value={formData.title}
                  onChange={handleFormChange}
                  placeholder="Enter task title"
                  required
                />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select
                  name="priority"
                  value={formData.priority}
                  onChange={handleFormChange}
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="URGENT">Urgent</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Assigned To</label>
                <select
                  name="assigned_to"
                  value={formData.assigned_to}
                  onChange={handleFormChange}
                >
                  <option value="">-- Unassigned --</option>
                  {teamMembers.map(member => (
                    <option key={member.id} value={member.id}>
                      {member.username}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Due Date</label>
                <input
                  type="datetime-local"
                  name="due_date"
                  value={formData.due_date}
                  onChange={handleFormChange}
                />
              </div>
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleFormChange}
                placeholder="Enter task description"
                rows="3"
              />
            </div>

            <div className="form-actions">
              <button type="submit" className="btn-primary">
                Create Task
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setShowCreateForm(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

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

      <div className="tasks-grid">
        {filteredTasks.length > 0 ? (
          filteredTasks.map(task => (
            <div key={task.id} className="task-card">
              <div className="task-header">
                <div>
                  <h3>
                    <Link to={`/teams/${teamId}/tasks/${task.id}`} className="task-title-link">
                      {task.title}
                    </Link>
                  </h3>
                  <div className="team-link-container">
                    Team: <Link to={`/teams/${teamId}`} className="team-link">{team?.name}</Link>
                  </div>
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

              <div className="task-meta">
                {task.assigned_to_user && (
                  <p><strong>Assigned to:</strong> {task.assigned_to_user.username}</p>
                )}
                {task.due_date && (
                  <p><strong>Due:</strong> {new Date(task.due_date).toLocaleDateString()}</p>
                )}
                <p><strong>Created by:</strong> {task.created_by_user?.username}</p>
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
                {(canCreateTask) && (
                  <button
                    className="btn-delete-sm"
                    onClick={() => handleDeleteTask(task.id)}
                  >
                    Delete
                  </button>
                )}
              </div>
              <CommentForm 
  taskId={task.id} 
  onCommentAdded={() => fetchTasks()}
/>
<CommentsList 
  comments={task.comments || []}
  onCommentMutated={() => fetchTasks()}
/>
            </div>
          ))
        ) : (
          <div className="empty-state">No tasks found</div>
        )}
      </div>
    </div>
  );
}
