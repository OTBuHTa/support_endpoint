import { FormEvent, useEffect, useState } from 'react'
import { api, clearTokens, saveTokens, tokenPair } from './api'
import type { PortalAccount, PortalMessage, PortalTicket, TokenPair, User } from './types'

export default function PortalApp() {
  const [authenticated, setAuthenticated] = useState(Boolean(tokenPair()))
  const [user, setUser] = useState<User | null>(null)
  const [accounts, setAccounts] = useState<PortalAccount[]>([])
  const [linkId, setLinkId] = useState('')
  const [tickets, setTickets] = useState<PortalTicket[]>([])
  const [selectedTicket, setSelectedTicket] = useState<PortalTicket | null>(null)
  const [messages, setMessages] = useState<PortalMessage[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function loadAccounts() {
    const [me, linked] = await Promise.all([
      api<User>('/api/v1/auth/me'),
      api<PortalAccount[]>('/api/v1/portal/accounts'),
    ])
    setUser(me)
    setAccounts(linked)
    const selected = linked.some((item) => item.link_id === linkId)
      ? linkId
      : (linked[0]?.link_id ?? '')
    setLinkId(selected)
    if (selected) await loadTickets(selected)
  }

  async function loadTickets(selectedLink: string) {
    const items = await api<PortalTicket[]>(`/api/v1/portal/accounts/${selectedLink}/tickets`)
    setTickets(items)
    if (selectedTicket) {
      const refreshed = items.find((item) => item.id === selectedTicket.id) ?? null
      setSelectedTicket(refreshed)
      if (refreshed) await loadMessages(selectedLink, refreshed.id)
    }
  }

  async function loadMessages(selectedLink: string, ticketId: string) {
    const items = await api<PortalMessage[]>(
      `/api/v1/portal/accounts/${selectedLink}/tickets/${ticketId}/messages`,
    )
    setMessages(items)
  }

  useEffect(() => {
    if (!authenticated) return
    setBusy(true)
    void loadAccounts()
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Failed to load portal')
        if ((e instanceof Error ? e.message : '').startsWith('401')) {
          clearTokens()
          setAuthenticated(false)
        }
      })
      .finally(() => setBusy(false))
  }, [authenticated])

  async function login(email: string, password: string) {
    setBusy(true)
    setError('')
    try {
      const tokens = await api<TokenPair>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      saveTokens(tokens)
      setAuthenticated(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  async function logout() {
    const pair = tokenPair()
    try {
      if (pair) {
        await api<void>('/api/v1/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: pair.refresh_token }),
        })
      }
    } catch {
      // Local logout still proceeds.
    }
    clearTokens()
    setAuthenticated(false)
    setUser(null)
    setAccounts([])
    setTickets([])
    setSelectedTicket(null)
  }

  async function createTicket(subject: string, description: string, priority: string) {
    if (!linkId) return
    setBusy(true)
    try {
      const created = await api<PortalTicket>(`/api/v1/portal/accounts/${linkId}/tickets`, {
        method: 'POST',
        body: JSON.stringify({ subject, description, priority }),
      })
      await loadTickets(linkId)
      setSelectedTicket(created)
      setMessages([])
    } finally {
      setBusy(false)
    }
  }

  async function openTicket(ticket: PortalTicket) {
    setSelectedTicket(ticket)
    setBusy(true)
    try {
      await loadMessages(linkId, ticket.id)
    } finally {
      setBusy(false)
    }
  }

  async function reply(body: string) {
    if (!selectedTicket || !linkId) return
    setBusy(true)
    try {
      await api(`/api/v1/portal/accounts/${linkId}/tickets/${selectedTicket.id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ body }),
      })
      await loadMessages(linkId, selectedTicket.id)
    } finally {
      setBusy(false)
    }
  }

  if (!authenticated) return <PortalLogin busy={busy} error={error} onLogin={login} />

  const account = accounts.find((item) => item.link_id === linkId)
  return (
    <div className="portal-shell">
      <header className="portal-topbar">
        <div className="brand">
          <span className="brand-mark">SE</span>
          <div><strong>Support Endpoint</strong><small>Customer portal</small></div>
        </div>
        <div className="top-actions">
          {accounts.length > 1 ? (
            <select value={linkId} onChange={(e) => {
              const value = e.target.value
              setLinkId(value)
              setSelectedTicket(null)
              setMessages([])
              void loadTickets(value)
            }}>
              {accounts.map((item) => (
                <option key={item.link_id} value={item.link_id}>{item.workspace_name}</option>
              ))}
            </select>
          ) : null}
          <div className="identity"><strong>{user?.full_name}</strong><small>{user?.email}</small></div>
          <button className="ghost" onClick={() => void logout()}>Sign out</button>
        </div>
      </header>
      {busy ? <div className="progress" /> : null}
      {error ? <div className="alert">{error}</div> : null}
      <main className="portal-content">
        <section className="portal-hero">
          <div><span className="eyebrow">Customer support</span><h1>{account?.workspace_name ?? 'Support portal'}</h1><p>{account?.client_name ?? 'Linked customer account'}</p></div>
          <CreateTicket onCreate={createTicket} disabled={!linkId || busy} />
        </section>
        {accounts.length === 0 ? (
          <div className="empty denied"><strong>No linked customer account</strong><span>An operator must explicitly link this login to a CRM client record.</span></div>
        ) : (
          <div className="portal-grid">
            <section className="panel portal-ticket-list">
              <div className="panel-head"><h2>Your requests · {tickets.length}</h2></div>
              {tickets.length ? tickets.map((ticket) => (
                <button key={ticket.id} className={`portal-ticket ${selectedTicket?.id === ticket.id ? 'portal-ticket-active' : ''}`} onClick={() => void openTicket(ticket)}>
                  <div><strong>{ticket.subject}</strong><small>{ticket.id.slice(0, 8)}</small></div>
                  <span className={`pill pill-${ticket.status.replaceAll('_', '-')}`}>{ticket.status}</span>
                </button>
              )) : <div className="empty">No support requests yet</div>}
            </section>
            <section className="panel portal-thread">
              <div className="panel-head"><h2>{selectedTicket?.subject ?? 'Conversation'}</h2></div>
              {!selectedTicket ? <div className="empty">Select a request to view its conversation</div> : <>
                <div className="message-list">
                  {messages.length ? messages.map((message) => (
                    <article key={message.id} className={`message ${message.direction === 'inbound' ? 'message-customer' : 'message-support'}`}>
                      <small>{message.direction === 'inbound' ? 'You' : 'Support'} · {new Date(message.created_at).toLocaleString()}</small>
                      <p>{message.body}</p>
                    </article>
                  )) : <div className="empty">No messages yet</div>}
                </div>
                <ReplyForm onReply={reply} disabled={busy} />
              </>}
            </section>
          </div>
        )}
      </main>
    </div>
  )
}

function PortalLogin({ busy, error, onLogin }: { busy: boolean; error: string; onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  function submit(e: FormEvent) { e.preventDefault(); void onLogin(email, password) }
  return <div className="login-page"><div className="login-card"><div className="brand login-brand"><span className="brand-mark">SE</span><div><strong>Support Endpoint</strong><small>Customer portal</small></div></div><h1>Customer sign in</h1><p>Sign in with the account linked to your customer record.</p>{error ? <div className="alert">{error}</div> : null}<form onSubmit={submit}><label>Email<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label><label>Password<input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label><button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button></form></div></div>
}

function CreateTicket({ onCreate, disabled }: { onCreate: (subject: string, description: string, priority: string) => Promise<void>; disabled: boolean }) {
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('medium')
  async function submit(e: FormEvent) {
    e.preventDefault()
    await onCreate(subject, description, priority)
    setSubject('')
    setDescription('')
    setPriority('medium')
    setOpen(false)
  }
  if (!open) return <button className="primary" disabled={disabled} onClick={() => setOpen(true)}>New request</button>
  return <form className="portal-create" onSubmit={(e) => void submit(e)}><input required maxLength={255} placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} /><textarea maxLength={20000} placeholder="Describe the issue" value={description} onChange={(e) => setDescription(e.target.value)} /><select value={priority} onChange={(e) => setPriority(e.target.value)}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select><div><button className="primary" disabled={disabled}>Create</button><button type="button" className="ghost" onClick={() => setOpen(false)}>Cancel</button></div></form>
}

function ReplyForm({ onReply, disabled }: { onReply: (body: string) => Promise<void>; disabled: boolean }) {
  const [body, setBody] = useState('')
  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!body.trim()) return
    await onReply(body.trim())
    setBody('')
  }
  return <form className="reply-form" onSubmit={(e) => void submit(e)}><textarea required maxLength={50000} placeholder="Write a reply…" value={body} onChange={(e) => setBody(e.target.value)} /><button className="primary" disabled={disabled || !body.trim()}>Send reply</button></form>
}
