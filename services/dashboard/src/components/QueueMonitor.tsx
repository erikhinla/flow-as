import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Clock, Users, Zap } from 'lucide-react'

interface QueueStatus {
  timestamp: string
  queues: {
    openclaw: number
    hermes: number
    agent_zero: number
  }
  total: number
}

export function QueueMonitor() {
  const { data: queueStatus, isLoading } = useQuery<QueueStatus>({
    queryKey: ['queue-status'],
    queryFn: async () => {
      const response = await fetch('/api/intake/queues/status')
      if (!response.ok) throw new Error('Failed to fetch queue status')
      return response.json()
    },
    refetchInterval: 2000, // Update every 2 seconds
  })

  const queueData = [
    {
      name: 'OpenClaw',
      description: 'Classification & Routing',
      count: queueStatus?.queues.openclaw || 0,
      color: 'bg-yellow-500',
      icon: Clock,
    },
    {
      name: 'Hermes',
      description: 'Content Generation',
      count: queueStatus?.queues.hermes || 0,
      color: 'bg-green-500',
      icon: Zap,
    },
    {
      name: 'Agent Zero',
      description: 'High-Risk Implementation',
      count: queueStatus?.queues.agent_zero || 0,
      color: 'bg-red-500',
      icon: Users,
    },
  ]

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
          <h2 className="text-lg font-semibold text-gray-900">Queue Status</h2>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>Live</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {queueData.map((queue) => {
            const Icon = queue.icon
            return (
              <div
                key={queue.name}
                className="bg-gray-50 rounded-lg p-4 border border-gray-200"
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${queue.color}`}></div>
                    <span className="text-sm font-medium text-gray-900">
                      {queue.name}
                    </span>
                  </div>
                  <Icon className="w-4 h-4 text-gray-400" />
                </div>
                <div className="text-2xl font-bold text-gray-900 mb-1">
                  {queue.count}
                </div>
                <div className="text-xs text-gray-500">{queue.description}</div>
              </div>
            )
          })}
        </div>

        <div className="border-t pt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-500">Total Pending Jobs</span>
            <span className="font-semibold text-gray-900">
              {queueStatus?.total || 0}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-gray-400 mt-1">
            <span>Last updated</span>
            <span>
              {queueStatus?.timestamp
                ? new Date(queueStatus.timestamp).toLocaleTimeString()
                : '--:--:--'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}