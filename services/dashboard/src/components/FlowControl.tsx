import React, { useEffect, useMemo, useState } from 'react'
import {
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Circle,
  Clock3,
  Copy,
  FileText,
  Loader2,
  RefreshCw,
  Send,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  Zap,
} from 'lucide-react'
import { apiFetch } from '../lib/api'

type ModelTask = {
  task_id: string
  source_task_id?: string
  title: string
  goal: string
  task_type: string
  risk_tier: string
  owner_role: 'alpha' | 'beta' | 'gamma' | string
  status: string
  artifact_path?: string
  error_message?: string
  created_at?: string
  updated_at?: string
  completed_at?: string
}

type AgentStatus = {
  name: string
  port: number
  port_open: boolean
  runtime_registered: boolean
  healthy: boolean
  upstream_repository?: string
  upstream_commit?: string
}

type FlowStatus = {
  agents: Record<string, AgentStatus>
  queues?: Record<string, number>
  healthy: boolean
}

type ReviewStatus = {
  all_valid: boolean
  can_execute: boolean
  diff_present: boolean
  diff_valid: boolean
  review_present: boolean
  review_valid: boolean
  rollback_present: boolean
  rollback_valid: boolean
  review_approver?: { name?: string; date?: string }
}

type ArtifactResponse = { path: string; content: string }
type TaskFilter = 'all' | 'in_flight' | 'review' | 'ready' | 'failed'

const agentDisplay = {
  alpha: {
    name: 'Hermes Agent',
    lane: 'Alpha',
    purpose: 'Public-facing drafts and reputation-sensitive work',
  },
  beta: {
    name: 'OpenClaw',
    lane: 'Beta',
    purpose: 'Analysis, production, and file-aware execution',
  },
  gamma: {
    name: 'Agent Zero',
    lane: 'Gamma',
    purpose: 'Approval-gated implementation and high-risk work',
  },
} as const

const statusCopy: Record<string, string> = {
  pending: 'Brief received',
  validated: 'Routing',
  queued: 'Queued',
  active: 'Working',
  review_required: 'Approval required',
  completed: 'Ready for review',
  failed: 'Needs attention',
  blocked: 'Blocked',
}

const taskTypes = [
  ['content_prep', 'Content preparation'],
  ['rewrite', 'Rewrite'],
  ['classification', 'Research or classification'],
  ['implementation', 'Implementation'],
  ['skill_extraction', 'Extract a reusable skill'],
  ['healthcheck', 'Health check'],
]

const riskOptions = [
  ['reputation', 'Hermes Agent', 'Public-facing or reputation-sensitive work'],
  ['time_loss', 'OpenClaw', 'Analysis, production, or file-aware work'],
  ['downtime_security_money', 'Agent Zero', 'Deployment, security, money, or downtime risk'],
]

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || data.error || `Request failed with HTTP ${response.status}`)
  }
  return data
}

function ownerForRisk(riskTier: string) {
  if (riskTier === 'reputation') return 'alpha'
  if (riskTier === 'time_loss') return 'beta'
  return 'gamma'
}

