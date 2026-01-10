// frontend/src/components/CommentsList.jsx

import React, { useState } from 'react';
import api from '../api';
import '../styles/CommentsList.css';

export default function CommentsList({ comments = [], onCommentMutated }) {
  const [editingCommentId, setEditingCommentId] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [error, setError] = useState('');
  const currentUser = JSON.parse(localStorage.getItem('user'));

  const handleEditComment = (commentId, content) => {
    setEditingCommentId(commentId);
    setEditContent(content);
  };

  const handleSaveEdit = async (commentId) => {
    if (!editContent.trim()) {
      setError('Comment cannot be empty');
      return;
    }

    try {
      await api.patch(`/api/comments/${commentId}`, {
        content: editContent
      });
      
      setEditingCommentId(null);
      setEditContent('');
      if (onCommentMutated) {
        onCommentMutated();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update comment');
    }
  };

  const handleDeleteComment = async (commentId) => {
    if (!window.confirm('Delete this comment?')) return;

    try {
      await api.delete(`/api/comments/${commentId}`);
      if (onCommentMutated) {
        onCommentMutated();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete comment');
    }
  };

  const canEditDeleteComment = (comment) => {
    return currentUser && (
      currentUser.id === comment.user?.id || 
      currentUser.role === 'ADMIN'
    );
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
  };

  return (
    <div className="comments-list-container">
      <h3 className="comments-title">
        💬 Comments ({comments.length})
      </h3>

      {error && <div className="comments-error">{error}</div>}

      {comments.length > 0 ? (
        <div className="comments-list">
          {comments.map(comment => (
            <div key={comment.id} className="comment-item">
              <div className="comment-header">
                <div className="comment-author-info">
                  <span className="comment-author">
                    {comment.user?.username || 'Unknown User'}
                  </span>
                  <span className="comment-time">
                    {formatDate(comment.created_at)}
                  </span>
                  {comment.created_at !== comment.updated_at && (
                    <span className="comment-edited">(edited)</span>
                  )}
                </div>

                {canEditDeleteComment(comment) && (
                  <div className="comment-actions">
                    <button
                      className="comment-btn-edit"
                      onClick={() => handleEditComment(comment.id, comment.content)}
                      title="Edit"
                    >
                      ✏️
                    </button>
                    <button
                      className="comment-btn-delete"
                      onClick={() => handleDeleteComment(comment.id)}
                      title="Delete"
                    >
                      🗑️
                    </button>
                  </div>
                )}
              </div>

              {editingCommentId === comment.id ? (
                <div className="comment-edit-form">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="comment-edit-textarea"
                    autoFocus
                  />
                  <div className="comment-edit-actions">
                    <button
                      className="btn-save-edit"
                      onClick={() => handleSaveEdit(comment.id)}
                    >
                      Save
                    </button>
                    <button
                      className="btn-cancel-edit"
                      onClick={() => setEditingCommentId(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <p className="comment-content">{comment.content}</p>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="comments-empty">
          <p>No comments yet. Be the first to comment!</p>
        </div>
      )}
    </div>
  );
}
