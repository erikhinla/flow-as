import { apiFetch } from '../lib/api'
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Brain, TrendingUp, Target, Zap } from 'lucide-react'

interface Skill {
  skill_id: string
  pattern: string
  confidence: number
  times_used: number
  times_succeeded: number
  success_rate: number
  context_type?: string
  last_updated?: string
}

interface SkillEffectiveness {
  total_active_skills: number
  high_confidence_skills: number
  frequently_used_skills: number
  top_skills: Skill[]
  skill_distribution: {
    high_confidence: number
    medium_confidence: number
    low_confidence: number
  }
}

interface SkillsPanelProps {
  expanded?: boolean
}

export function SkillsPanel({ expanded = false }: SkillsPanelProps) {
  const { data: skills, isLoading } = useQuery<SkillEffectiveness>({
    queryKey: ['skill-effectiveness'],
    queryFn: async () => {
      const response = await apiFetch('/api/performance/skills/effectiveness')
      if (!response.ok) throw new Error('Failed to fetch skills data')
      return response.json()
    },
    refetchInterval: 60000, // Update every minute
  })

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.7) return 'text-green-600 bg-green-50'
    if (confidence >= 0.4) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.7) return '🟢'
    if (confidence >= 0.4) return '🟡'
    return '🔴'
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
          <h2 className="text-lg font-semibold text-gray-900">Learning System</h2>
          <Brain className="w-5 h-5 text-purple-500" />
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <Target className="w-4 h-4 text-blue-500" />
              <span className="text-xs text-gray-500">Active</span>
            </div>
            <div className="text-xl font-bold text-gray-900">
              {skills?.total_active_skills || 0}
            </div>
            <div className="text-xs text-gray-500">Total Skills</div>
          </div>
          
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-4 h-4 text-green-500" />
              <span className="text-xs text-gray-500">High Conf</span>
            </div>
            <div className="text-xl font-bold text-gray-900">
              {skills?.high_confidence_skills || 0}
            </div>
            <div className="text-xs text-gray-500">Reliable</div>
          </div>
        </div>

        {/* Skill Distribution */}
        {skills?.skill_distribution && (
          <div className="mb-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Confidence Distribution</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span>🟢</span>
                  <span className="text-sm text-gray-600">High (70%+)</span>
                </div>
                <span className="text-sm font-medium">{skills.skill_distribution.high_confidence}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span>🟡</span>
                  <span className="text-sm text-gray-600">Medium (40-70%)</span>
                </div>
                <span className="text-sm font-medium">{skills.skill_distribution.medium_confidence}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span>🔴</span>
                  <span className="text-sm text-gray-600">Low (&lt;40%)</span>
                </div>
                <span className="text-sm font-medium">{skills.skill_distribution.low_confidence}</span>
              </div>
            </div>
          </div>
        )}

        {/* Top Skills */}
        {skills?.top_skills && skills.top_skills.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">
              Top Performing Skills {!expanded && '(Top 3)'}
            </h3>
            <div className="space-y-3">
              {skills.top_skills.slice(0, expanded ? undefined : 3).map((skill) => (
                <div 
                  key={skill.skill_id}
                  className="border border-gray-200 rounded-lg p-3"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span>{getConfidenceIcon(skill.confidence)}</span>
                      <span className="text-sm font-medium text-gray-900">
                        Pattern #{skill.skill_id.slice(0, 8)}
                      </span>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(skill.confidence)}`}>
                      {Number((skill.confidence || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 mb-2">
                    {skill.pattern}
                  </p>
                  
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>{skill.times_used} uses</span>
                    <span>{Number(skill.success_rate || 0).toFixed(0)}% success</span>
                    {skill.context_type && (
                      <span className="bg-gray-100 px-2 py-1 rounded">
                        {skill.context_type}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {(!skills?.top_skills || skills.top_skills.length === 0) && (
          <div className="text-center py-8 text-gray-500">
            <Brain className="w-8 h-8 text-gray-300 mx-auto mb-2" />
            <p>No skills learned yet</p>
            <p className="text-xs">Skills will appear as the system learns from completed jobs</p>
          </div>
        )}
      </div>
    </div>
  )
}