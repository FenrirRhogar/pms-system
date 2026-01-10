import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests CORRECTLY
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.params = config.params || {};
    config.params.token = token;  // ← Στέλνε το token ως query parameter
  }
  return config;
});

// Global 401 handler
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Καθαρισμός ληγμένου/άκυρου token
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      localStorage.removeItem('leaderTeamId');
      // Redirect σε login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  signup: (username, email, password) =>
    api.post('/api/users/signup', { username, email, password }),
  
  login: (email, password) =>
    api.post('/api/users/login', { email, password }),
  
  getCurrentUser: () =>
    api.get('/api/users/me'),
};

export default api;
