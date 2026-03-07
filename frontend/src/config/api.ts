import axios from "axios";

// Get the API base URL from environment or use localhost as fallback
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// API Endpoints
export const API_ENDPOINTS = {
  // Workspace Endpoints
  WORKSPACES: {
    LIST: `${API_BASE_URL}/api/workspaces`,
    CREATE: `${API_BASE_URL}/api/workspaces`,
    GET: (id: string) => `${API_BASE_URL}/api/workspaces/${id}`,
    UPDATE: (id: string) => `${API_BASE_URL}/api/workspaces/${id}`,
    DELETE: (id: string) => `${API_BASE_URL}/api/workspaces/${id}`,
  },
  // Project Endpoints
  PROJECTS: {
    LIST: (workspaceId: string) =>
      `${API_BASE_URL}/api/workspaces/${workspaceId}/projects`,
    CREATE: (workspaceId: string) =>
      `${API_BASE_URL}/api/workspaces/${workspaceId}/projects`,
    GET: (workspaceId: string, projectId: string) =>
      `${API_BASE_URL}/api/workspaces/${workspaceId}/projects/${projectId}`,
    UPDATE: (workspaceId: string, projectId: string) =>
      `${API_BASE_URL}/api/workspaces/${workspaceId}/projects/${projectId}`,
    DELETE: (workspaceId: string, projectId: string) =>
      `${API_BASE_URL}/api/workspaces/${workspaceId}/projects/${projectId}`,
  },
  // Meeting Endpoints
  MEETINGS: {
    JOIN: `${API_BASE_URL}/api/meetings/join`,
  },
  // Health Check
  HEALTH: `${API_BASE_URL}/health`,
};

// Axios Instance with Interceptors
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request Interceptor - Add Authorization Header
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage (set by react-oidc-context)
    const auth = localStorage.getItem("oidc.user");
    if (auth) {
      try {
        const user = JSON.parse(auth);
        if (user?.access_token) {
          config.headers.Authorization = `Bearer ${user.access_token}`;
        }
      } catch (error) {
        console.error("Failed to parse auth from localStorage:", error);
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor - Handle Errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - token might be expired
      console.error("Unauthorized - Token might be expired");
      // Could trigger logout here if needed
    }
    return Promise.reject(error);
  }
);

export default apiClient;
