# Simple Agent 02 (`network-agent` + `check-gcp-subnet-ips`) — Distributed Multi-Agent A2A Architecture

A distributed **two-agent deployment** built with the **Google Agent Development Kit (ADK)** and **Agent-to-Agent (A2A)** protocol, deployed in **`asia-southeast2` (Jakarta)** on both **Cloud Run** and **Vertex AI Agent Engine (Agent Platform)** to study **Agent Gateway** and **Agent Registry**.

---

## 1. What Changed from `simple-agent-01` to `simple-agent-02`?

In [`simple-agent-01`](https://github.com/indrapn00/simple-agent-01), there was only **1 deployed Agent** (`root_agent`) with **2 local Python functions**.

In **`simple-agent-02`**, we split the deployment into **2 separate, independently deployed Agents** in `asia-southeast2`:

| Component | In `simple-agent-01` | In `simple-agent-02` | How It Is Deployed Now |
| :--- | :--- | :--- | :--- |
| **Main Agent** | `network_gateway_assistant` | **`network-agent`** (`network_agent`) | Deployed as its own standalone service on **Cloud Run** and **Agent Platform** |
| **Fork 1: `check_gcp_subnet_ips`** | 🔧 Plain Python Function | 🤖 **Standalone Remote Agent (`check-gcp-subnet-ips`)** | Deployed as its own separate service on **Cloud Run** and **Agent Platform**. `network-agent` calls it over the network via **A2A (`RemoteA2aAgent`)**! |
| **Fork 2: `recommend_agent_gateway_mode`** | 🔧 Plain Python Function | 🔧 **Local Python Function** | Kept inside `network-agent` as a local function tool (`tools=[recommend_agent_gateway_mode]`) |

---

## 2. Visual Architecture (2 Separate Deployed Agents)

```text
                        [ User Prompt ]
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DEPLOYED AGENT 1: `network-agent` (Main Orchestrator Agent)         │
│  Cloud Run: https://network-agent-66063681189.asia-southeast2.run.app│
│  Agent Engine ID: 1269979910546391040                                │
│                                                                      │
│                   🤖 network_agent (gemini-2.5-flash)                │
│                      /                           \                   │
│       Fork 1: Remote A2A Sub-Agent         Fork 2: Local Function    │
│       (transfer_to_agent over HTTP)               (in-process)       │
│                    /                               \                 │
│                   ▼                                 ▼                │
│     🌐 RemoteA2aAgent client          🔧 recommend_agent_gateway_mode│
└───────────────────┼──────────────────────────────────────────────────┘
                    │
                    │  A2A Protocol (JSON-RPC over HTTPS)
                    │  POST /a2a/check_gcp_subnet_ips
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  DEPLOYED AGENT 2: `check-gcp-subnet-ips` (Specialist Agent)         │
│  Cloud Run: https://check-gcp-subnet-ips-66063681189...run.app       │
│  Agent Engine ID: 6764371455938396160                                │
│                                                                      │
│               🤖 check_gcp_subnet_ips (gemini-2.5-flash)             │
│                                  │                                   │
│                                  ▼                                   │
│                      🔧 calculate_subnet_ips                         │
└──────────────────────────────────────────────────────────────────────┘
```

### Networking Analogy: Why This Matters for Agent Gateway
- **Fork 2 (`recommend_agent_gateway_mode`)** is an **internal function call** inside `network-agent`'s own process (like a router checking its local routing table).
- **Fork 1 (`check-gcp-subnet-ips`)** is a **real network hop between two separately deployed agents** using the **A2A (Agent-to-Agent) protocol** (`/.well-known/agent-card.json` + JSON-RPC over HTTPS). This is the exact east-west **Agent-to-Agent (A2A)** traffic flow that **Agent Gateway** governs and secures!

---

## 3. Live Deployments in `asia-southeast2` (`gcp-demo-02-307713`)

### A. Cloud Run Services (`asia-southeast2`)
1. **`network-agent` (Main Agent)**
   - **Web UI / Playground:** `https://network-agent-66063681189.asia-southeast2.run.app`
   - **A2A Agent Card URL:** `https://network-agent-66063681189.asia-southeast2.run.app/a2a/network_agent/.well-known/agent-card.json`
   - **Agent Registry Service:** `projects/gcp-demo-02-307713/locations/asia-southeast2/services/network-agent-cloudrun`
2. **`check-gcp-subnet-ips` (Standalone Subnet Calculator Agent)**
   - **Web UI / Playground:** `https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app`
   - **A2A Agent Card URL:** `https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app/a2a/check_gcp_subnet_ips/.well-known/agent-card.json`
   - **A2A JSON-RPC Endpoint:** `https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app/a2a/check_gcp_subnet_ips`
   - **Agent Registry Service:** `projects/gcp-demo-02-307713/locations/asia-southeast2/services/check-gcp-subnet-ips-cloudrun`

### B. Vertex AI Agent Engine / Agent Platform (`asia-southeast2`)
1. **`network-agent` (Main Agent)**
   - **Resource Name:** `projects/66063681189/locations/asia-southeast2/reasoningEngines/1269979910546391040`
   - **Console Playground:** [Open `network-agent` in Agent Engine Playground](https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/asia-southeast2/agent-engines/1269979910546391040/playground?project=66063681189)
2. **`check-gcp-subnet-ips` (Standalone Subnet Calculator Agent)**
   - **Resource Name:** `projects/66063681189/locations/asia-southeast2/reasoningEngines/6764371455938396160`
   - **Console Playground:** [Open `check-gcp-subnet-ips` in Agent Engine Playground](https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/asia-southeast2/agent-engines/6764371455938396160/playground?project=66063681189)

---

## 4. Repository Structure

```text
simple-agent-02/
├── README.md
├── check_gcp_subnet_ips/        # Deployed Agent 1: Standalone Subnet Calculator Agent
│   ├── __init__.py
│   ├── agent.py                 # Defines `check_gcp_subnet_ips` Agent + `calculate_subnet_ips` tool
│   ├── agent.json               # A2A v1 AgentCard exposed at /a2a/check_gcp_subnet_ips/.well-known/agent-card.json
│   └── requirements.txt
└── network_agent/               # Deployed Agent 2: Main Orchestrator Agent
    ├── __init__.py
    ├── agent.py                 # Defines `network_agent` + RemoteA2aAgent(`check_gcp_subnet_ips`) + `recommend_agent_gateway_mode`
    ├── agent.json               # A2A v1 AgentCard exposed at /a2a/network_agent/.well-known/agent-card.json
    └── requirements.txt
```

---

## 5. How to Test Both Forks on `network-agent`

Open the **`network-agent`** Web UI (`https://network-agent-66063681189.asia-southeast2.run.app`) or the Agent Engine Playground:

### Test Fork 1 — Remote A2A Agent Call (`network-agent` $\rightarrow$ `check-gcp-subnet-ips`)
Try asking:
- *"How many usable IPs are in 10.10.0.0/28 in GCP?"*
- *"Calculate the GCP reserved IPs and usable host count for 192.168.1.0/24."*

**What you will see in the UI:**
1. `network_agent` calls `transfer_to_agent(agent_name="check_gcp_subnet_ips")`.
2. Behind the scenes, `RemoteA2aAgent` sends an A2A JSON-RPC request over HTTPS to the separately deployed **`check-gcp-subnet-ips`** service (`https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app/a2a/check_gcp_subnet_ips`).
3. The remote `check-gcp-subnet-ips` agent runs `calculate_subnet_ips` and returns the response back to `network_agent`.

### Test Fork 2 — Local Function Call (`recommend_agent_gateway_mode`)
Try asking:
- *"Which Agent Gateway deployment mode should I use for agent to MCP tool egress traffic?"*
- *"Recommend an Agent Gateway mode if I already have an existing ALB or Secure Web Proxy."*

**What you will see in the UI:**
1. `network_agent` calls its local Python function `recommend_agent_gateway_mode` directly inside its own container.

---

## 6. Configuring the Remote Agent URL (If You Recreate `check-gcp-subnet-ips`)

In [`network_agent/agent.py`](./network_agent/agent.py), the URL for `check-gcp-subnet-ips` uses a placeholder by default so you never accidentally point to a stale hardcoded URL:

```python
CHECK_GCP_SUBNET_IPS_BASE_URL = os.environ.get(
    "CHECK_GCP_SUBNET_IPS_BASE_URL",
    "https://<REPLACE_WITH_CHECK_GCP_SUBNET_IPS_CLOUD_RUN_URL>",
)
```

If you delete and recreate the `check-gcp-subnet-ips` Cloud Run service and receive a new URL:
1. **Option A (Without touching code — Cloud Run only):** Update the environment variable on the `network-agent` Cloud Run service:
   ```bash
   gcloud run services update network-agent \
     --project=gcp-demo-02-307713 \
     --region=asia-southeast2 \
     --update-env-vars="CHECK_GCP_SUBNET_IPS_BASE_URL=https://<YOUR_NEW_CHECK_GCP_SUBNET_IPS_URL>"
   ```
2. **Option B (For both Cloud Run and Agent Platform / Vertex AI Agent Engine):** Replace `https://<REPLACE_WITH_CHECK_GCP_SUBNET_IPS_CLOUD_RUN_URL>` in [`network_agent/agent.py`](./network_agent/agent.py) (and `supported_interfaces[0].url` in [`check_gcp_subnet_ips/agent.json`](./check_gcp_subnet_ips/agent.json) if the URL of `check-gcp-subnet-ips` changed) before deploying.
   - **Important:** Because both Cloud Run and Agent Platform run [`network_agent/agent.py`](./network_agent/agent.py), `network-agent` on **Agent Platform** also uses this URL to call the remote `check-gcp-subnet-ips` A2A endpoint!

---

## 7. Deployment Commands Reference (`asia-southeast2`)

### Deploy Agent 1 (`check-gcp-subnet-ips`)
```bash
# Deploy to Cloud Run (with A2A + Web UI)
adk deploy cloud_run \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --service_name=check-gcp-subnet-ips \
  --app_name=check_gcp_subnet_ips \
  --with_ui \
  --a2a \
  ./check_gcp_subnet_ips \
  -- --allow-unauthenticated

# Deploy to Vertex AI Agent Engine
adk deploy agent_engine \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --display_name="check-gcp-subnet-ips" \
  ./check_gcp_subnet_ips
```

### Deploy Agent 2 (`network-agent`)
```bash
# Deploy to Cloud Run (with A2A + Web UI)
adk deploy cloud_run \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --service_name=network-agent \
  --app_name=network_agent \
  --with_ui \
  --a2a \
  ./network_agent \
  -- --allow-unauthenticated

# Configure the remote check-gcp-subnet-ips URL & Vertex AI env vars on Cloud Run
gcloud run services update network-agent \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --update-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=gcp-demo-02-307713,GOOGLE_CLOUD_LOCATION=global,CHECK_GCP_SUBNET_IPS_BASE_URL=https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app"

# Deploy to Vertex AI Agent Engine (make sure CHECK_GCP_SUBNET_IPS_BASE_URL in network_agent/agent.py is set first!)
adk deploy agent_engine \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --display_name="network-agent" \
  ./network_agent
```
