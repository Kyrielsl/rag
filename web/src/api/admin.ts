import http from './http'

export interface TokenOut {
  access_token: string
  token_type: string
}

export interface DashboardOut {
  documents: number
  needs_review: number
  domains: number
  api_keys: number
}

export interface DocumentHit {
  document_id: string
  name: string
  type: string
  status: string
  domains: string[]
  sensitive: boolean
  created_at: string
}

export interface AuditItem {
  id: string
  subject: string | null
  action: string
  object_id: string | null
  result: string
  query_summary: string | null
  hit_count: number
  sensitive_hit: boolean
  ip: string | null
  created_at: string
}

export interface ApiKeyItem {
  id: string
  name: string
  scope: string
  status: string
  expires_at: string | null
  created_at: string
}

export interface DomainItem {
  id: string
  name: string
  is_sensitive: boolean
}

export interface DocumentDetail {
  document_id: string
  name: string
  type: string
  size: number
  sha256: string
  status: string
  extracted_status: string
  needs_review: boolean
  sensitive: boolean
  created_at: string
  domains: { domain: string; confidence: number; source: string }[]
  content: { text: string; fields: any; rows: any; encoding: string | null; delimiter: string | null; warnings: any } | null
}

export const login = (username: string, password: string) =>
  http.post<TokenOut>('/auth/login', { username, password }).then((r) => r.data)

export const dashboard = () => http.get<DashboardOut>('/admin/dashboard').then((r) => r.data)

export const listDocuments = (params?: Record<string, any>) =>
  http.get<DocumentHit[]>('/admin/documents', { params }).then((r) => r.data)

export const documentDetail = (id: string) =>
  http.get<DocumentDetail>(`/admin/documents/${id}`).then((r) => r.data)

export const reviewQueue = () => http.get<DocumentHit[]>('/admin/review-queue').then((r) => r.data)

export const reviewDocument = (id: string, action: 'approve' | 'reject') =>
  http.post(`/admin/review/${id}`, { action }).then((r) => r.data)

export const listAudit = (params?: Record<string, any>) =>
  http.get<AuditItem[]>('/admin/audit', { params }).then((r) => r.data)

export const listApiKeys = () => http.get<ApiKeyItem[]>('/admin/api-keys').then((r) => r.data)

export const createApiKey = (name: string, scope: string) =>
  http.post<ApiKeyItem & { key: string }>('/admin/api-keys', { name, scope }).then((r) => r.data)

export const listDomains = () => http.get<DomainItem[]>('/domains').then((r) => r.data)

export const createDomain = (name: string, is_sensitive: boolean) =>
  http.post('/admin/domains', { name, is_sensitive }).then((r) => r.data)

export const updateDomain = (id: string, body: { enabled?: boolean; is_sensitive?: boolean }) =>
  http.patch(`/admin/domains/${id}`, body).then((r) => r.data)
export const saveCustomerFields = (id: string, fields: Record<string, any>) =>
  http.patch(`/admin/documents/${id}/customer-fields`, { fields }).then((r) => r.data)