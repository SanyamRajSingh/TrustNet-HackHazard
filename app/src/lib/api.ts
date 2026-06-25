const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
console.log('[API] Base URL configured as:', API_BASE);


interface InvestigateRequest {
  raw_input: string;
  input_type: 'paste' | 'screenshot' | 'pdf' | 'voice';
  source_language?: string;
}

interface VoiceRequest {
  audio_base64: string;
  mime_type: string;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ message: `HTTP ${resp.status}` }));
    throw new Error(err.message || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export const api = {
  investigate: (body: InvestigateRequest) =>
    apiFetch('/investigate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  voiceInvestigate: (body: VoiceRequest) =>
    apiFetch('/voice', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getInvestigation: (id: string) => apiFetch(`/investigate/${id}`),

  getGraph: (entityValue: string) => apiFetch(`/graph/${encodeURIComponent(entityValue)}`),

  getStats: () => apiFetch('/stats'),

  getEntity: (hash: string) => apiFetch(`/entity/${hash}`),

  submitReport: (body: { entity_id: string; report_type: string; loss_amount_inr?: number; description?: string }) =>
    apiFetch('/community/report', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getCommunityReports: (params?: { entity_id?: string; limit?: number }) => {
    const qs = params ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined) as [string, string][]).toString() : '';
    return apiFetch(`/community/reports${qs}`);
  },

  checkRegistry: (hash: string) => apiFetch(`/registry/check/${hash}`),
};