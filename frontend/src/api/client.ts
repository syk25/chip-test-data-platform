const BASE = '/api/v1'

function authHeader(): Record<string, string> {
  const token = localStorage.getItem('token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...authHeader(), ...init?.headers },
    ...init,
  })
  if (res.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
  if (!res.ok) { const err = await res.json().catch(() => ({})); throw new Error(err.detail ?? res.statusText) }
  return res.json()
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }),

  me: () => request<{ id: number; email: string; name: string; role_id: number }>('/users/me'),

  lots: (page = 1) => request<LotSummary[]>(`/lots?page=${page}`),
  lot: (id: number) => request<LotDetail>(`/lots/${id}`),

  uploadStdf: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/stdf-files`, {
      method: 'POST',
      headers: authHeader(),
      body: form,
    }).then(r => r.json())
  },

  jobStatus: (jobId: number) =>
    request<{ job_id: number; status: string; error_message: string | null }>(`/stdf-files/${jobId}/status`),

  measurements: (partId: number, page = 1) =>
    request<Measurement[]>(`/measurements?part_id=${partId}&page=${page}`),
}

export interface LotSummary {
  id: number; lot_code: string; product_type: string | null
  wafer_count: number; total_parts: number; pass_parts: number; fail_rate: number
  created_at: string
}
export interface LotDetail extends LotSummary { wafers: WaferSummary[] }
export interface WaferSummary {
  id: number; wafer_code: string; total_parts: number; pass_parts: number; fail_rate: number
}
export interface Measurement {
  id: number; test_num: number; test_name: string; unit: string | null
  result: number | null; is_pass: boolean; is_alarm: boolean
}
