import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { api, clearTokens, saveTokens, tokenPair } from './api'
import type { Client, KnowledgeArticle, ListResponse, Notification, Task, Ticket, TokenPair, User, Workspace } from './types'

type View = 'overview' | 'tickets' | 'clients' | 'tasks' | 'knowledge' | 'notifications'

const nav: Array<[View, string]> = [
  ['overview', 'Overview'],
  ['tickets', 'Tickets'],
  ['clients', 'Clients'],
  ['tasks', 'Tasks'],
  ['knowledge', 'Knowledge'],
  ['notifications', 'Notifications'],
]

function statusClass(value: string) {
  return `pill pill-${value.replaceAll('_', '-')}`
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(Boolean(tokenPair()))
  const [user, setUser] = useState<User | null>(null)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [workspaceId, setWorkspaceId] = useState(sessionStorage.getItem('csp.workspace') ?? '')
  const [permissions, setPermissions] = useState<string[]>([])
  const [view, setView] = useState<View>('overview')
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [knowledge, setKnowledge] = useState<KnowledgeArticle[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const can = useCallback((permission: string) => permissions.includes(permission), [permissions])

  const loadWorkspace = useCallback(async (id: string) => {
    if (!id) return
    setBusy(true)
    setError('')
    try {
      const permissionResult = await api<{ permissions: string[] }>(`/api/v1/workspaces/${id}/my-permissions`)
      setPermissions(permissionResult.permissions)
      const requests: Promise<void>[] = []
      const load = <T,>(permission: string, path: string, setter: (items: T[]) => void, unwrap = false) => {
        if (!permissionResult.permissions.includes(permission)) { setter([]); return }
        requests.push(api<T[] | ListResponse<T>>(path).then((data) => setter(unwrap ? (data as ListResponse<T>).items : data as T[])))
      }
      load<Ticket>('tickets.read', `/api/v1/workspaces/${id}/tickets?limit=100`, setTickets, true)
      load<Client>('clients.read', `/api/v1/workspaces/${id}/clients?limit=100`, setClients, true)
      load<Task>('tasks.read', `/api/v1/workspaces/${id}/tasks`, setTasks)
      load<KnowledgeArticle>('knowledge.read', `/api/v1/workspaces/${id}/knowledge`, setKnowledge)
      load<Notification>('notifications.read', `/api/v1/workspaces/${id}/notifications`, setNotifications)
      await Promise.all(requests)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load workspace')
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    if (!authenticated) return
    Promise.all([api<User>('/api/v1/auth/me'), api<Workspace[]>('/api/v1/workspaces')])
      .then(([me, spaces]) => {
        setUser(me)
        setWorkspaces(spaces)
        const selected = spaces.some((w) => w.id === workspaceId) ? workspaceId : (spaces[0]?.id ?? '')
        setWorkspaceId(selected)
        if (selected) {
          sessionStorage.setItem('csp.workspace', selected)
          void loadWorkspace(selected)
        }
      })
      .catch((e) => {
        clearTokens()
        setAuthenticated(false)
        setError(e instanceof Error ? e.message : 'Session expired')
      })
  }, [authenticated, loadWorkspace, workspaceId])

  const selectedWorkspace = workspaces.find((w) => w.id === workspaceId)
  const openTickets = tickets.filter((t) => !['resolved', 'closed'].includes(t.status)).length
  const urgentTickets = tickets.filter((t) => t.priority === 'urgent' && !['resolved', 'closed'].includes(t.status)).length
  const openTasks = tasks.filter((t) => t.status === 'open').length
  const unread = notifications.filter((n) => !n.read_at).length

  async function login(email: string, password: string) {
    setBusy(true); setError('')
    try {
      const tokens = await api<TokenPair>('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
      saveTokens(tokens); setAuthenticated(true)
    } catch (e) { setError(e instanceof Error ? e.message : 'Login failed') }
    finally { setBusy(false) }
  }

  async function logout() {
    const pair = tokenPair()
    try { if (pair) await api<void>('/api/v1/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: pair.refresh_token }) }) } catch { /* local logout still proceeds */ }
    clearTokens(); sessionStorage.removeItem('csp.workspace'); setAuthenticated(false); setUser(null); setWorkspaceId('')
  }

  async function markRead(id: string) {
    if (!workspaceId) return
    await api(`/api/v1/workspaces/${workspaceId}/notifications/${id}/read`, { method: 'POST' })
    await loadWorkspace(workspaceId)
  }

  if (!authenticated) return <LoginScreen busy={busy} error={error} onLogin={login} />

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">SE</span><div><strong>Support Endpoint</strong><small>Operations console</small></div></div>
        <nav>{nav.map(([key, label]) => <button key={key} className={view === key ? 'nav-active' : ''} onClick={() => setView(key)}>{label}{key === 'notifications' && unread > 0 ? <span className="nav-badge">{unread}</span> : null}</button>)}</nav>
        <div className="sidebar-foot"><span className="health-dot" /> API connected<div className="version">v0.6.0-alpha</div></div>
      </aside>
      <main>
        <header className="topbar">
          <div><h1>{nav.find(([key]) => key === view)?.[1]}</h1><p>{selectedWorkspace?.name ?? 'Select a workspace'}</p></div>
          <div className="top-actions">
            <select value={workspaceId} onChange={(e) => { const id = e.target.value; setWorkspaceId(id); sessionStorage.setItem('csp.workspace', id); void loadWorkspace(id) }}>
              {workspaces.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select>
            <div className="identity"><strong>{user?.full_name}</strong><small>{user?.email}</small></div>
            <button className="ghost" onClick={() => void logout()}>Sign out</button>
          </div>
        </header>
        {error ? <div className="alert">{error}</div> : null}
        {busy ? <div className="progress" /> : null}
        <section className="content">
          {view === 'overview' && <Overview tickets={tickets} clients={clients} tasks={tasks} notifications={notifications} openTickets={openTickets} urgentTickets={urgentTickets} openTasks={openTasks} unread={unread} />}
          {view === 'tickets' && <Tickets tickets={tickets} enabled={can('tickets.read')} />}
          {view === 'clients' && <Clients clients={clients} enabled={can('clients.read')} />}
          {view === 'tasks' && <Tasks tasks={tasks} enabled={can('tasks.read')} />}
          {view === 'knowledge' && <Knowledge articles={knowledge} enabled={can('knowledge.read')} />}
          {view === 'notifications' && <Notifications items={notifications} enabled={can('notifications.read')} onRead={markRead} />}
        </section>
      </main>
    </div>
  )
}

function LoginScreen({ busy, error, onLogin }: { busy: boolean; error: string; onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  function submit(e: FormEvent) { e.preventDefault(); void onLogin(email, password) }
  return <div className="login-page"><div className="login-card"><div className="brand login-brand"><span className="brand-mark">SE</span><div><strong>Support Endpoint</strong><small>Secure operations console</small></div></div><h1>Operator sign in</h1><p>Use your CSP account. Authorization remains enforced by backend workspace permissions.</p>{error ? <div className="alert">{error}</div> : null}<form onSubmit={submit}><label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></label><label>Password<input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label><button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form><small className="login-note">Tokens are kept in sessionStorage and cleared when the browser session ends.</small></div></div>
}

function Overview({ tickets, clients, tasks, notifications, openTickets, urgentTickets, openTasks, unread }: { tickets: Ticket[]; clients: Client[]; tasks: Task[]; notifications: Notification[]; openTickets: number; urgentTickets: number; openTasks: number; unread: number }) {
  const recent = notifications.slice(0, 5)
  return <><div className="metrics"><Metric label="Open tickets" value={openTickets} sub={`${tickets.length} total`} /><Metric label="Urgent" value={urgentTickets} sub="active tickets" danger={urgentTickets > 0} /><Metric label="Open tasks" value={openTasks} sub={`${tasks.length} total`} /><Metric label="Unread" value={unread} sub={`${notifications.length} notifications`} /></div><div className="grid-two"><Panel title="Recent tickets"><TicketTable tickets={tickets.slice(0, 7)} /></Panel><Panel title="Operational feed">{recent.length ? recent.map((n) => <div className="feed" key={n.id}><span className={`feed-icon ${n.read_at ? '' : 'feed-new'}`} /><div><strong>{n.title}</strong><small>{n.type.replaceAll('_', ' ')}</small></div></div>) : <Empty text="No notifications yet" />}</Panel></div><Panel title="Customer base"><div className="summary-line"><span>Active customer records</span><strong>{clients.filter((c) => c.is_active).length}</strong></div></Panel></>
}

function Tickets({ tickets, enabled }: { tickets: Ticket[]; enabled: boolean }) { return enabled ? <Panel title={`Tickets · ${tickets.length}`}><TicketTable tickets={tickets} /></Panel> : <Denied /> }
function TicketTable({ tickets }: { tickets: Ticket[] }) { return tickets.length ? <div className="table-wrap"><table><thead><tr><th>Subject</th><th>Priority</th><th>Status</th><th>Assignee</th></tr></thead><tbody>{tickets.map((t) => <tr key={t.id}><td><strong>{t.subject}</strong><small className="mono">{t.id.slice(0, 8)}</small></td><td><span className={statusClass(t.priority)}>{t.priority}</span></td><td><span className={statusClass(t.status)}>{t.status.replaceAll('_', ' ')}</span></td><td className="muted">{t.assignee_user_id ? t.assignee_user_id.slice(0, 8) : 'Unassigned'}</td></tr>)}</tbody></table></div> : <Empty text="No tickets in this workspace" /> }
function Clients({ clients, enabled }: { clients: Client[]; enabled: boolean }) { return enabled ? <Panel title={`Clients · ${clients.length}`}><div className="cards">{clients.map((c) => <article className="client-card" key={c.id}><div className="avatar">{c.full_name.slice(0, 2).toUpperCase()}</div><div><strong>{c.full_name}</strong><small>{c.primary_email ?? 'No email'}</small><small>{c.primary_phone ?? 'No phone'}</small></div><span className={c.is_active ? 'pill pill-open' : 'pill pill-closed'}>{c.is_active ? 'active' : 'inactive'}</span></article>)}</div>{clients.length === 0 ? <Empty text="No clients in this workspace" /> : null}</Panel> : <Denied /> }
function Tasks({ tasks, enabled }: { tasks: Task[]; enabled: boolean }) { return enabled ? <Panel title={`Tasks · ${tasks.length}`}><div className="task-list">{tasks.map((t) => <div className="task" key={t.id}><span className={statusClass(t.status)}>{t.status}</span><div><strong>{t.title}</strong><small>Ticket {t.ticket_id.slice(0, 8)} {t.due_at ? `· due ${new Date(t.due_at).toLocaleString()}` : ''}</small></div></div>)}</div>{tasks.length === 0 ? <Empty text="No operational tasks" /> : null}</Panel> : <Denied /> }
function Knowledge({ articles, enabled }: { articles: KnowledgeArticle[]; enabled: boolean }) { return enabled ? <Panel title={`Knowledge · ${articles.length}`}><div className="knowledge-list">{articles.map((a) => <article key={a.id}><span className={statusClass(a.status)}>{a.status}</span><h3>{a.title}</h3><p>{a.body.slice(0, 240)}{a.body.length > 240 ? '…' : ''}</p></article>)}</div>{articles.length === 0 ? <Empty text="No knowledge articles" /> : null}</Panel> : <Denied /> }
function Notifications({ items, enabled, onRead }: { items: Notification[]; enabled: boolean; onRead: (id: string) => Promise<void> }) { return enabled ? <Panel title={`Notifications · ${items.length}`}><div className="notification-list">{items.map((n) => <article key={n.id} className={n.read_at ? '' : 'unread'}><div><strong>{n.title}</strong><p>{n.body}</p><small>{n.type.replaceAll('_', ' ')} · {new Date(n.created_at).toLocaleString()}</small></div>{!n.read_at ? <button className="ghost" onClick={() => void onRead(n.id)}>Mark read</button> : <span className="muted">Read</span>}</article>)}</div>{items.length === 0 ? <Empty text="No notifications" /> : null}</Panel> : <Denied /> }
function Metric({ label, value, sub, danger = false }: { label: string; value: number; sub: string; danger?: boolean }) { return <article className={`metric ${danger ? 'metric-danger' : ''}`}><span>{label}</span><strong>{value}</strong><small>{sub}</small></article> }
function Panel({ title, children }: { title: string; children: React.ReactNode }) { return <section className="panel"><div className="panel-head"><h2>{title}</h2></div>{children}</section> }
function Empty({ text }: { text: string }) { return <div className="empty">{text}</div> }
function Denied() { return <div className="empty denied"><strong>Permission not granted</strong><span>This workspace role cannot access this surface. The UI does not bypass backend RBAC.</span></div> }
