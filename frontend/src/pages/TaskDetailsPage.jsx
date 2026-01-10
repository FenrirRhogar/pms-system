// frontend/src/pages/TaskDetailsPage.jsx

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import CommentsList from '../components/CommentsList';
import CommentForm from '../components/CommentForm';
import '../styles/TaskDetailsPage.css';

export default function TaskDetailsPage() {
  const { taskId, teamId } = useParams();
  const navigate = useNavigate();

  const user = JSON.parse(localStorage.getItem('user'));

  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: '',
    priority: ''
  });

  const fetchTask = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/tasks/${taskId}/details`);

      setTask(response.data);
      setFormData({
        title: response.data.title,
        description: response.data.description,
        status: response.data.status,
        priority: response.data.priority
      });
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load task');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleUpdateTask = async (e) => {
    e.preventDefault();
    try {
      await api.patch(`/api/tasks/${taskId}`, {
        title: formData.title,
        description: formData.description,
        status: formData.status,
        priority: formData.priority
      });

      setEditMode(false);
      fetchTask();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update task');
    }
  };

  const handleStatusChange = async (e) => {
    const newStatus = e.target.value;
    try {
      await api.patch(`/api/tasks/${taskId}`, {
        status: newStatus
      });
      fetchTask();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update status');
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

  const canEdit = user && user.role === 'TEAM_LEADER';

const canChangeStatus = user && (
  user.id === task?.assigned_to ||
  user.role === 'TEAM_LEADER'
);

  if (loading) return <div className="loading">Loading task...</div>;

  if (!task) return (
    <div className="task-details-container">
      <div className="error-message">{error || 'Task not found'}</div>
      <button className="btn-back" onClick={() => navigate(-1)}>
        ← Go Back
      </button>
    </div>
  );

  return (
    <div className="task-details-container">
      {error && <div className="error-message">{error}</div>}

      <button className="btn-back" onClick={() => navigate(-1)}>
        ← Go Back
      </button>

      <div className="task-details-card">
        {/* Task Header */}
        <div className="task-details-header">
          <div>
            <h1>{task.title}</h1>
            <div className="task-details-badges">
              <span
                className="priority-badge"
                style={{ backgroundColor: getPriorityColor(task.priority) }}
              >
                {task.priority}
              </span>
              {canChangeStatus ? (
                <select
                  value={task.status}
                  onChange={handleStatusChange}
                  className="status-select-details"
                  style={{ backgroundColor: getStatusColor(task.status) }}
                >
                  <option value="TODO">To Do</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="ON_HOLD">On Hold</option>
                </select>
              ) : (
                <span
                  className="status-badge"
                  style={{ backgroundColor: getStatusColor(task.status) }}
                >
                  {task.status.replace('_', ' ')}
                </span>
              )}
            </div>
          </div>

          {canEdit && (
            <button
              className="btn-edit-task"
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? '✕ Cancel' : '✏️ Edit'}
            </button>
          )}
        </div>

        {/* Edit Form */}
        {editMode && canEdit && (
          <form onSubmit={handleUpdateTask} className="task-edit-form">
            <div className="form-group">
              <label>Title</label>
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleFormChange}
              />
            </div>

            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleFormChange}
                rows="5"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Status</label>
                <select
                  name="status"
                  value={formData.status}
                  onChange={handleFormChange}
                >
                  <option value="TODO">To Do</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="COMPLETED">Completed</option>
                  <option value="ON_HOLD">On Hold</option>
                </select>
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

            <div className="form-actions">
              <button type="submit" className="btn-primary">Save Changes</button>
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

        {/* Task Details */}
        {!editMode && (
          <div className="task-details-section">
            <h2>Description</h2>
            <p className="task-description-details">
              {task.description || 'No description provided'}
            </p>

            <div className="task-meta-grid">
              <div className="meta-item">
                <strong>Created by:</strong>
                <span>{task.created_by_user?.username || 'Unknown'}</span>
              </div>

              <div className="meta-item">
                <strong>Assigned to:</strong>
                <span>{task.assigned_to_user?.username || 'Unassigned'}</span>
              </div>

              <div className="meta-item">
                <strong>Created:</strong>
                <span>{new Date(task.created_at).toLocaleDateString()}</span>
              </div>

              {task.due_date && (
                <div className="meta-item">
                  <strong>Due:</strong>
                  <span>{new Date(task.due_date).toLocaleDateString()}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Comments Section */}
      <CommentForm
        taskId={taskId}
        onCommentAdded={fetchTask}
      />
      <CommentsList
        comments={task.comments || []}
        onCommentMutated={fetchTask}
      />
    </div>
  );
}
