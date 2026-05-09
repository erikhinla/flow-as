const fs = require('fs');
const path = require('path');

const STATE = process.env.FLOW_STATE_DIR || '/state';
const WORKSPACE = process.env.FLOW_WORKSPACE_DIR || '/workspace';
const ARTIFACTS = process.env.FLOW_ARTIFACTS_DIR || '/artifacts';

const dirs = {
  pending: path.join(STATE, 'tasks/pending'),
  active: path.join(STATE, 'tasks/active'),
  completed: path.join(STATE, 'tasks/completed'),
  failed: path.join(STATE, 'tasks/failed'),
  escalated: path.join(STATE, 'tasks/escalated'),
  reports: path.join(STATE, 'reports'),
};

for (const dir of Object.values(dirs)) fs.mkdirSync(dir, { recursive: true });
fs.mkdirSync(WORKSPACE, { recursive: true });
fs.mkdirSync(ARTIFACTS, { recursive: true });

const required = ['task_id', 'source', 'instruction', 'risk_class', 'status', 'created_at'];
const allowedRisk = ['reputation', 'time_loss', 'downtime', 'security', 'money'];

function validate(task) {
  const missing = required.filter((key) => !task[key]);
  if (missing.length) throw new Error(`Missing required fields: ${missing.join(', ')}`);
  if (!allowedRisk.includes(task.risk_class)) throw new Error(`Invalid risk_class: ${task.risk_class}`);
}

function route(task) {
  if (['downtime', 'security', 'money'].includes(task.risk_class)) return 'gamma_agent_zero_required';
  if (task.workflow_type === 'publishing' || task.destination === 'postiz') return 'postiz_publishing';
  if (task.workflow_type === 'campaign_asset') return 'asset_workflow';
  return 'standard_execution';
}

function writeReport(task, routeName, resultPath) {
  const report = `# FLOW Asset Worker Report\n\nTask ID: ${task.task_id}\nStatus: ${task.status}\nRoute: ${routeName}\nSource: ${task.source}\nRisk: ${task.risk_class}\nCompleted At: ${task.completed_at || ''}\n\nInstruction:\n${task.instruction}\n\nResult:\n${JSON.stringify(task.result || {}, null, 2)}\n\nResult File:\n${resultPath}\n`;
  fs.writeFileSync(path.join(dirs.reports, `${task.task_id}.md`), report);
}

function processOne(file) {
  const pendingPath = path.join(dirs.pending, file);
  const task = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
  validate(task);

  const activePath = path.join(dirs.active, file);
  fs.renameSync(pendingPath, activePath);

  const routeName = route(task);

  if (routeName === 'gamma_agent_zero_required') {
    task.status = 'escalated';
    task.escalated_at = new Date().toISOString();
    task.route = routeName;
    task.reason = 'High-risk task requires Agent Zero approval/execution.';
    const escalatedPath = path.join(dirs.escalated, file);
    fs.writeFileSync(escalatedPath, JSON.stringify(task, null, 2));
    fs.rmSync(activePath, { force: true });
    writeReport(task, routeName, escalatedPath);
    return;
  }

  const outputDir = path.join(ARTIFACTS, task.task_id);
  fs.mkdirSync(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, 'result.json');

  task.status = 'completed';
  task.completed_at = new Date().toISOString();
  task.route = routeName;
  task.worker = 'flow-asset-worker';
  task.result = {
    accepted: true,
    workflow_type: task.workflow_type || 'standard',
    publishing_ready: routeName === 'postiz_publishing',
    artifact_dir: outputDir,
    message: 'Task envelope processed by FLOW asset worker.'
  };

  fs.writeFileSync(resultPath, JSON.stringify(task.result, null, 2));
  fs.writeFileSync(path.join(dirs.completed, file), JSON.stringify(task, null, 2));
  fs.rmSync(activePath, { force: true });
  writeReport(task, routeName, resultPath);
}

function tick() {
  const files = fs.readdirSync(dirs.pending).filter((f) => f.endsWith('.json'));
  for (const file of files) {
    try {
      processOne(file);
      console.log(`[FLOW] processed ${file}`);
    } catch (err) {
      console.error(`[FLOW] failed ${file}: ${err.message}`);
      const src = path.join(dirs.pending, file);
      const dst = path.join(dirs.failed, file);
      if (fs.existsSync(src)) fs.renameSync(src, dst);
    }
  }
}

console.log('[FLOW] asset worker started');
setInterval(tick, 5000);
tick();
