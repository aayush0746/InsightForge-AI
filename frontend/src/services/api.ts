import {
  DocumentMetadata,
  ChatRequest,
  ChatResponse,
  ResearchRequest,
  ResearchReport,
  ResearchReportSummary,
  EvaluationRequest,
  EvaluationRunRecord,
  PromptTemplate,
  EvaluationHistorySummary,
  SystemSettings,
  SystemHealth,
  Project,
  ProjectThread,
  User,
  AuthResponse
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const token = localStorage.getItem('insightforge_auth_token');
  const headers = new Headers(init?.headers || {});
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  try {
    return await fetch(url, {
      ...init,
      headers,
      credentials: 'include',
    });
  } catch (error: any) {
    if (error?.message === 'Failed to fetch' || error?.name === 'TypeError') {
      throw new Error('Connection to the server failed. Please ensure the backend is running on port 8000.');
    }
    throw error;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `Server error ${res.status}`;
    try {
      const errorData = await res.json();
      if (errorData.detail) {
        errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // Ignore JSON parse error on non-JSON response
    }
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  // Health
  async getHealth(): Promise<SystemHealth> {
    const res = await authFetch(`${API_BASE}/health`);
    return handleResponse<SystemHealth>(res);
  },

  // Documents
  async listDocuments(): Promise<{ documents: DocumentMetadata[]; total_count: number }> {
    const res = await authFetch(`${API_BASE}/documents`);
    return handleResponse(res);
  },

  async uploadDocument(file: File): Promise<{ success: boolean; document: DocumentMetadata; message: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await authFetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  async ingestUrl(url: string): Promise<{ success: boolean; document: DocumentMetadata; message: string }> {
    const res = await authFetch(`${API_BASE}/documents/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    return handleResponse(res);
  },

  async deleteDocument(documentId: string): Promise<{ success: boolean; message: string }> {
    const res = await authFetch(`${API_BASE}/documents/${documentId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  getDocumentFileUrl(documentId: string): string {
    return `${API_BASE}/documents/${documentId}/file`;
  },

  async compareDocuments(docId1: string, docId2: string): Promise<{ success: boolean; data: any }> {
    const res = await authFetch(`${API_BASE}/documents/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_id_1: docId1, doc_id_2: docId2 }),
    });
    return handleResponse(res);
  },

  // Chat
  async askChat(payload: ChatRequest): Promise<ChatResponse> {
    const res = await authFetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<ChatResponse>(res);
  },

  async getChatHistory(): Promise<{ history: Array<{ id: string; role: 'user' | 'assistant'; content: string; agent_mode?: string; citations?: any[]; created_at?: string }> }> {
    const res = await authFetch(`${API_BASE}/chat/history`);
    return handleResponse(res);
  },

  async saveChatMessage(payload: { role: string; content: string; agent_mode?: string; citations?: any }): Promise<{ success: boolean }> {
    const res = await authFetch(`${API_BASE}/chat/history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async clearChatHistory(): Promise<{ success: boolean }> {
    const res = await authFetch(`${API_BASE}/chat/history`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // Research
  async startResearch(payload: ResearchRequest): Promise<{ success: boolean; report: ResearchReport; message: string }> {
    const res = await authFetch(`${API_BASE}/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async listReports(): Promise<ResearchReportSummary[]> {
    const res = await authFetch(`${API_BASE}/research/reports`);
    return handleResponse<ResearchReportSummary[]>(res);
  },

  async getReport(researchId: string): Promise<ResearchReport> {
    const res = await authFetch(`${API_BASE}/research/${researchId}`);
    return handleResponse<ResearchReport>(res);
  },

  async generatePodcastBriefing(text: string, topic?: string): Promise<{ success: boolean; podcast_script: string; estimated_duration_minutes: number }> {
    const res = await authFetch(`${API_BASE}/research/podcast-briefing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, topic: topic || 'Executive Research Briefing' }),
    });
    return handleResponse(res);
  },

  // Evaluation
  async evaluatePrompts(payload: EvaluationRequest): Promise<EvaluationRunRecord> {
    const res = await authFetch(`${API_BASE}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<EvaluationRunRecord>(res);
  },

  async getTemplates(): Promise<PromptTemplate[]> {
    const res = await authFetch(`${API_BASE}/evaluate/templates`);
    return handleResponse<PromptTemplate[]>(res);
  },

  async getEvaluationHistory(): Promise<EvaluationHistorySummary[]> {
    const res = await authFetch(`${API_BASE}/evaluate/history`);
    return handleResponse<EvaluationHistorySummary[]>(res);
  },

  async getEvaluationRun(runId: string): Promise<EvaluationRunRecord> {
    const res = await authFetch(`${API_BASE}/evaluate/history/${runId}`);
    return handleResponse<EvaluationRunRecord>(res);
  },

  // Settings
  async getSettings(): Promise<SystemSettings> {
    const res = await authFetch(`${API_BASE}/settings`);
    return handleResponse<SystemSettings>(res);
  },

  async updateSettings(settings: SystemSettings): Promise<SystemSettings> {
    const res = await authFetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    return handleResponse<SystemSettings>(res);
  },

  // Workspace Projects & Collections
  async listProjects(): Promise<Project[]> {
    const res = await authFetch(`${API_BASE}/projects`);
    return handleResponse<Project[]>(res);
  },

  async createProject(payload: { name: string; description?: string; color?: string; icon?: string }): Promise<Project> {
    const res = await authFetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<Project>(res);
  },

  async getProject(projectId: string): Promise<Project> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}`);
    return handleResponse<Project>(res);
  },

  async deleteProject(projectId: string): Promise<{ success: boolean; message: string }> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async assignDocToProject(projectId: string, documentId: string): Promise<{ success: boolean; message: string }> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}/documents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: documentId }),
    });
    return handleResponse(res);
  },

  async removeDocFromProject(projectId: string, documentId: string): Promise<{ success: boolean; message: string }> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}/documents/${documentId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // Threads & Conversational Follow-up Memory
  async listThreads(projectId: string): Promise<ProjectThread[]> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}/threads`);
    return handleResponse<ProjectThread[]>(res);
  },

  async createThread(projectId: string, title: string): Promise<ProjectThread> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}/threads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    return handleResponse<ProjectThread>(res);
  },

  async getThread(projectId: string, threadId: string): Promise<ProjectThread> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}/threads/${threadId}`);
    return handleResponse<ProjectThread>(res);
  },

  async deleteThread(projectId: string, threadId: string): Promise<{ success: boolean; message: string }> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}/threads/${threadId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async sendThreadMessage(
    projectId: string,
    threadId: string,
    message: string,
    enableWebSearch: boolean = false
  ): Promise<{ success: boolean; thread: ProjectThread; user_message: any; assistant_message: any }> {
    const res = await authFetch(`${API_BASE}/projects/${projectId}/threads/${threadId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, enable_web_search: enableWebSearch }),
    });
    return handleResponse(res);
  },

  async clearGuestData(): Promise<{ success: boolean; message: string }> {
    try {
      await authFetch(`${API_BASE}/documents/guest/clear`, { method: 'DELETE' });
    } catch {
      // ignore
    }
    const res = await authFetch(`${API_BASE}/projects/guest/clear`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // Authentication (Google & Local)
  async signUp(payload: { name: string; email: string; password: string }): Promise<AuthResponse> {
    const res = await authFetch(`${API_BASE}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<AuthResponse>(res);
  },

  async signIn(payload: { email: string; password: string }): Promise<AuthResponse> {
    const res = await authFetch(`${API_BASE}/auth/signin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<AuthResponse>(res);
  },

  async googleAuth(payload: {
    email: string;
    name: string;
    avatar_url?: string | null;
    google_id?: string;
    credential?: string;
    mode?: 'signin' | 'signup';
  }): Promise<AuthResponse> {
    const res = await authFetch(`${API_BASE}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<AuthResponse>(res);
  },

  async getCurrentUser(token?: string): Promise<User> {
    const authToken = token || localStorage.getItem('insightforge_auth_token');
    const headers: Record<string, string> = {};
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }
    const res = await authFetch(`${API_BASE}/auth/me`, {
      headers,
    });
    return handleResponse<User>(res);
  },

  async logout(): Promise<{ success: boolean }> {
    const authToken = localStorage.getItem('insightforge_auth_token');
    try {
      const headers: Record<string, string> = {};
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
      await authFetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers,
      });
    } catch {
      // ignore
    }
    localStorage.removeItem('insightforge_auth_token');
    localStorage.removeItem('insightforge_user');
    return { success: true };
  },

  async getAuthConfig(): Promise<{ google_client_id: string }> {
    const res = await authFetch(`${API_BASE}/auth/config`);
    return handleResponse<{ google_client_id: string }>(res);
  },

  // OTP Email Verification
  async sendOtp(payload: { email: string; name?: string; purpose?: string }): Promise<{ success: boolean; message: string }> {
    const res = await authFetch(`${API_BASE}/auth/send-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  async verifyOtp(payload: { email: string; otp: string; name?: string; password?: string }): Promise<AuthResponse> {
    const res = await authFetch(`${API_BASE}/auth/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<AuthResponse>(res);
  },

  async resendOtp(payload: { email: string; name?: string }): Promise<{ success: boolean; message: string }> {
    const res = await authFetch(`${API_BASE}/auth/resend-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },
};

