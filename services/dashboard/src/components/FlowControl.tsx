import React, { useEffect, useMemo, useState } from 'react'
import { FileText, RefreshCw, Send } from 'lucide-react'
import { apiFetch } from '../lib/api'

type ModelTask = {
  task_id: string
  title: string
  goal: string
  task_type: string
  risk_tier: string
  owner_role: string
  status: string
  artifact_path?: string
  error_message?: string
  created_at?: string
  completed_at?: string
}

type FlowStatus = {
  agents: Record<string, { name: string; port: number; port_open: boolean; runtime_registered: boolean; healthy: boolean }>
  healthy: boolean
}

type ArtifactResponse = { path: string; content: string }

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`/api/flow${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  const data = await response.json()
  if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`)
  return data
}

function ownerForRisk(riskTier: string) {
  return riskTier === 'reputation' ? 'alpha' : riskTier === 'time_loss' ? 'beta' : 'gamma'
}

export function FlowControl() {
  const [status, setStatus] = useState<FlowStatus | null>(null)
  const [tasks, setTasks] = useState<ModelTask[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [selected, setSelected] = useState<ModelTask | null>(null)
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [artifactContent, setArtifactContent] = useState('')
  const [artifactLoading, setArtifactLoading] = useState(false)
  const [form, setForm] = useState({
    title: '',
    goal: '',
    risk_tier: 'reputation',
    task_type: 'content_prep',
    output_required: 'A concise Markdown artifact ready for human review.',
  })

  const selectedOwner = useMemo(() => selected?.owner_role || '', [selected])

  async function refresh() {
    const [nextStatus, nextTasks] = await Promise.all([
      api<FlowStatus>('/status'),
      api<{ tasks: ModelTask[] }>('/model/jobs'),
    ])
    setStatus(nextStatus)
    setTasks(nextTasks.tasks)
    if (selectedId) setSelected(await api<ModelTask>(`/model/jobs/${selectedId}`))
  }

  useEffect(() => { refresh().catch((error) => setMessage(error.message)) }, [])

  async function submitTask(event: React.FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setMessage('')
    try {
      const taskId = crypto.randomUUID()
      const riskTier = form.risk_tier
      const response = await apiFetch('/api/intake/task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: taskId,
          created_at: new Date().toISOString(),
          source: 'dashboard',
          title: form.title,
          goal: form.goal,
          task_type: form.task_type,
          risk_tier: riskTier,
          preferred_owner: ownerForRisk(riskTier),
          owner_role: ownerForRisk(riskTier),
          inputs: {},
          output_required: form.output_required,
          review_required: riskTier === 'downtime_security_money',
          rollback_required: false,
          status: 'pending',
        }),
      })
      const data = await response.json()
      if (!response.ok || data.status !== 'accepted') throw new Error(data.error || data.detail || 'Task was not accepted')
      setSelectedId(data.job_id)
      setForm({ ...form, title: '', goal: '' })
      await refresh()
      setMessage(`Submitted ${data.job_id}. Refresh to follow its live status.`)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Submit failed')
    } finally {
      setSubmitting(false)
    }
  }

  async function loadTask(taskId: string) {
    setSelectedId(taskId)
    setArtifactContent('')
    setSelected(await api<ModelTask>(`/model/jobs/${taskId}`))
  }

  async function loadArtifact() {
    if (!selected) return
    setArtifactLoading(true)
    setMessage('')
    try {
      const artifact = await api<ArtifactResponse>(`/model/jobs/${selected.task_id}/artifact`)
      setArtifactContent(artifact.content)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Output is not available yet')
    } finally {
      setArtifactLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-950">FLOW Control</h2>
          <p className="text-sm text-gray-600">Provider-backed tasks. Output stays here for review before any external action.</p>
        </div>
        <button type="button" onClick={() => refresh().catch((error) => setMessage(error.message))} className="inline-flex h-10 items-center gap-2 rounded-md border border-gray-300 bg-white px-3 text-sm font-medium text-gray-800 hover:bg-gray-50">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {message && <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">{message}</div>}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {(['alpha', 'beta', 'gamma'] as const).map((role) => {
          const agent = status?.agents?.[role]
          return <div key={role} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between"><div><h3 className="text-lg font-semibold text-gray-950">{agent?.name || role}</h3><p className="text-sm text-gray-600">Internal runtime</p></div><span className={`h-3 w-3 rounded-full ${agent?.healthy ? 'bg-emerald-500' : 'bg-red-500'}`} /></div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm"><span className="text-gray-500">Port</span><span className="font-medium text-gray-900">{agent?.port_open ? 'ready' : 'unavailable'}</span><span className="text-gray-500">Runtime</span><span className="font-medium text-gray-900">{agent?.runtime_registered ? 'ready' : 'unavailable'}</span></div>
          </div>
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[420px_1fr]">
        <form onSubmit={submitTask} className="rounded-lg border border-gray-200 bg-white p-4">
          <h3 className="text-lg font-semibold text-gray-950">Run a model task</h3>
          <p className="mt-1 text-sm text-gray-600">The Canon is supplied to the model. This does not publish, schedule, or change an external account.</p>
          <div className="mt-4 space-y-4">
            <input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} className="h-10 w-full rounded-md border border-gray-300 px-3 text-sm" placeholder="Task title" required />
            <textarea value={form.goal} onChange={(event) => setForm({ ...form, goal: event.target.value })} className="min-h-[120px] w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="Observable goal and source material to use" required />
            <select value={form.task_type} onChange={(event) => setForm({ ...form, task_type: event.target.value })} className="h-10 w-full rounded-md border border-gray-300 px-3 text-sm">
              <option value="content_prep">Content preparation</option><option value="rewrite">Rewrite</option><option value="classification">Classification</option><option value="implementation">Implementation plan</option><option value="skill_extraction">Extract a reusable skill</option><option value="healthcheck">Health check</option>
            </select>
            <textarea value={form.output_required} onChange={(event) => setForm({ ...form, output_required: event.target.value })} className="min-h-[84px] w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="What should be delivered?" required />
            <select value={form.risk_tier} onChange={(event) => setForm({ ...form, risk_tier: event.target.value })} className="h-10 w-full rounded-md border border-gray-300 px-3 text-sm">
              <option value="reputation">Internal review (Alpha)</option><option value="time_loss">Low-risk production (Beta)</option><option value="downtime_security_money">Hold for approval (Gamma)</option>
            </select>
            <button type="submit" disabled={submitting} className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-gray-950 px-3 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-60"><Send className="h-4 w-4" />{submitting ? 'Submitting…' : 'Submit for review'}</button>
          </div>
        </form>

        <div className="rounded-lg border border-gray-200 bg-white"><div className="border-b border-gray-200 p-4"><h3 className="text-lg font-semibold text-gray-950">Model tasks</h3></div><div className="grid grid-cols-1 lg:grid-cols-[1fr_420px]"><div className="max-h-[620px] overflow-auto">{tasks.length ? tasks.map((task) => <button type="button" key={task.task_id} onClick={() => loadTask(task.task_id).catch((error) => setMessage(error.message))} className={`block w-full border-b border-gray-100 px-4 py-3 text-left hover:bg-gray-50 ${selectedId === task.task_id ? 'bg-gray-50' : ''}`}><div className="flex items-center justify-between gap-3"><span className="font-medium text-gray-950">{task.title}</span><span className="text-xs uppercase text-gray-500">{task.status}</span></div><div className="mt-1 text-xs text-gray-500">{task.owner_role} · {task.task_id}</div></button>) : <div className="p-4 text-sm text-gray-500">No model tasks yet.</div>}</div><div className="border-t border-gray-200 p-4 lg:border-l lg:border-t-0">{selected ? <div className="space-y-4"><div><h4 className="font-semibold text-gray-950">{selected.title}</h4><p className="mt-1 text-sm text-gray-600">{selected.goal}</p><p className="mt-2 text-xs text-gray-500">{selected.task_id}</p></div><div className="grid grid-cols-2 gap-2 text-sm"><span className="text-gray-500">Owner</span><span className="font-medium text-gray-900">{selectedOwner}</span><span className="text-gray-500">Status</span><span className="font-medium text-gray-900">{selected.status}</span><span className="text-gray-500">Type</span><span className="font-medium text-gray-900">{selected.task_type}</span></div>{selected.error_message && <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-950">{selected.error_message}</div>}{selected.artifact_path && <div className="rounded-md bg-gray-50 p-3 text-sm"><div className="mb-1 flex items-center gap-2 font-medium text-gray-950"><FileText className="h-4 w-4" />Output</div><button type="button" onClick={() => loadArtifact()} disabled={artifactLoading} className="mt-2 inline-flex h-9 items-center rounded-md border border-gray-300 px-3 text-sm font-medium text-gray-800 hover:bg-white disabled:opacity-50">{artifactLoading ? 'Loading output…' : 'Open output'}</button>{artifactContent && <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-white p-3 text-xs text-gray-800">{artifactContent}</pre>}</div>}</div> : <div className="text-sm text-gray-500">Select a model task.</div>}</div></div></div>
      </div>
    </div>
  )
}
