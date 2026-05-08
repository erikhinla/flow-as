import { apiFetch } from '../lib/api'
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, AlertCircle, CheckCircle } from 'lucide-react'

interface HealthStatus {
  status: string
  timestamp: string
  version?: string
}

export function SystemHealth() {
  const { data: health, isLoading } = useQuery<HealthStatus>({
    queryKey: ['health'],
    queryFn: async () => {
      const response = await apiFetch('/api/health')
      if (!response.ok) throw new Error('Health check failed')
      return response.json()
    },
    refetchInterval: 5000, // Check every 5 seconds
  })

  const { data: flowHealth } = useQuery({
    queryKey: ['flow-health'],
    queryFn: async () => {
      const response = await apiFetch('/api/flow/health')
      if (!response.ok) throw new Error('Flow health check failed')
      return response.json()
    },
    refetchInterval: 10000, // Check every 10 seconds
  })

  const isHealthy = health?.status === 'healthy'
  const flowHealthy = flowHealth?.status === 'healthy'

  if (isLoading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
        <span className="text-sm text-gray-500">Checking...</span>
      </div>
    )
  }

  return (
    <div className="flex items-center space-x-4">
      {/* API Health */}
      <div className="flex items-center space-x-2">
        {isHealthy ? (
          <CheckCircle className="w-4 h-4 text-green-500" />
        ) : (
          <AlertCircle className="w-4 h-4 text-red-500" />
        )}
        <span className="text-sm text-gray-600">API</span>
      </div>

      {/* FLOW Health */}
      <div className="flex items-center space-x-2">
        {flowHealthy ? (
          <Activity className="w-4 h-4 text-green-500" />
        ) : (
          <AlertCircle className="w-4 h-4 text-red-500" />
        )}
        <span className="text-sm text-gray-600">Workers</span>
      </div>

      {/* Overall Status */}
      <div className="flex items-center space-x-2">
        <div 
          className={`w-2 h-2 rounded-full ${
            isHealthy && flowHealthy ? 'bg-green-500' : 'bg-red-500'
          } animate-pulse`}
        ></div>
        <span className="text-sm font-medium text-gray-900">
          {isHealthy && flowHealthy ? 'Operational' : 'Degraded'}
        </span>
      </div>
    </div>
  )
}