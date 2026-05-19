#!/usr/bin/env node

/**
 * Notion -> FLOW Agent AS bridge worker
 *
 * Purpose:
 * Poll a Notion Tasks database for records with Status=Submitted and empty FLOW Job ID,
 * submit each task to FLOW intake, then write the resulting FLOW Job ID and Status back
 * to the same Notion page.
 *
 * This intentionally removes Activepieces from the critical path. Activepieces can be
 * reintroduced later, but this worker gives the system a direct, observable submission loop.
 */

const REQUIRED_ENV = [
  'NOTION_TOKEN',
  'NOTION_TASKS_DATABASE_ID',
  'FLOW_INTAKE_URL',
  'FLOW_API_TOKEN'
];

const CONFIG = {
  notionVersion: process.env.NOTION_VERSION || '2022-06-28',
  notionToken: process.env.NOTION_TOKEN,
  notionDatabaseId: process.env.NOTION_TASKS_DATABASE_ID,
  flowIntakeUrl: process.env.FLOW_INTAKE_URL || 'http://127.0.0.1:18000/v1/intake/task',
  flowApiToken: process.env.FLOW_API_TOKEN,
  pollIntervalMs: Number(process.env.POLL_INTERVAL_MS || 30000),
  once: process.env.BRIDGE_ONCE === 'true',
  ownerDefault: process.env.DEFAULT_OWNER || 'agent_zero',
  logLevel: process.env.LOG_LEVEL || 'info'
};

function log(level, message, meta = {}) {
  const allowed = ['debug', 'info', 'warn', 'error'];
  if (allowed.indexOf(level) < allowed.indexOf(CONFIG.logLevel)) return;
  console.log(JSON.stringify({ ts: new Date().toISOString(), level, message, ...meta }));
}

function requireEnv() {
  const missing = REQUIRED_ENV.filter((key) => !process.env[key]);
  if (missing.length) {
    throw new Error(`Missing required env vars: ${missing.join(', ')}`);
  }
}

async function notion(path, options = {}) {
  const res = await fetch(`https://api.notion.com/v1${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${CONFIG.notionToken}`,
      'Notion-Version': CONFIG.notionVersion,
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  });

  const bodyText = await res.text();
  let body;
  try {
    body = bodyText ? JSON.parse(bodyText) : {};
  } catch {
    body = { raw: bodyText };
  }

  if (!res.ok) {
    throw new Error(`Notion API ${res.status}: ${JSON.stringify(body)}`);
  }
  return body;
}

function prop(properties, name) {
  return properties?.[name];
}

function plainText(value) {
  if (!value) return '';
  if (value.type === 'title') return value.title?.map((x) => x.plain_text).join('') || '';
  if (value.type === 'rich_text') return value.rich_text?.map((x) => x.plain_text).join('') || '';
  if (value.type === 'select') return value.select?.name || '';
  if (value.type === 'status') return value.status?.name || '';
  if (value.type === 'checkbox') return value.checkbox ? 'true' : 'false';
  if (value.type === 'url') return value.url || '';
  if (value.type === 'date') return value.date?.start || '';
  if (value.type === 'formula') {
    if (value.formula?.type === 'string') return value.formula.string || '';
    if (value.formula?.type === 'number') return String(value.formula.number ?? '');
    if (value.formula?.type === 'boolean') return value.formula.boolean ? 'true' : 'false';
  }
  if (value.type === 'unique_id') {
    const prefix = value.unique_id?.prefix ? `${value.unique_id.prefix}-` : '';
    return `${prefix}${value.unique_id?.number ?? ''}`;
  }
  return '';
}

function parseInputs(raw) {
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { request: raw };
  }
}

function getPageTaskId(page) {
  const existing = plainText(prop(page.properties, 'Task ID'));
  if (existing) return existing;
  return page.id;
}

