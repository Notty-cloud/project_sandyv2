const AUTH_TOKEN_KEY = 'authToken';
const USER_DATA_KEY = 'userData';

export const authService = {
  login: (token, userData) => {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    localStorage.setItem(USER_DATA_KEY, JSON.stringify(userData));
  },

  logout: () => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(USER_DATA_KEY);
  },

  getToken: () => localStorage.getItem(AUTH_TOKEN_KEY),

  getUserData: () => {
    const data = localStorage.getItem(USER_DATA_KEY);
    if (!data) return null;
    try {
      return JSON.parse(data);
    } catch {
      localStorage.removeItem(USER_DATA_KEY);
      return null;
    }
  },

  isAuthenticated: () => localStorage.getItem(AUTH_TOKEN_KEY) !== null,
};
