import axios from "axios";

// Get the API base URL from environment or use localhost as fallback
export const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const REQUIREMENT_SERVICE_URL = import.meta.env.VITE_REQUIREMENT_SERVICE_URL || "http://localhost:8001";

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
    DELETE: (meetingId: string) => `${REQUIREMENT_SERVICE_URL}/api/meetings/${meetingId}`,
  },
  // Schedule Endpoints
  SCHEDULES: {
    CREATE: `${REQUIREMENT_SERVICE_URL}/api/schedules/`,
    LIST: `${REQUIREMENT_SERVICE_URL}/api/schedules/`,
    GET: (id: string) => `${REQUIREMENT_SERVICE_URL}/api/schedules/${id}`,
    UPDATE: (id: string) => `${REQUIREMENT_SERVICE_URL}/api/schedules/${id}`,
    DELETE: (id: string) => `${REQUIREMENT_SERVICE_URL}/api/schedules/${id}`,
  },
  // Chat Endpoint (RAG)
  CHAT: `${API_BASE_URL}/api/chat/`,
  // Video Endpoints (Requirement Service)
  VIDEOS: {
    STREAM: (meetingId: string) => `${REQUIREMENT_SERVICE_URL}/api/videos/${meetingId}/stream`,
    INFO: (meetingId: string) => `${REQUIREMENT_SERVICE_URL}/api/videos/${meetingId}/info`,
  },
  // Custom Requirements Endpoints
  CUSTOM_REQUIREMENTS: {
    UPLOAD: `${API_BASE_URL}/api/custom-requirements/upload`,
    LIST: (projectId: string) => `${API_BASE_URL}/api/custom-requirements/list/${projectId}`,
    DELETE: (requirementId: string) => `${API_BASE_URL}/api/custom-requirements/${requirementId}`,
    VIEW: (requirementId: string) => `${API_BASE_URL}/api/custom-requirements/view/${requirementId}`,
  },
  // Unified Requirements List (combines meetings and custom requirements)
  REQUIREMENTS: {
    LIST_ALL: (projectId: string) => `${REQUIREMENT_SERVICE_URL}/api/requirements/list/${projectId}`,
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
