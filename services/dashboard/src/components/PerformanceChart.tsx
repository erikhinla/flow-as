import { apiFetch } from '../lib/api'
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { TrendingUp, Clock, CheckCircle } from 'lucide-react'

interface PerformanceData {
  success_rate: number
  avg_execution_time: number
  total_jobs: number
  performance_metrics: Array<{
    owner: string
    task_type: string
    status: string
    count: number
    avg_execution_time: number
  }>
  recommendations: string[]
}

interface PerformanceChartProps {
  expanded?: boolean
}

export function PerformanceChart({ expanded = false }: PerformanceChartProps) {
  const { data: performance, isLoading } = useQuery<PerformanceData>({
    queryKey: ['performance-analysis'],
    queryFn: async () => {
      const response = await apiFetch('/api/performance/analysis?hours=24')
      if (!response.ok) throw new Error('Failed to fetch performance data')
      return response.json()
    },
    refetchInterval: 30000, // Update every 30 seconds
  })

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </div>
    )
  }

  // Transform data for charts
  const ownerData = performance?.performance_metrics?.reduce((acc, metric) => {
    const existing = acc.find(item => item.owner === metric.owner)
    if (existing) {
      existing.total += metric.count
      if (metric.status === 'completed') {
        existing.completed += metric.count
        existing.totalTime += metric.avg_execution_time * metric.count
      }
    } else {
      acc.push({
        owner: metric.owner,
        total: metric.count,
        completed: metric.status === 'completed' ? metric.count : 0,
        totalTime: metric.status === 'completed' ? metric.avg_execution_time * metric.count : 0
      })
    }
    return acc
  }, [] as Array<{owner: string, total: number, completed: number, totalTime: number}>)

  const chartData = ownerData?.map(item => ({
    name: item.owner.charAt(0).toUpperCase() + item.owner.slice(1),
    'Success Rate': item.total > 0 ? Math.round((item.completed / item.total) * 100) : 0,
    'Avg Time (s)': item.completed > 0 ? Math.round(item.totalTime / item.completed) : 0,
    Jobs: item.total
  })) || []

  const statusData = [
    { name: 'Completed', value: (performance?.performance_metrics || []).filter(m => m.status === 'completed').reduce((sum, m) => sum + m.count, 0) || 0, color: '#10B981' },
    { name: 'Failed', value: (performance?.performance_metrics || []).filter(m => m.status === 'failed').reduce((sum, m) => sum + m.count, 0) || 0, color: '#EF4444' },
    { name: 'Other', value: (performance?.performance_metrics || []).filter(m => !['completed', 'failed'].includes(m.status)).reduce((sum, m) => sum + m.count, 0) || 0, color: '#6B7280' }
  ].filter(item => item.value > 0)

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">Performance (24h)</h2>
        
        {/* Key Metrics */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="text-center">
            <div className="flex items-center justify-center w-8 h-8 bg-green-100 rounded-full mb-2 mx-auto">
              <CheckCircle className="w-4 h-4 text-green-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {Number(performance?.success_rate || 0).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500">Success Rate</div>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-full mb-2 mx-auto">
              <Clock className="w-4 h-4 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {Number(performance?.avg_execution_time || 0).toFixed(1)}s
            </div>
            <div className="text-xs text-gray-500">Avg Time</div>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center w-8 h-8 bg-purple-100 rounded-full mb-2 mx-auto">
              <TrendingUp className="w-4 h-4 text-purple-600" />
            </div>
            <div className="text-2xl font-bold text-gray-900">
              {performance?.total_jobs || 0}
            </div>
            <div className="text-xs text-gray-500">Total Jobs</div>
          </div>
        </div>

        {expanded && (
          <>
            {/* Performance by Agent */}
            {chartData.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Performance by Agent</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="Success Rate" fill="#10B981" />
                    <Bar dataKey="Avg Time (s)" fill="#3B82F6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Status Distribution */}
            {statusData.length > 0 && (
              <div className="mb-6">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Job Status Distribution</h3>
                <div className="flex items-center">
                  <ResponsiveContainer width="40%" height={150}>
                    <PieChart>
                      <Pie
                        data={statusData}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={70}
                        dataKey="value"
                      >
                        {statusData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex-1 ml-4">
                    {statusData.map((item, index) => (
                      <div key={index} className="flex items-center justify-between py-1">
                        <div className="flex items-center space-x-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: item.color }}
                          ></div>
                          <span className="text-sm text-gray-600">{item.name}</span>
                        </div>
                        <span className="text-sm font-medium text-gray-900">{item.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* Recommendations */}
        {performance?.recommendations && performance.recommendations.length > 0 && (
          <div className="border-t pt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Recommendations</h3>
            <div className="space-y-1">
              {performance.recommendations.slice(0, expanded ? undefined : 2).map((rec, index) => (
                <div key={index} className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded">
                  {rec}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}