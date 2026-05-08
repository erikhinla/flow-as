import React, { useState } from 'react'
import { Activity, BarChart3, Settings, ShieldCheck, Zap } from 'lucide-react'
import { QueueMonitor } from './components/QueueMonitor'
import { PerformanceChart } from './components/PerformanceChart'
import { JobsTable } from './components/JobsTable'
import { SystemHealth } from './components/SystemHealth'
import { SkillsPanel } from './components/SkillsPanel'
import { FlowControl } from './components/FlowControl'

type Tab = 'overview' | 'flow-control' | 'performance' | 'jobs' | 'skills' | 'settings'

function App() {
  const initialTab: Tab = window.location.pathname === '/flow-control' ? 'flow-control' : 'overview'
  const [activeTab, setActiveTab] = useState<Tab>(initialTab)

  const tabs = [
    { id: 'overview' as Tab, label: 'Overview', icon: Activity },
    { id: 'flow-control' as Tab, label: 'FLOW Control', icon: ShieldCheck },
    { id: 'performance' as Tab, label: 'Performance', icon: BarChart3 },
    { id: 'jobs' as Tab, label: 'Jobs', icon: Zap },
    { id: 'skills' as Tab, label: 'Skills', icon: Settings },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
                <h1 className="text-xl font-semibold text-gray-900">FLOW Agent AS</h1>
              </div>
              <div className="hidden md:block">
                <div className="ml-10 flex items-baseline space-x-4">
                  {tabs.map((tab) => {
                    const Icon = tab.icon
                    return (
                      <button
                        key={tab.id}
                        onClick={() => {
                          setActiveTab(tab.id)
                          window.history.replaceState(null, '', tab.id === 'flow-control' ? '/flow-control' : '/')
                        }}
                        className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 ${
                          activeTab === tab.id
                            ? 'bg-blue-100 text-blue-700'
                            : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                        }`}
                      >
                        <Icon className="w-4 h-4" />
                        <span>{tab.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
            <SystemHealth />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'overview' && (
          <div className="space-y-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <QueueMonitor />
              </div>
              <div>
                <PerformanceChart />
              </div>
            </div>
            <JobsTable limit={10} />
          </div>
        )}

        {activeTab === 'flow-control' && <FlowControl />}

        {activeTab === 'performance' && (
          <div className="space-y-8">
            <PerformanceChart expanded />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <QueueMonitor />
              <SkillsPanel />
            </div>
          </div>
        )}

        {activeTab === 'jobs' && <JobsTable />}

        {activeTab === 'skills' && <SkillsPanel expanded />}

        {activeTab === 'settings' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Settings</h2>
            <p className="text-gray-600">Configuration options coming soon...</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
