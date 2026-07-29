import { Activity, Lock } from 'lucide-react'
import { FlowControl } from './components/FlowControl'

function App() {
  return (
    <div className="min-h-screen bg-flow-canvas text-flow-ink">
      <a
        href="#task-workspace"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-flow-ink focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to task workspace
      </a>

      <header className="border-b border-flow-line/80 bg-flow-canvas/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between px-5 py-4 sm:px-8 lg:px-10">
          <div className="flex items-center gap-3">
            <div className="flow-mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <div>
              <div className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-flow-muted">
                TransformBy10X
              </div>
              <div className="text-lg font-semibold tracking-[-0.025em] text-flow-ink">
                FLOW Agent AS
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm text-flow-muted">
            <div className="hidden items-center gap-2 sm:flex">
              <Lock className="h-4 w-4" />
              <span>Private operator workspace</span>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-flow-ink px-3 py-1.5 text-xs font-semibold text-white">
              <Activity className="h-3.5 w-3.5 text-flow-accent" />
              Live
            </div>
          </div>
        </div>
      </header>

      <main id="task-workspace">
        <FlowControl />
      </main>
    </div>
  )
}

export default App
