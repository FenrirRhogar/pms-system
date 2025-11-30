// frontend/src/components/CommentForm.jsx

import React, { useState } from 'react';
import api from '../api';
import '../styles/CommentForm.css';

export default function CommentForm({ taskId, token, onCommentAdded }) {
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [charCount, setCharCount] = useState(0);

  const handleContentChange = (e) => {
    const text = e.target.value;
    setContent(text);
    setCharCount(text.length);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!content.trim()) {
      setError('Comment cannot be empty');
      return;
    }

    try {
      setLoading(true);
      await api.post(`/api/comments/task/${taskId}`, {
        content: content.trim()
      }, {
        params: { token }
      });

      setContent('');
      setCharCount(0);
      setError('');
      
      if (onCommentAdded) {
        onCommentAdded();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add comment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="comment-form-container">
      <h3 className="comment-form-title">Add a Comment</h3>

      {error && <div className="comment-form-error">{error}</div>}

      <form onSubmit={handleSubmit} className="comment-form">
        <div className="form-group">
          <textarea
            value={content}
            onChange={handleContentChange}
            placeholder="Write your comment here..."
            className="comment-textarea"
            rows="4"
            maxLength="1000"
          />
          <div className="textarea-footer">
            <span className="char-count">
              {charCount}/1000
            </span>
          </div>
        </div>

        <button
          type="submit"
          className="btn-submit-comment"
          disabled={loading || !content.trim()}
        >
          {loading ? 'Posting...' : '📤 Post Comment'}
        </button>
      </form>
    </div>
  );
}
