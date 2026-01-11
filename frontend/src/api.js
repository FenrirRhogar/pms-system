import axios from 'axios';

// Automatically detect the API URL based on the current browser location
// If running locally or env var is set, use that. Otherwise, assume API is on port 80 of the same host.
const getBaseUrl = () => {
  if (process.env.REACT_APP_API_URL && process.env.REACT_APP_API_URL !== 'http://localhost') {
    return process.env.REACT_APP_API_URL;
  }
  // If we are on localhost, assume local dev environment
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost'; // Gateway is on port 80
  }
  // Otherwise (e.g. GCP IP), use the current hostname but port 80 (default http port)
  return `http://${window.location.hostname}`;
};

const API_BASE_URL = getBaseUrl();

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
    console.error("API Error:", error); // Debug log
    if (error.response && error.response.status === 401) {
      // Don't redirect if we are failing to login (invalid credentials)
      // or if we are already on the login page
      const isLoginRequest = error.config.url.includes('/login');
      const isLoginPage = window.location.pathname === '/login';

      if (!isLoginRequest && !isLoginPage) {
          // Clean up and redirect only for expired sessions on protected routes
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          localStorage.removeItem('leaderTeamId');
          window.location.href = '/login';
      }
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
