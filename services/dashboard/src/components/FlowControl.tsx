import React, { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, FileText, PauseCircle, RefreshCw, Send, ShieldCheck } from 'lucide-react'
import { apiFetch } from '../lib/api'

type QueueName = 'pending' | 'active' | 'completed' | 'escalated' | 'blocked'

type FlowTask = {
  task_id: string
  title: string
  goal: string
  risk_tier: string
  owner_role: string
  status: string
  queue: string
  artifact_path?: string
  review_artifacts_ready?: boolean
  review_artifacts?: Record<string, string>
  audit?: Array<Record<string, unknown>>
}

type FlowStatus = {
  agents: Record<string, { name: string; port: number; port_open: boolean; runtime_registered: boolean; healthy: boolean }>
  queues: Record<string, number>
  state_root: string
  healthy: boolean
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`/api/flow${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`)
  }
  return data
}

export function FlowControl() {
  const [status, setStatus] = useState<FlowStatus | null>(null)
  const [tasks, setTasks] = useState<FlowTask[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [selected, setSelected] = useState<FlowTask | null>(null)
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({
    title: '',
    goal: '',
    risk_tier: 'reputation',
  })

  const selectedQueue = useMemo(() => selected?.queue || '', [selected])

  async function refresh() {
    const [nextStatus, nextTasks] = await Promise.all([
      api<FlowStatus>('/status'),
      api<{ tasks: FlowTask[] }>('/tasks'),
    ])
    setStatus(nextStatus)
    setTasks(nextTasks.tasks)
    if (selectedId) {
      const task = await api<FlowTask>(`/tasks/${selectedId}`)
      setSelected(task)
    }
  }

  useEffect(() => {
    refresh().catch((error) => setMessage(error.message))
  }, [])

  async function submitTask(event: React.FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setMessage('')
    try {
      const data = await api<{ task: FlowTask }>('/submit', {
        method: 'POST',
        body: JSON.stringify({ ...form, source: 'landing_page' }),
      })
      setSelectedId(data.task.task_id)
      setSelected(data.task)
      setForm({ title: '', goal: '', risk_tier: form.risk_tier })
      await refresh()
      setMessage(`Submitted ${data.task.task_id}`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Submit failed')
    } finally {
      setSubmitting(false)
    }
  }

  async function loadTask(taskId: string) {
    setSelectedId(taskId)
    setSelected(await api<FlowTask>(`/tasks/${taskId}`))
  }

  async function approveGamma() {
    if (!selected) return
    const data = await api<{ task: FlowTask }>('/approve', {
      method: 'POST',
      body: JSON.stringify({ task_id: selected.task_id, actor: 'landing_page' }),
    })
    setSelected(data.task)
    await refresh()
    setMessage(`Approved ${selected.task_id}`)
  }

  async function blockSelected() {
    if (!selected) return
    const reason = window.prompt('Block reason')
    if (!reason) return
    const data = await api<{ task: FlowTask }>('/block', {
      method: 'POST',
      body: JSON.stringify({ task_id: selected.task_id, reason, actor: 'landing_page' }),
    })
    setSelected(data.task)
    await refresh()
    setMessage(`Blocked ${selected.task_id}`)
  }

  const queueNames: QueueName[] = ['pending', 'active', 'completed', 'escalated', 'blocked']

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-950">FLOW Control</h2>
          <p className="text-sm text-gray-600">{status?.state_root || 'Loading state root'}</p>
        </div>
        <button
          type="button"
          onClick={() => refresh().catch((error) => setMessage(error.message))}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-gray-300 bg-white px-3 text-sm font-medium text-gray-800 hover:bg-gray-50"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {message && <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{message}</div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {(['alpha', 'beta', 'gamma'] as const).map((role) => {
          const agent = status?.agents?.[role]
          return (
            <div key={role} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-950">{agent?.name || role}</h3>
                  <p className="text-sm text-gray-600">Port {agent?.port}</p>
                </div>
                <span className={`h-3 w-3 rounded-full ${agent?.healthy ? 'bg-emerald-500' : 'bg-red-500'}`} />
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                <span className="text-gray-500">Port</span>
                <span className="font-medium text-gray-900">{agent?.port_open ? 'open' : 'closed'}</span>
                <span className="text-gray-500">Runtime</span>
                <span className="font-medium text-gray-900">{agent?.runtime_registered ? 'registered' : 'missing'}</span>
              </div>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {queueNames.map((name) => (
          <div key={name} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="text-sm capitalize text-gray-600">{name}</div>
            <div className="mt-1 text-3xl font-semibold text-gray-950">{status?.queues?.[name] || 0}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[420px_1fr]">
        <form onSubmit={submitTask} className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="text-lg font-semibold text-gray-950">Submit Task</h3>
          <div className="mt-4 space-y-4">
            <input
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              className="h-10 w-full rounded-md border border-gray-300 px-3 text-sm"
              placeholder="Task title"
              required
            />
            <textarea
              value={form.goal}
              onChange={(event) => setForm({ ...form, goal: event.target.value })}
              className="min-h-[120px] w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder="Observable goal"
              required
            />
            <select
              value={form.risk_tier}
              onChange={(event) => setForm({ ...form, risk_tier: event.target.value })}
              className="h-10 w-full rounded-md border border-gray-300 px-3 text-sm"
            >
              <option value="reputation">Reputation to Alpha</option>
              <option value="time_loss">Time loss to Beta</option>
              <option value="downtime_security_money">Downtime/security/money to Gamma</option>
            </select>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-gray-950 px-3 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-60"
            >
              <Send className="h-4 w-4" />
              Submit
            </button>
          </div>
        </form>

        <div className="rounded-lg border border-gray-200 bg-white">
          <div className="border-b border-gray-200 p-4">
            <h3 className="text-lg font-semibold text-gray-950">Tasks</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_420px]">
            <div className="max-h-[620px] overflow-auto">
              {tasks.map((task) => (
                <button
                  type="button"
                  key={task.task_id}
                  onClick={() => loadTask(task.task_id).catch((error) => setMessage(error.message))}
                  className={`block w-full border-b border-gray-100 px-4 py-3 text-left hover:bg-gray-50 ${
                    selectedId === task.task_id ? 'bg-gray-50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-gray-950">{task.title}</span>
                    <span className="text-xs uppercase text-gray-500">{task.queue}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">{task.task_id}</div>
                </button>
              ))}
            </div>

            <div className="border-t border-gray-200 p-4 lg:border-l lg:border-t-0">
              {selected ? (
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-gray-950">{selected.title}</h4>
                    <p className="mt-1 text-sm text-gray-600">{selected.goal}</p>
                    <p className="mt-2 text-xs text-gray-500">{selected.task_id}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <span className="text-gray-500">Owner</span>
                    <span className="font-medium text-gray-900">{selected.owner_role}</span>
                    <span className="text-gray-500">Status</span>
                    <span className="font-medium text-gray-900">{selected.status}</span>
                    <span className="text-gray-500">Queue</span>
                    <span className="font-medium text-gray-900">{selectedQueue}</span>
                  </div>
                  {selected.artifact_path && (
                    <div className="rounded-md bg-gray-50 p-3 text-sm">
                      <div className="mb-1 flex items-center gap-2 font-medium text-gray-950">
                        <FileText className="h-4 w-4" />
                        Artifact
                      </div>
                      <code className="break-all text-xs text-gray-700">{selected.artifact_path}</code>
                    </div>
                  )}
                  {selected.owner_role === 'gamma' && (
                    <div className="rounded-md border border-red-200 bg-red-50 p-3">
                      <div className="mb-2 flex items-center gap-2 font-medium text-red-950">
                        <ShieldCheck className="h-4 w-4" />
                        Gamma Approval
                      </div>
                      <div className="space-y-1 text-xs text-red-900">
                        {Object.entries(selected.review_artifacts || {}).map(([key, value]) => (
                          <div key={key}>
                            {key}: <code className="break-all">{value}</code>
                          </div>
                        ))}
                      </div>
                      <button
                        type="button"
                        onClick={() => approveGamma().catch((error) => setMessage(error.message))}
                        disabled={!selected.review_artifacts_ready || selected.status !== 'review_required'}
                        className="mt-3 inline-flex h-9 items-center gap-2 rounded-md bg-red-700 px-3 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        Approve
                      </button>
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => blockSelected().catch((error) => setMessage(error.message))}
                    className="inline-flex h-9 items-center gap-2 rounded-md border border-gray-300 px-3 text-sm font-medium text-gray-800 hover:bg-gray-50"
                  >
                    <PauseCircle className="h-4 w-4" />
                    Block
                  </button>
                  <div className="text-xs text-gray-500">Audit events: {selected.audit?.length || 0}</div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">Select a task.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
