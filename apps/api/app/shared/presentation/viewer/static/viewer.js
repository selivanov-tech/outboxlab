const REFRESH_INTERVAL_MS = 5000;
const CREDENTIALS_STORAGE_KEY = "outboxlab.viewer.credentials";

const viewer = { headers: null, campaignId: null, timer: null };

const find = (selector) => document.querySelector(selector);

function readStoredCredentials() {
  try {
    return JSON.parse(sessionStorage.getItem(CREDENTIALS_STORAGE_KEY) || "null");
  } catch {
    return null;
  }
}

function storeCredentials(credentials) {
  try {
    sessionStorage.setItem(CREDENTIALS_STORAGE_KEY, JSON.stringify(credentials));
  } catch {
    return;
  }
}

function headersFor(credentials) {
  if (credentials.apiKey) return { Authorization: `Bearer ${credentials.apiKey}` };
  if (credentials.workspaceId) return { "X-Workspace-Id": credentials.workspaceId };
  return null;
}

async function getJson(path) {
  const response = await fetch(path, { headers: viewer.headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(`${path} → ${response.status} ${body.detail ?? ""}`.trim());
  }
  return response.json();
}

function cell(value) {
  const td = document.createElement("td");
  td.textContent = value ?? "—";
  return td;
}

function badgeCell(value) {
  const td = document.createElement("td");
  const badge = document.createElement("span");
  badge.className = `badge state-${value}`;
  badge.textContent = value ?? "—";
  td.append(badge);
  return td;
}

function row(cells) {
  const tr = document.createElement("tr");
  tr.append(...cells);
  return tr;
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString() : null;
}

function formatDelay(seconds) {
  if (seconds === 0) return "immediately";
  if (seconds < 3600) return `after ${Math.round(seconds / 60)} min`;
  return `after ${Math.round(seconds / 3600)} h`;
}

function formatCounts(counts) {
  const entries = Object.entries(counts ?? {});
  return entries.length ? entries.map(([key, count]) => `${key} ${count}`).join(" · ") : "none";
}

function renderCampaigns(campaigns) {
  find("#campaigns tbody").replaceChildren(
    ...campaigns.map((campaign) => {
      const tr = row([
        cell(campaign.name),
        badgeCell(campaign.status),
        cell(formatCounts(campaign.lead_counts)),
        cell(formatTime(campaign.created_at)),
      ]);
      tr.classList.add("clickable");
      tr.classList.toggle("selected", campaign.id === viewer.campaignId);
      tr.addEventListener("click", () => {
        viewer.campaignId = campaign.id;
        refresh();
      });
      return tr;
    }),
  );
}

function renderWorkspace(state) {
  const facts = [
    ["Mailbox sync cursor", state.mailbox_last_sync_cursor ?? "not set yet"],
    ["Outbound / inbound", `${state.outbound_count} / ${state.inbound_count}`],
    ["Leads", formatCounts(state.leads)],
    ["Send jobs", formatCounts(state.send_jobs)],
    ["Reply intents", formatCounts(state.intents)],
  ];
  find("#counts").replaceChildren(
    ...facts.flatMap(([label, value]) => {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      return [dt, dd];
    }),
  );
  find("#events tbody").replaceChildren(
    ...state.recent_events.map((event) =>
      row([cell(event.event_type), cell(event.aggregate_id.slice(0, 8)), cell(formatTime(event.created_at))]),
    ),
  );
}

function renderDetail(detail) {
  find("#detail").hidden = false;
  find("#detail-title").textContent = `${detail.name} (${detail.status})`;
  find("#steps tbody").replaceChildren(
    ...detail.steps.map((step) => row([cell(step.position), cell(step.subject), cell(formatDelay(step.delay_seconds))])),
  );
  find("#leads tbody").replaceChildren(
    ...detail.leads.map((lead) =>
      row([
        cell(lead.email),
        badgeCell(lead.state),
        cell(lead.steps_sent),
        cell(lead.stop_reason),
        cell(lead.reply_intent),
        cell(formatTime(lead.next_send_at)),
        cell(formatTime(lead.updated_at)),
      ]),
    ),
  );
}

async function refresh() {
  try {
    const [campaigns, state] = await Promise.all([getJson("/campaigns"), getJson("/debug/state")]);
    if (!campaigns.some((campaign) => campaign.id === viewer.campaignId)) {
      viewer.campaignId = campaigns.length ? campaigns[0].id : null;
    }
    renderCampaigns(campaigns);
    renderWorkspace(state);
    if (viewer.campaignId) {
      renderDetail(await getJson(`/campaigns/${viewer.campaignId}`));
    } else {
      find("#detail").hidden = true;
    }
    find("#main").hidden = false;
    find("#status").textContent = `updated ${new Date().toLocaleTimeString()}`;
  } catch (error) {
    find("#status").textContent = error.message;
  }
}

function connect(credentials) {
  viewer.headers = headersFor(credentials);
  if (!viewer.headers) {
    find("#status").textContent = "Enter an API key or a workspace id.";
    return;
  }
  storeCredentials(credentials);
  clearInterval(viewer.timer);
  refresh();
  viewer.timer = setInterval(refresh, REFRESH_INTERVAL_MS);
}

find("#credentials").addEventListener("submit", (event) => {
  event.preventDefault();
  connect({ apiKey: find("#api-key").value.trim(), workspaceId: find("#workspace-id").value.trim() });
});

const initialCredentials = readStoredCredentials() ?? {
  apiKey: "",
  workspaceId: new URLSearchParams(location.search).get("workspace") ?? "",
};
find("#workspace-id").value = initialCredentials.workspaceId ?? "";
if (initialCredentials.apiKey || initialCredentials.workspaceId) connect(initialCredentials);
