import { apiFetch } from '../lib/api'
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock, CheckCircle, XCircle, AlertCircle, ExternalLink } from 'lucide-react'

interface Job {
  task_id: string
  title?: string
  source?: string
  status?: string
  priority?: number
  owner_agent?: string | null
  thread_id?: string | null
  repo_path?: string | null
  metadata?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

interface JobsTableProps {
  limit?: number
}

export function JobsTable({ limit }: JobsTableProps) {
  const { data: jobs, isLoading } = useQuery<Job[]>({
    queryKey: ['recent-jobs', limit],
    queryFn: async () => {
      const url = `/api/tasks${limit ? `?limit=${limit}` : ''}`
      const response = await apiFetch(url)
      if (!response.ok) throw new Error('Failed to fetch jobs')
      const result = await response.json()
      return Array.isArray(result) ? result : (result.tasks || [])
    },
    refetchInterval: 15000, // Update every 15 seconds
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />
      case 'active':
        return <Clock className="w-4 h-4 text-blue-500 animate-pulse" />
      case 'review_required':
        return <AlertCircle className="w-4 h-4 text-amber-500" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    switch (status) {
      case 'completed':
        return `${baseClasses} bg-green-100 text-green-800`
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800`
      case 'active':
        return `${baseClasses} bg-blue-100 text-blue-800`
      case 'review_required':
        return `${baseClasses} bg-amber-100 text-amber-800`
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`
    }
  }

  const getOwnerColor = (owner: string) => {
    switch (owner) {
      case 'hermes':
        return 'text-green-600 bg-green-50'
      case 'openclaw':
        return 'text-yellow-600 bg-yellow-50'
      case 'agent_zero':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const formatDuration = (started: string, completed?: string) => {
    if (!completed) return '--'
    const start = new Date(started)
    const end = new Date(completed)
    const duration = (end.getTime() - start.getTime()) / 1000
    return `${duration.toFixed(1)}s`
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">
            Recent Jobs {limit && `(Last ${limit})`}
          </h2>
          {!limit && (
            <button className="text-sm text-blue-600 hover:text-blue-500">
              View All
            </button>
          )}
        </div>

        {!jobs || jobs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No recent jobs found
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Job
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Agent
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Duration
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {jobs.map((job, index) => {
                  if (!job) return null
                  const jobId = job.task_id || `missing-${index}`
                  const status = job.status || 'unknown'
                  const owner = job.owner_agent || 'unassigned'
                  const taskType = job.source || (job.metadata?.type as string) || 'unknown'

                  return (
                    <tr key={jobId} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {job.title || 'Untitled Task'}
                          </div>
                          <div className="text-sm text-gray-500">
                            {taskType}
                          </div>
                          <div className="text-xs text-gray-400 font-mono">
                            {job.task_id ? `${job.task_id.slice(0, 8)}...` : jobId}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getOwnerColor(owner)}`}>
                          {owner}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(status)}
                          <span className={getStatusBadge(status)}>
                            {status.replace('_', ' ')}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {/* Task records do not currently include duration fields */}
                        --
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {job.created_at ? new Date(job.created_at).toLocaleString() : '--'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {/* No result_pointer currently available on TaskRecord */}
                        --
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}