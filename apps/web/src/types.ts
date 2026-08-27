export type TokenPair = { access_token: string; refresh_token: string }
export type User = { id: string; email: string; full_name: string; is_active: boolean }
export type Workspace = { id: string; name: string; created_at?: string }
export type Ticket = {
  id: string
  client_id: string
  assignee_user_id: string | null
  subject: string
  description: string
  status: string
  priority: string
}
export type Client = {
  id: string
  full_name: string
  primary_email: string | null
  primary_phone: string | null
  is_active: boolean
}
export type Task = {
  id: string
  ticket_id: string
  title: string
  status: string
  assignee_user_id: string | null
  due_at: string | null
}
export type Notification = {
  id: string
  ticket_id: string | null
  type: string
  title: string
  body: string
  read_at: string | null
  created_at: string
}
export type KnowledgeArticle = { id: string; title: string; body: string; status: string }
export type ListResponse<T> = { items: T[]; total: number; limit: number; offset: number }