function buildEnvelope(page) {
  const properties = page.properties;
  const taskName = plainText(prop(properties, 'Task Name')) || plainText(prop(properties, 'Name')) || 'Untitled FLOW Task';
  const taskId = getPageTaskId(page);
  const outputRequiredProp = prop(properties, 'Output Required');
  const outputRequired = outputRequiredProp?.type === 'checkbox' ? outputRequiredProp.checkbox : true;

  return {
    task_id: taskId,
    task_name: taskName,
    task_type: plainText(prop(properties, 'Task Type')) || 'implementation',
    risk_tier: plainText(prop(properties, 'Risk Tier')) || 'low',
    priority: plainText(prop(properties, 'Priority')) || 'high',
    preferred_owner: plainText(prop(properties, 'Preferred Owner')) || CONFIG.ownerDefault,
    output_required: outputRequired ? 'true' : 'false',
    goal: plainText(prop(properties, 'Goal')),
    inputs: parseInputs(plainText(prop(properties, 'Inputs'))),
    source: {
      system: 'notion',
      database: 'Tasks FAAS',
      notion_page_id: page.id,
      notion_url: page.url
    }
  };
}

async function findSubmittedTasks() {
  const body = {
    page_size: 10,
    filter: {
      and: [
        { property: 'Status', status: { equals: 'Submitted' } },
        { property: 'FLOW Job ID', rich_text: { is_empty: true } }
      ]
    }
  };

  const response = await notion(`/databases/${CONFIG.notionDatabaseId}/query`, {
    method: 'POST',
    body: JSON.stringify(body)
  });

  return response.results || [];
}

async function postToFlow(envelope) {
  const res = await fetch(CONFIG.flowIntakeUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Api-Token': CONFIG.flowApiToken
    },
    body: JSON.stringify(envelope)
  });

  const bodyText = await res.text();
  let body;
  try {
    body = bodyText ? JSON.parse(bodyText) : {};
  } catch {
    body = { raw: bodyText };
  }

  if (!res.ok) {
    const err = new Error(`FLOW intake ${res.status}: ${JSON.stringify(body)}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }

  return body;
}

function flowJobIdFromResponse(response, envelope) {
  return response.job_id || response.flow_job_id || response.id || response.task_id || envelope.task_id;
}

async function updateNotionSuccess(page, flowResponse, envelope) {
  const flowJobId = flowJobIdFromResponse(flowResponse, envelope);
  await notion(`/pages/${page.id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      properties: {
        'Status': { status: { name: 'Activated' } },
        'FLOW Job ID': { rich_text: [{ text: { content: String(flowJobId) } }] },
        'Submitted At': { date: { start: new Date().toISOString() } },
        'Last Error': { rich_text: [] }
      }
    })
  });
  return flowJobId;
}

async function updateNotionFailure(page, error) {
  const message = String(error.message || error).slice(0, 1900);
  await notion(`/pages/${page.id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      properties: {
        'Status': { status: { name: 'Failed' } },
        'Last Error': { rich_text: [{ text: { content: message } }] }
      }
    })
  });
}

async function processTask(page) {
  const envelope = buildEnvelope(page);
  log('info', 'submitting_task_to_flow', { task_id: envelope.task_id, task_name: envelope.task_name });

  try {
    const flowResponse = await postToFlow(envelope);
    const flowJobId = await updateNotionSuccess(page, flowResponse, envelope);
    log('info', 'task_submitted_to_flow', { task_id: envelope.task_id, flow_job_id: flowJobId });
  } catch (error) {
    log('error', 'task_submission_failed', { page_id: page.id, error: error.message });
    await updateNotionFailure(page, error);
  }
}

async function tick() {
  const tasks = await findSubmittedTasks();
  log('info', 'poll_complete', { submitted_tasks_found: tasks.length });
  for (const task of tasks) {
    await processTask(task);
  }
}

async function main() {
  requireEnv();
  log('info', 'notion_flow_bridge_started', {
    database_id: CONFIG.notionDatabaseId,
    flow_intake_url: CONFIG.flowIntakeUrl,
    poll_interval_ms: CONFIG.pollIntervalMs,
    once: CONFIG.once
  });

  if (CONFIG.once) {
    await tick();
    return;
  }

  await tick();
  setInterval(() => {
    tick().catch((error) => log('error', 'poll_tick_failed', { error: error.message }));
  }, CONFIG.pollIntervalMs);
}

main().catch((error) => {
  log('error', 'bridge_fatal_error', { error: error.message });
  process.exit(1);
});