function formatDate(value?: string) {
  if (!value) return 'Not recorded'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function shortId(value: string) {
  return value.slice(0, 8)
}

function statusTone(status: string) {
  if (status === 'completed') return 'bg-emerald-50 text-emerald-800'
  if (status === 'failed' || status === 'blocked') return 'bg-red-50 text-red-800'
  if (status === 'review_required') return 'bg-amber-50 text-amber-900'
  if (status === 'active') return 'bg-sky-50 text-sky-800'
  return 'bg-stone-100 text-stone-700'
}

function lifecycleFor(task: ModelTask | null) {
  const requiresApproval = task?.risk_tier === 'downtime_security_money'
  const steps = [
    { id: 'brief', label: 'Brief' },
    { id: 'route', label: 'Routed' },
    ...(requiresApproval ? [{ id: 'approval', label: 'Approval' }] : []),
    { id: 'work', label: 'Working' },
    { id: 'ready', label: 'Ready' },
  ]

  if (!task) return { steps, current: -1, failed: false }
  if (task.status === 'failed' || task.status === 'blocked') {
    return { steps, current: Math.max(1, steps.findIndex((step) => step.id === 'work')), failed: true }
  }
  if (task.status === 'completed') return { steps, current: steps.length - 1, failed: false }
  if (task.status === 'active') {
    return { steps, current: steps.findIndex((step) => step.id === 'work'), failed: false }
  }
  if (task.status === 'review_required') {
    return { steps, current: steps.findIndex((step) => step.id === 'approval'), failed: false }
  }
  if (task.status === 'queued' || task.status === 'validated') {
    return { steps, current: 1, failed: false }
  }
  return { steps, current: 0, failed: false }
}

function reviewTemplates(task: ModelTask | null) {
  const title = task?.title || 'Approved FLOW task'
  const today = new Date().toISOString().slice(0, 10)
  return {
    diff: `--- a/proposed-change\n+++ b/proposed-change\n@@ -1,1 +1,1 @@\n-Current approved state\n+${title}\n`,
    review: `# Review\n\n## What changed\n${title}\n\n## Why\nState why this change is required.\n\n## Impact\nState the expected impact and affected systems.\n\n## Testing\nState the checks that must pass.\n\n## Rollback\nReference the rollback actions below.\n\n## Risks\nState the remaining risks.\n\n## Approver\nApprover: Erik H Bush, ${today}\n`,
    rollback: `# Rollback Plan\n\n## Detection\nState the exact signal that requires rollback.\n\n## Immediate Actions\nState the exact steps that restore the last known good state.\n\n## Validation\nState how the restored state will be verified.\n`,
  }
}

export function FlowControl() {
  const [status, setStatus] = useState<FlowStatus | null>(null)
  const [tasks, setTasks] = useState<ModelTask[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [selected, setSelected] = useState<ModelTask | null>(null)
  const [notice, setNotice] = useState<{ tone: 'info' | 'error' | 'success'; text: string } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [artifactContent, setArtifactContent] = useState('')
  const [artifactLoading, setArtifactLoading] = useState(false)
  const [filter, setFilter] = useState<TaskFilter>('all')
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | null>(null)
  const [reviewSubmitting, setReviewSubmitting] = useState(false)
  const [approvalRunning, setApprovalRunning] = useState(false)
  const [reviewPack, setReviewPack] = useState(reviewTemplates(null))
  const [form, setForm] = useState({
    title: '',
    goal: '',
    risk_tier: 'reputation',
    task_type: 'content_prep',
    output_required: 'A finished Markdown artifact ready for human review.',
  })

  const selectedOwner = selected?.owner_role || ownerForRisk(form.risk_tier)
  const lifecycle = lifecycleFor(selected)

  const filteredTasks = useMemo(() => {
    if (filter === 'all') return tasks
    if (filter === 'in_flight') return tasks.filter((task) => ['pending', 'validated', 'queued', 'active'].includes(task.status))
    if (filter === 'review') return tasks.filter((task) => task.status === 'review_required')
    if (filter === 'ready') return tasks.filter((task) => task.status === 'completed')
    return tasks.filter((task) => ['failed', 'blocked'].includes(task.status))
  }, [filter, tasks])

  const taskCounts = useMemo(
    () => ({
      in_flight: tasks.filter((task) => ['pending', 'validated', 'queued', 'active'].includes(task.status)).length,
      review: tasks.filter((task) => task.status === 'review_required').length,
      ready: tasks.filter((task) => task.status === 'completed').length,
      failed: tasks.filter((task) => ['failed', 'blocked'].includes(task.status)).length,
    }),
    [tasks],
  )

  async function refresh(options: { quiet?: boolean } = {}) {
    if (!options.quiet) setRefreshing(true)
    try {
      const [nextStatus, nextTasks] = await Promise.all([
        api<FlowStatus>('/flow/status'),
        api<{ tasks: ModelTask[] }>('/flow/model/jobs'),
      ])
      setStatus(nextStatus)
      setTasks(nextTasks.tasks)

      const nextSelectedId = selectedId || nextTasks.tasks[0]?.task_id
      if (nextSelectedId) {
        const detail = await api<ModelTask>(`/flow/model/jobs/${nextSelectedId}`)
        setSelectedId(nextSelectedId)
        setSelected(detail)
      }
    } catch (error) {
      setNotice({
        tone: 'error',
        text: error instanceof Error ? error.message : 'The task workspace could not refresh.',
      })
    } finally {
      if (!options.quiet) setRefreshing(false)
    }
  }

  useEffect(() => {
    refresh()
    const interval = window.setInterval(() => refresh({ quiet: true }), 5000)
    return () => window.clearInterval(interval)
  }, [selectedId])

  useEffect(() => {
    setArtifactContent('')
    setReviewStatus(null)
    setReviewPack(reviewTemplates(selected))
    if (selected?.status === 'review_required') {
      loadReviewStatus(selected.task_id).catch(() => undefined)
    }
  }, [selected?.task_id])

  async function submitTask(event: React.FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setNotice(null)
    try {
      const taskId = crypto.randomUUID()
      const riskTier = form.risk_tier
      const owner = ownerForRisk(riskTier)
      const data = await api<{
        status: string
        job_id?: string
        error?: string
      }>('/intake/task', {
        method: 'POST',
        body: JSON.stringify({
          task_id: taskId,
          created_at: new Date().toISOString(),
          source: 'dashboard',
          title: form.title.trim(),
          goal: form.goal.trim(),
          task_type: form.task_type,
          risk_tier: riskTier,
          preferred_owner: owner,
          owner_role: owner,
          inputs: {},
          output_required: form.output_required.trim(),
          review_required: riskTier === 'downtime_security_money',
          rollback_required: riskTier === 'downtime_security_money',
          status: 'pending',
        }),
      })
      if (data.status !== 'accepted' || !data.job_id) {
        throw new Error(data.error || 'The task was not accepted.')
      }

      setSelectedId(data.job_id)
      setForm((current) => ({ ...current, title: '', goal: '' }))
      setNotice({
        tone: 'success',
        text: riskTier === 'downtime_security_money'
          ? 'The task is waiting for its review pack and approval.'
          : 'The task is routed and running.',
      })
      await refresh({ quiet: true })
    } catch (error) {
      setNotice({
        tone: 'error',
        text: error instanceof Error ? error.message : 'The task could not be submitted.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  async function loadTask(taskId: string) {
    setSelectedId(taskId)
    setArtifactContent('')
    setSelected(await api<ModelTask>(`/flow/model/jobs/${taskId}`))
  }

  async function loadArtifact() {
    if (!selected) return
    setArtifactLoading(true)
    setNotice(null)
    try {
      const artifact = await api<ArtifactResponse>(`/flow/model/jobs/${selected.task_id}/artifact`)
      setArtifactContent(artifact.content)
    } catch (error) {
      setNotice({
        tone: 'error',
        text: error instanceof Error ? error.message : 'The output is not available yet.',
      })
    } finally {
      setArtifactLoading(false)
    }
  }

  async function loadReviewStatus(taskId: string) {
    const next = await api<ReviewStatus>(`/agent-zero/reviews/${taskId}/status`)
    setReviewStatus(next)
  }

  async function submitReviewPack() {
    if (!selected) return
    setReviewSubmitting(true)
    setNotice(null)
    try {
      await api(`/agent-zero/reviews/${selected.task_id}/submit`, {
        method: 'POST',
        body: JSON.stringify(reviewPack),
      })
      await loadReviewStatus(selected.task_id)
      setNotice({ tone: 'success', text: 'The review pack passed validation and is ready for approval.' })
    } catch (error) {
      setNotice({
        tone: 'error',
        text: error instanceof Error ? error.message : 'The review pack did not pass validation.',
      })
    } finally {
      setReviewSubmitting(false)
    }
  }

  async function approveAndRun() {
    if (!selected) return
    setApprovalRunning(true)
    setNotice(null)
    try {
      const response = await api<{ status: string; error?: string }>(`/agent-zero/execute`, {
        method: 'POST',
        body: JSON.stringify({
          job_id: selected.task_id,
          task_id: selected.source_task_id || selected.task_id,
          action: 'execute',
        }),
      })
      if (response.status !== 'allowed') throw new Error(response.error || 'Execution was not approved.')
      setNotice({ tone: 'success', text: 'Approval recorded. Agent Zero is now working on the task.' })
      await refresh({ quiet: true })
    } catch (error) {
      setNotice({
        tone: 'error',
        text: error instanceof Error ? error.message : 'The approved task could not start.',
      })
    } finally {
      setApprovalRunning(false)
    }
  }

  function reuseTask() {
    if (!selected) return
    setForm({
      title: `${selected.title} copy`,
      goal: selected.goal,
      task_type: selected.task_type,
      risk_tier: selected.risk_tier,
      output_required: 'A finished Markdown artifact ready for human review.',
    })
    document.getElementById('new-task')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="mx-auto max-w-[1500px] px-5 pb-16 pt-8 sm:px-8 lg:px-10 lg:pt-10">
      <section className="grid gap-8 border-b border-flow-line pb-9 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="mb-3 text-sm font-semibold text-flow-accent-deep">Task workspace</p>
          <h1 className="max-w-4xl text-4xl font-semibold leading-[1.02] tracking-[-0.048em] text-flow-ink sm:text-5xl">
            Give the work a clear path from request to result.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-flow-muted">
            Submit the brief, follow the assigned agent, handle approvals, and inspect the finished artifact in one place.
          </p>
        </div>
        <button
          type="button"
          onClick={() => refresh()}
          disabled={refreshing}
          className="flow-button inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-flow-line bg-flow-surface px-4 text-sm font-semibold text-flow-ink disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </section>

      {notice && (
        <div
          role="status"
          className={`mt-6 flex items-start gap-3 rounded-xl px-4 py-3 text-sm ${
            notice.tone === 'error'
              ? 'border border-red-200 bg-red-50 text-red-900'
              : notice.tone === 'success'
                ? 'border border-emerald-200 bg-emerald-50 text-emerald-900'
                : 'border border-sky-200 bg-sky-50 text-sky-900'
          }`}
        >
          {notice.tone === 'error' ? (
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{notice.text}</span>
        </div>
      )}

      <section aria-label="Agent health" className="mt-7 grid gap-3 lg:grid-cols-3">
        {(['alpha', 'beta', 'gamma'] as const).map((role) => {
          const agent = status?.agents?.[role]
          const display = agentDisplay[role]
          return (
            <article key={role} className="flow-surface rounded-xl px-5 py-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-flow-mono text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-flow-muted">
                      {display.lane}
                    </span>
                    <span className={`h-2 w-2 rounded-full ${agent?.healthy ? 'bg-emerald-500' : 'bg-red-500'}`} />
                  </div>
                  <h2 className="mt-2 text-lg font-semibold tracking-[-0.025em] text-flow-ink">
                    {agent?.name || display.name}
                  </h2>
                  <p className="mt-1 text-sm leading-5 text-flow-muted">{display.purpose}</p>
                </div>
                <span className={`rounded-md px-2 py-1 text-xs font-semibold ${agent?.healthy ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'}`}>
                  {agent?.healthy ? 'Ready' : 'Offline'}
                </span>
              </div>
            </article>
          )
        })}
      </section>

      <section className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ['in_flight', 'In flight', taskCounts.in_flight],
          ['review', 'Needs approval', taskCounts.review],
          ['ready', 'Ready for review', taskCounts.ready],
          ['failed', 'Needs attention', taskCounts.failed],
        ].map(([id, label, value]) => (
          <button
            type="button"
            key={String(id)}
            onClick={() => setFilter(id as TaskFilter)}
            className={`flow-button rounded-xl px-4 py-4 text-left ${
              filter === id ? 'bg-flow-ink text-white' : 'flow-surface text-flow-ink'
            }`}
          >
            <div className={`text-xs font-semibold ${filter === id ? 'text-white/60' : 'text-flow-muted'}`}>{label}</div>
            <div className="font-flow-mono mt-2 text-3xl font-semibold">{value}</div>
          </button>
        ))}
      </section>

      <section className="mt-8 grid gap-6 xl:grid-cols-[21rem_minmax(25rem,0.9fr)_minmax(27rem,1.1fr)]">
        <form id="new-task" onSubmit={submitTask} className="flow-surface self-start rounded-2xl p-5 xl:sticky xl:top-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-flow-accent-deep">New task</p>
              <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em] text-flow-ink">Write the brief</h2>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-flow-ink text-flow-accent">
              <Zap className="h-4 w-4" />
            </div>
          </div>

          <div className="mt-5 space-y-4">
            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-flow-muted">Task name</span>
              <input
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                className="flow-input h-11 px-3.5 text-sm"
                placeholder="What needs to move?"
                minLength={5}
                required
              />
            </label>

            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-flow-muted">Done looks like</span>
              <textarea
                value={form.goal}
                onChange={(event) => setForm({ ...form, goal: event.target.value })}
                className="flow-input min-h-[8.5rem] resize-y px-3.5 py-3 text-sm leading-6"
                placeholder="Describe the finished result, source material, constraints, and anything that must stay unchanged."
                minLength={10}
                required
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label>
                <span className="mb-1.5 block text-xs font-semibold text-flow-muted">Work type</span>
                <select
                  value={form.task_type}
                  onChange={(event) => setForm({ ...form, task_type: event.target.value })}
                  className="flow-input h-11 px-3 text-sm"
                >
                  {taskTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <label>
                <span className="mb-1.5 block text-xs font-semibold text-flow-muted">Route</span>
                <select
                  value={form.risk_tier}
                  onChange={(event) => setForm({ ...form, risk_tier: event.target.value })}
                  className="flow-input h-11 px-3 text-sm"
                >
                  {riskOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
            </div>

            <div className="rounded-lg bg-stone-100 px-3.5 py-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-flow-ink">
                <ArrowRight className="h-3.5 w-3.5 text-flow-accent-deep" />
                Routes to {agentDisplay[ownerForRisk(form.risk_tier) as keyof typeof agentDisplay].name}
              </div>
              <p className="mt-1 text-xs leading-5 text-flow-muted">
                {riskOptions.find(([value]) => value === form.risk_tier)?.[2]}
              </p>
            </div>

            <label className="block">
              <span className="mb-1.5 block text-xs font-semibold text-flow-muted">Required output</span>
              <textarea
                value={form.output_required}
                onChange={(event) => setForm({ ...form, output_required: event.target.value })}
                className="flow-input min-h-[5.75rem] resize-y px-3.5 py-3 text-sm leading-6"
                required
              />
            </label>

            {form.risk_tier === 'downtime_security_money' && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-3 text-xs leading-5 text-amber-900">
                Agent Zero will stop at the approval gate. Nothing runs until the review pack is valid and approved.
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="flow-button inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-flow-ink px-4 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4 text-flow-accent" />}
              {submitting ? 'Routing task' : 'Send to FLOW'}
            </button>
          </div>
        </form>

        <div className="flow-surface min-h-[44rem] overflow-hidden rounded-2xl">
          <div className="border-b border-flow-line px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-flow-accent-deep">Task queue</p>
                <h2 className="mt-1 text-xl font-semibold tracking-[-0.03em] text-flow-ink">
                  {filter === 'all' ? 'All work' : filter === 'in_flight' ? 'In flight' : filter === 'review' ? 'Needs approval' : filter === 'ready' ? 'Ready for review' : 'Needs attention'}
                </h2>
              </div>
              {filter !== 'all' && (
                <button type="button" onClick={() => setFilter('all')} className="text-xs font-semibold text-flow-accent-deep hover:underline">
                  Clear filter
                </button>
              )}
            </div>
          </div>

          <div className="flow-scrollbar max-h-[calc(100vh-9rem)] min-h-[38rem] overflow-y-auto">
            {filteredTasks.length ? filteredTasks.map((task) => (
              <button
                type="button"
                key={task.task_id}
                onClick={() => loadTask(task.task_id).catch((error) => setNotice({ tone: 'error', text: error.message }))}
                className={`group block w-full border-b border-flow-line px-5 py-4 text-left transition-colors duration-200 ${
                  selectedId === task.task_id ? 'bg-stone-100' : 'hover:bg-white'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-flow-ink">{task.title}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-flow-muted">
                      <span>{agentDisplay[task.owner_role as keyof typeof agentDisplay]?.name || task.owner_role}</span>
                      <span aria-hidden="true">·</span>
                      <span>{formatDate(task.created_at)}</span>
                    </div>
                  </div>
                  <ChevronRight className={`mt-1 h-4 w-4 shrink-0 transition-transform ${selectedId === task.task_id ? 'translate-x-1 text-flow-accent-deep' : 'text-stone-400 group-hover:translate-x-1'}`} />
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <span className={`rounded-md px-2 py-1 text-[0.68rem] font-semibold ${statusTone(task.status)}`}>
                    {statusCopy[task.status] || task.status}
                  </span>
                  <span className="font-flow-mono text-[0.66rem] text-stone-400">{shortId(task.task_id)}</span>
                </div>
              </button>
            )) : (
              <div className="flex min-h-[38rem] flex-col items-center justify-center px-8 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-stone-100 text-stone-500">
                  <FileText className="h-5 w-5" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-flow-ink">No tasks in this view</h3>
                <p className="mt-2 max-w-xs text-sm leading-6 text-flow-muted">Submit a new brief or clear the current filter.</p>
              </div>
            )}
          </div>
        </div>

        <aside className="flow-surface min-h-[44rem] overflow-hidden rounded-2xl">
          {selected ? (
            <div>
              <div className="border-b border-flow-line px-5 py-5 sm:px-6">
                <div className="flex items-start justify-between gap-5">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-md px-2 py-1 text-[0.68rem] font-semibold ${statusTone(selected.status)}`}>
                        {statusCopy[selected.status] || selected.status}
                      </span>
                      <span className="font-flow-mono text-[0.66rem] text-stone-400">{shortId(selected.task_id)}</span>
                    </div>
                    <h2 className="mt-3 text-2xl font-semibold leading-tight tracking-[-0.035em] text-flow-ink">
                      {selected.title}
                    </h2>
                  </div>
                  <button
                    type="button"
                    onClick={reuseTask}
                    className="flow-button flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-flow-line bg-white text-flow-muted"
                    aria-label="Use this task as a new brief"
                    title="Use as a new brief"
                  >
                    <Copy className="h-4 w-4" />
                  </button>
                </div>

                <div className="mt-6 flex items-center">
                  {lifecycle.steps.map((step, index) => {
                    const done = index < lifecycle.current || selected.status === 'completed'
                    const current = index === lifecycle.current && selected.status !== 'completed'
                    const failed = lifecycle.failed && current
                    return (
                      <React.Fragment key={step.id}>
                        <div className="flex min-w-0 flex-col items-center gap-1.5">
                          <div className={`flex h-7 w-7 items-center justify-center rounded-full ${
                            failed ? 'bg-red-100 text-red-700' : done ? 'bg-flow-ink text-flow-accent' : current ? 'bg-flow-accent text-flow-ink' : 'bg-stone-100 text-stone-400'
                          }`}>
                            {failed ? <XCircle className="h-3.5 w-3.5" /> : done ? <Check className="h-3.5 w-3.5" /> : current ? <Clock3 className="h-3.5 w-3.5" /> : <Circle className="h-3 w-3" />}
                          </div>
                          <span className={`truncate text-[0.62rem] font-semibold ${current || done ? 'text-flow-ink' : 'text-stone-400'}`}>{step.label}</span>
                        </div>
                        {index < lifecycle.steps.length - 1 && (
                          <div className={`mx-1 mb-5 h-px flex-1 ${index < lifecycle.current ? 'bg-flow-ink' : 'bg-flow-line'}`} />
                        )}
                      </React.Fragment>
                    )
                  })}
                </div>
              </div>

              <div className="flow-scrollbar max-h-[calc(100vh-9rem)] space-y-6 overflow-y-auto px-5 py-5 sm:px-6">
                <section>
                  <h3 className="text-xs font-semibold text-flow-muted">Finished result</h3>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-flow-ink">{selected.goal}</p>
                </section>

                <dl className="grid grid-cols-2 gap-x-5 gap-y-4 border-y border-flow-line py-4 text-sm">
                  <div>
                    <dt className="text-xs text-flow-muted">Assigned agent</dt>
                    <dd className="mt-1 font-semibold text-flow-ink">{agentDisplay[selectedOwner as keyof typeof agentDisplay]?.name || selectedOwner}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-flow-muted">Work type</dt>
                    <dd className="mt-1 font-semibold text-flow-ink">{taskTypes.find(([value]) => value === selected.task_type)?.[1] || selected.task_type}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-flow-muted">Started</dt>
                    <dd className="mt-1 font-semibold text-flow-ink">{formatDate(selected.created_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-flow-muted">Last update</dt>
                    <dd className="mt-1 font-semibold text-flow-ink">{formatDate(selected.updated_at || selected.completed_at)}</dd>
                  </div>
                </dl>

                {selected.error_message && selected.status === 'failed' && (
                  <section className="rounded-xl border border-red-200 bg-red-50 p-4">
                    <div className="flex items-center gap-2 font-semibold text-red-900">
            <AlertTriangle className="h-4 w-4" />
                      This task needs attention
                    </div>
                    <p className="mt-2 break-words text-xs leading-5 text-red-800">{selected.error_message}</p>
                    <button
                      type="button"
                      onClick={reuseTask}
                      className="flow-button mt-3 inline-flex h-9 items-center gap-2 rounded-lg bg-red-900 px-3 text-xs font-semibold text-white"
                    >
                      Revise as a new task
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  </section>
                )}

                {selected.status === 'review_required' && (
                  <section className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-800">
                        <ShieldCheck className="h-4 w-4" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-amber-950">Approval gate</h3>
                        <p className="mt-1 text-xs leading-5 text-amber-900">
                          Review the proposed change, testing evidence, risk, and rollback plan. Agent Zero cannot run until all three records pass validation.
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 space-y-3">
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-semibold text-amber-950">Proposed diff</span>
                        <textarea
                          value={reviewPack.diff}
                          onChange={(event) => setReviewPack({ ...reviewPack, diff: event.target.value })}
                          className="flow-input font-flow-mono min-h-[7rem] resize-y px-3 py-2 text-xs leading-5"
                        />
                      </label>
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-semibold text-amber-950">Review record</span>
                        <textarea
                          value={reviewPack.review}
                          onChange={(event) => setReviewPack({ ...reviewPack, review: event.target.value })}
                          className="flow-input min-h-[12rem] resize-y px-3 py-2 text-xs leading-5"
                        />
                      </label>
                      <label className="block">
                        <span className="mb-1.5 block text-xs font-semibold text-amber-950">Rollback plan</span>
                        <textarea
                          value={reviewPack.rollback}
                          onChange={(event) => setReviewPack({ ...reviewPack, rollback: event.target.value })}
                          className="flow-input min-h-[9rem] resize-y px-3 py-2 text-xs leading-5"
                        />
                      </label>
                    </div>

                    {reviewStatus?.all_valid ? (
                      <div className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900">
                        Review pack valid{reviewStatus.review_approver?.name ? ` · ${reviewStatus.review_approver.name}` : ''}
                      </div>
                    ) : reviewStatus && (
                      <div className="mt-4 grid grid-cols-3 gap-2 text-[0.68rem] font-semibold">
                        <span className={reviewStatus.diff_valid ? 'text-emerald-800' : 'text-amber-900'}>Diff {reviewStatus.diff_valid ? 'valid' : 'needed'}</span>
                        <span className={reviewStatus.review_valid ? 'text-emerald-800' : 'text-amber-900'}>Review {reviewStatus.review_valid ? 'valid' : 'needed'}</span>
                        <span className={reviewStatus.rollback_valid ? 'text-emerald-800' : 'text-amber-900'}>Rollback {reviewStatus.rollback_valid ? 'valid' : 'needed'}</span>
                      </div>
                    )}

                    <div className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={submitReviewPack}
                        disabled={reviewSubmitting}
                        className="flow-button inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-amber-300 bg-white px-3 text-xs font-semibold text-amber-950 disabled:opacity-50"
                      >
                        {reviewSubmitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
                        Validate review pack
                      </button>
                      <button
                        type="button"
                        onClick={approveAndRun}
                        disabled={!reviewStatus?.can_execute || approvalRunning}
                        className="flow-button inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-amber-900 px-3 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {approvalRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                        Approve and run
                      </button>
                    </div>
                  </section>
                )}

                {selected.status === 'active' && (
                  <section className="rounded-xl bg-sky-50 p-4">
                    <div className="flex items-center gap-3">
                      <Loader2 className="h-5 w-5 animate-spin text-sky-700" />
                      <div>
                        <h3 className="text-sm font-semibold text-sky-950">The assigned agent is working</h3>
                        <p className="mt-1 text-xs text-sky-800">This view refreshes automatically. The finished artifact will appear here.</p>
                      </div>
                    </div>
                  </section>
                )}

                {selected.artifact_path && (
                  <section>
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold text-flow-ink">Finished artifact</h3>
                        <p className="mt-1 text-xs text-flow-muted">Staged here for review. Nothing is published automatically.</p>
                      </div>
                      <button
                        type="button"
                        onClick={loadArtifact}
                        disabled={artifactLoading}
                        className="flow-button inline-flex h-9 items-center gap-2 rounded-lg bg-flow-ink px-3 text-xs font-semibold text-white disabled:opacity-50"
                      >
                        {artifactLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5 text-flow-accent" />}
                        {artifactContent ? 'Refresh output' : 'Open output'}
                      </button>
                    </div>
                    {artifactContent && (
                      <pre className="flow-scrollbar font-flow-mono mt-4 max-h-[34rem] overflow-auto whitespace-pre-wrap rounded-xl bg-[#17201d] p-4 text-xs leading-6 text-[#e6eee9]">
                        {artifactContent}
                      </pre>
                    )}
                  </section>
                )}
              </div>
            </div>
          ) : (
            <div className="flex min-h-[44rem] flex-col items-center justify-center px-8 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-stone-100 text-stone-500">
                <ChevronRight className="h-6 w-6" />
              </div>
              <h2 className="mt-5 text-xl font-semibold tracking-[-0.03em] text-flow-ink">Choose a task</h2>
              <p className="mt-2 max-w-sm text-sm leading-6 text-flow-muted">
                The brief, route, live status, approval gate, and finished artifact will appear here.
              </p>
            </div>
          )}
        </aside>
      </section>
    </div>
  )
}
