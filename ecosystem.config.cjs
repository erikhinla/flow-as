module.exports = {
  apps: [
    {
      name: 'openclaw-alpha',
      script: 'scripts/openclaw_runtime.py',
      interpreter: 'python3',
      args: '--role alpha --port 18789',
      cwd: __dirname,
      env: {
        FLOW_STATE_DIR: process.env.FLOW_STATE_DIR || `${process.env.HOME}/.openclaw/state`,
      },
    },
    {
      name: 'openclaw-beta',
      script: 'scripts/openclaw_runtime.py',
      interpreter: 'python3',
      args: '--role beta --port 18790',
      cwd: __dirname,
      env: {
        FLOW_STATE_DIR: process.env.FLOW_STATE_DIR || `${process.env.HOME}/.openclaw/state`,
      },
    },
  ],
}
