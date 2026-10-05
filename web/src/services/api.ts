import type {
  Certification,
  FullProfileData,
  PersonalInfo,
  SkillCategory,
  StreamProgressEvent,
  TrackedRepo,
  WorkExperience,
  WorkProject,
} from '../types/profile';

const API_BASE = '/api';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorMsg = `Error ${res.status}: ${res.statusText}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorMsg = errJson.detail;
      }
    } catch (_) {}
    throw new Error(errorMsg);
  }
  return res.json();
}

export const api = {
  // Perfil Completo
  getProfile: (): Promise<FullProfileData> =>
    fetch(`${API_BASE}/profile`).then((res) => handleResponse<FullProfileData>(res)),

  // Info Personal
  updatePersonal: (data: PersonalInfo): Promise<PersonalInfo> =>
    fetch(`${API_BASE}/profile/personal`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<PersonalInfo>(res)),

  // Experiencias Laborales
  createExperience: (data: Omit<WorkExperience, 'id' | 'projects'>): Promise<WorkExperience> =>
    fetch(`${API_BASE}/profile/experiences`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<WorkExperience>(res)),

  updateExperience: (id: number, data: Partial<WorkExperience>): Promise<WorkExperience> =>
    fetch(`${API_BASE}/profile/experiences/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<WorkExperience>(res)),

  deleteExperience: (id: number): Promise<{ message: string; id: number }> =>
    fetch(`${API_BASE}/profile/experiences/${id}`, {
      method: 'DELETE',
    }).then((res) => handleResponse<{ message: string; id: number }>(res)),

  // Iniciativas Técnicas (WorkProject)
  createProject: (data: Omit<WorkProject, 'id'>): Promise<WorkProject> =>
    fetch(`${API_BASE}/profile/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<WorkProject>(res)),

  updateProject: (id: number, data: Partial<WorkProject>): Promise<WorkProject> =>
    fetch(`${API_BASE}/profile/projects/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<WorkProject>(res)),

  deleteProject: (id: number): Promise<{ message: string; id: number }> =>
    fetch(`${API_BASE}/profile/projects/${id}`, {
      method: 'DELETE',
    }).then((res) => handleResponse<{ message: string; id: number }>(res)),

  // Repositorios Seguidos
  getRepos: (): Promise<TrackedRepo[]> =>
    fetch(`${API_BASE}/repos`).then((res) => handleResponse<TrackedRepo[]>(res)),

  toggleRepo: (id: number): Promise<TrackedRepo> =>
    fetch(`${API_BASE}/repos/${id}/toggle`, {
      method: 'PATCH',
    }).then((res) => handleResponse<TrackedRepo>(res)),

  updateRepo: (id: number, data: Partial<TrackedRepo>): Promise<TrackedRepo> =>
    fetch(`${API_BASE}/repos/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<TrackedRepo>(res)),

  createRepo: (data: Omit<TrackedRepo, 'id'>): Promise<TrackedRepo> =>
    fetch(`${API_BASE}/repos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<TrackedRepo>(res)),

  deleteRepo: (id: number): Promise<{ message: string; id: number }> =>
    fetch(`${API_BASE}/repos/${id}`, {
      method: 'DELETE',
    }).then((res) => handleResponse<{ message: string; id: number }>(res)),

  // Habilidades (Skills)
  createSkillCategory: (category: string, skills: string[]): Promise<SkillCategory> =>
    fetch(`${API_BASE}/profile/skills`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category, skills }),
    }).then((res) => handleResponse<SkillCategory>(res)),

  updateSkillCategory: (id: number, skills: string[]): Promise<SkillCategory> =>
    fetch(`${API_BASE}/profile/skills/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ skills }),
    }).then((res) => handleResponse<SkillCategory>(res)),

  deleteSkillCategory: (id: number): Promise<{ message: string; id: number }> =>
    fetch(`${API_BASE}/profile/skills/${id}`, {
      method: 'DELETE',
    }).then((res) => handleResponse<{ message: string; id: number }>(res)),

  // Certificaciones
  createCertification: (data: Omit<Certification, 'id'>): Promise<Certification> =>
    fetch(`${API_BASE}/profile/certifications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<Certification>(res)),

  deleteCertification: (id: number): Promise<{ message: string; id: number }> =>
    fetch(`${API_BASE}/profile/certifications/${id}`, {
      method: 'DELETE',
    }).then((res) => handleResponse<{ message: string; id: number }>(res)),

  // Health
  getHealth: (): Promise<{ status: string; database: string; counts: Record<string, number> }> =>
    fetch(`${API_BASE}/health`).then((res) => handleResponse(res)),

  // Tailoring Studio Stream
  streamTailor: async (
    jobInput: string,
    maxIterations: number = 2,
    language: string = 'en',
    onEvent: (event: StreamProgressEvent) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const res = await fetch(`${API_BASE}/tailor/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_input: jobInput,
        max_iterations: maxIterations,
        language,
      }),
      signal,
    });

    if (!res.ok) {
      let errorMsg = `Error ${res.status}: ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson.detail) errorMsg = errJson.detail;
      } catch (_) {}
      throw new Error(errorMsg);
    }

    if (!res.body) {
      throw new Error('La respuesta del servidor no tiene cuerpo de datos.');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        const trimmed = block.trim();
        if (!trimmed) continue;
        for (const line of trimmed.split('\n')) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            try {
              const parsed: StreamProgressEvent = JSON.parse(dataStr);
              onEvent(parsed);
            } catch (err) {
              console.error('Error parsing SSE event:', err, dataStr);
            }
          }
        }
      }
    }
  },
};

