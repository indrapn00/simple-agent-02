# Simple Agent 02 (`network-agent` + `check-gcp-subnet-ips`) — Distributed Multi-Agent Study Guide

A distributed **two-agent deployment** built with the **Google Agent Development Kit (ADK)**, deployed in **`asia-southeast2` (Jakarta)** to study **Agent Gateway**, **Agent Registry**, and multi-agent connectivity across **Cloud Run** and **Agent Platform (Vertex AI Agent Engine)**.

---

## 1. What Changed from `simple-agent-01` to `simple-agent-02`?

In [`simple-agent-01`](https://github.com/indrapn00/simple-agent-01), there was only **1 deployed Agent** (`root_agent`) with **2 local Python functions**.

In **`simple-agent-02`**, we split the deployment into **2 separate, independently deployed Agents** in `asia-southeast2`:

| Component | In `simple-agent-01` | In `simple-agent-02` | How It Is Deployed Now |
| :--- | :--- | :--- | :--- |
| **Main Agent** | `network_gateway_assistant` | **`network-agent`** (`network_agent`) | Deployed as its own standalone service on **Cloud Run** and/or **Agent Platform** |
| **Fork 1: `check_gcp_subnet_ips`** | 🔧 Plain Python Function | 🤖 **Standalone Remote Agent (`check-gcp-subnet-ips`)** | Deployed as its own separate service on **Cloud Run** and/or **Agent Platform**. `network-agent` calls it over the network! |
| **Fork 2: `recommend_agent_gateway_mode`** | 🔧 Plain Python Function | 🔧 **Local Python Function** | Kept inside `network-agent` as a local function tool (`tools=[recommend_agent_gateway_mode]`) |

---

## 2. Three Supported Multi-Agent Deployment & Connectivity Modes

[`network_agent/agent.py`](./network_agent/agent.py) is built so you can run the two agents in **3 different architectural topologies** controlled by a single variable (`SUBNET_AGENT_TARGET`):

| Mode | Where `network-agent` Runs | Where `check-gcp-subnet-ips` Runs | `SUBNET_AGENT_TARGET` Setting | How `network-agent` Calls `check-gcp-subnet-ips` | Cloud Run Dependency? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mode 1: Native Cloud Run Only** | **Cloud Run** | **Cloud Run** | `"cloud_run"` *(or `"auto"` on Cloud Run)* | **A2A Protocol over HTTPS** (`RemoteA2aAgent` $\rightarrow$ `https://check-gcp-subnet-ips-...run.app/a2a/check_gcp_subnet_ips`) | Uses Cloud Run only (Zero Agent Platform needed) |
| **Mode 2: Native Agent Platform Only** | **Agent Platform** *(Vertex AI Agent Engine)* | **Agent Platform** *(Vertex AI Agent Engine)* | `"agent_platform"` *(or `"auto"` on Agent Platform)* | **Vertex AI Regional API** (`RemoteAgentEngineSubAgent` $\rightarrow$ `reasoningEngines/<ID>:streamQuery` over IAM) | **Zero Cloud Run needed!** |
| **Mode 3: Hybrid (Cloud Run $\rightarrow$ Agent Platform)** | **Cloud Run** | **Agent Platform** *(Vertex AI Agent Engine)* | `"agent_platform"` *(set on Cloud Run)* | **Vertex AI Regional API** (Cloud Run container calls `reasoningEngines/<ID>:streamQuery` using its GCP Service Account IAM) | Only `network-agent` is on Cloud Run; `check-gcp-subnet-ips` is on Agent Platform only |

---

### Mode 1: Native Cloud Run Only (Cloud Run $\rightarrow$ Cloud Run)

Both agents run as independent **Cloud Run** services in `asia-southeast2`. You do **not** need Agent Platform at all in this mode.

```text
                        [ User Prompt ]
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CLOUD RUN SERVICE 1: `network-agent`                                │
│  URL: https://network-agent-66063681189.asia-southeast2.run.app      │
│                                                                      │
│                   🤖 network_agent (gemini-2.5-flash)                │
│                      /                           \                   │
│       Fork 1: Remote A2A Sub-Agent         Fork 2: Local Function    │
│                    /                               \                 │
│                   ▼                                 ▼                │
│     🌐 RemoteA2aAgent client          🔧 recommend_agent_gateway_mode│
└───────────────────┼──────────────────────────────────────────────────┘
                    │
                    │  A2A Protocol (JSON-RPC over HTTPS)
                    │  POST https://check-gcp-subnet-ips-...run.app/a2a/check_gcp_subnet_ips
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  CLOUD RUN SERVICE 2: `check-gcp-subnet-ips`                         │
│  URL: https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app│
│                                                                      │
│               🤖 check_gcp_subnet_ips (gemini-2.5-flash)             │
│                                  │                                   │
│                                  ▼                                   │
│                      🔧 calculate_subnet_ips                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Mode 2: Native Agent Platform Only (Agent Platform $\rightarrow$ Agent Platform)

Both agents run inside **Agent Platform (Vertex AI Agent Engine)** in `asia-southeast2`.
- **Zero Cloud Run dependency:** Even if you delete all Cloud Run services, `network-agent` on Agent Platform calls `check-gcp-subnet-ips` on Agent Platform directly using its **Reasoning Engine Resource ID** (`projects/66063681189/locations/asia-southeast2/reasoningEngines/<ID>`).

```text
                        [ User / Playground / API ]
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT ENGINE 1: `network-agent` (Agent Platform)                    │
│  ID: projects/66063681189/locations/asia-southeast2/                 │
│      reasoningEngines/5881665928973778944                            │
│                                                                      │
│                   🤖 network_agent (gemini-2.5-flash)                │
│                      /                           \                   │
│       Fork 1: RemoteAgentEngineSubAgent    Fork 2: Local Function    │
│                    /                               \                 │
│                   ▼                                 ▼                │
│     ☁️ vertexai.agent_engines.get()   🔧 recommend_agent_gateway_mode│
└───────────────────┼──────────────────────────────────────────────────┘
                    │
                    │  Vertex AI Regional API (IAM Authenticated)
                    │  asia-southeast2-aiplatform.googleapis.com
                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  AGENT ENGINE 2: `check-gcp-subnet-ips` (Agent Platform)             │
│  ID: projects/66063681189/locations/asia-southeast2/                 │
│      reasoningEngines/2395879817389015040                            │
│                                                                      │
│               🤖 check_gcp_subnet_ips (gemini-2.5-flash)             │
│                                  │                                   │
│                                  ▼                                   │
│                      🔧 calculate_subnet_ips                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Mode 3: Hybrid (`network-agent` on Cloud Run $\rightarrow$ `check-gcp-subnet-ips` on Agent Platform)

**Question:** *If `network-agent` is deployed on Cloud Run and `check-gcp-subnet-ips` is deployed ONLY on Agent Platform, can `network-agent` still access `check-gcp-subnet-ips`?*

**Answer:** **Yes!**
- Why it works: Your `network-agent` Cloud Run service runs as a Google Cloud Service Account (`66063681189-compute@developer.gserviceaccount.com`) that has IAM permission (`roles/aiplatform.user`) to invoke Vertex AI Agent Engines in your project.
- How to enable Mode 3 on Cloud Run without re-deploying code:
  Simply set `SUBNET_AGENT_TARGET=agent_platform` on the `network-agent` Cloud Run service:
  ```bash
  gcloud run services update network-agent \
    --project=gcp-demo-02-307713 \
    --region=asia-southeast2 \
    --update-env-vars="SUBNET_AGENT_TARGET=agent_platform,CHECK_GCP_SUBNET_IPS_AGENT_ENGINE_ID=projects/66063681189/locations/asia-southeast2/reasoningEngines/2395879817389015040"
  ```
- To switch `network-agent` on Cloud Run back to **Mode 1 (Cloud Run $\rightarrow$ Cloud Run)**:
  ```bash
  gcloud run services update network-agent \
    --project=gcp-demo-02-307713 \
    --region=asia-southeast2 \
    --update-env-vars="SUBNET_AGENT_TARGET=cloud_run"
  ```

---

## 3. Live Endpoints in `asia-southeast2` (`gcp-demo-02-307713`)

### A. Native Cloud Run Deployments (`asia-southeast2`)
1. **`network-agent` (Main Agent)**
   - **Web UI / Playground:** `https://network-agent-66063681189.asia-southeast2.run.app`
   - **A2A Agent Card URL:** `https://network-agent-66063681189.asia-southeast2.run.app/a2a/network_agent/.well-known/agent-card.json`
2. **`check-gcp-subnet-ips` (Standalone Subnet Calculator Agent)**
   - **Web UI / Playground:** `https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app`
   - **A2A Agent Card URL:** `https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app/a2a/check_gcp_subnet_ips/.well-known/agent-card.json`

### B. Native Agent Platform Deployments (`asia-southeast2`)
1. **`network-agent` (Main Agent)**
   - **Resource Name:** `projects/66063681189/locations/asia-southeast2/reasoningEngines/5881665928973778944`
   - **Console Playground:** [Open `network-agent` in Agent Engine Playground](https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/asia-southeast2/agent-engines/5881665928973778944/playground?project=66063681189)
2. **`check-gcp-subnet-ips` (Standalone Subnet Calculator Agent)**
   - **Resource Name:** `projects/66063681189/locations/asia-southeast2/reasoningEngines/2395879817389015040`
   - **Console Playground:** [Open `check-gcp-subnet-ips` in Agent Engine Playground](https://console.cloud.google.com/vertex-ai/agents/agent-engines/locations/asia-southeast2/agent-engines/2395879817389015040/playground?project=66063681189)

---

## 4. Copy-Pasteable Placeholders (If You Delete and Re-Deploy From Scratch)

To prevent confusion if you ever delete and re-create the agents and get new URLs or Agent Engine IDs, the files in this repository use explicit `<REPLACE_WITH_...>` placeholders:

| File | Placeholder to Replace | What to Paste | Needed For |
| :--- | :--- | :--- | :--- |
| [`check_gcp_subnet_ips/agent.json`](./check_gcp_subnet_ips/agent.json) | `https://<REPLACE_WITH_CHECK_GCP_SUBNET_IPS_CLOUD_RUN_URL>` | Your `check-gcp-subnet-ips` Cloud Run URL (e.g. `https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app`) | **Mode 1** (Cloud Run A2A) |
| [`network_agent/agent.json`](./network_agent/agent.json) | `https://<REPLACE_WITH_NETWORK_AGENT_CLOUD_RUN_URL>` | Your `network-agent` Cloud Run URL (e.g. `https://network-agent-66063681189.asia-southeast2.run.app`) | **Mode 1** (Cloud Run A2A) |
| [`network_agent/agent.py`](./network_agent/agent.py) | `https://<REPLACE_WITH_CHECK_GCP_SUBNET_IPS_CLOUD_RUN_URL>` | Your `check-gcp-subnet-ips` Cloud Run URL *(or pass via `CHECK_GCP_SUBNET_IPS_BASE_URL` env var)* | **Mode 1** (Cloud Run $\rightarrow$ Cloud Run) |
| [`network_agent/agent.py`](./network_agent/agent.py) | `<REPLACE_WITH_CHECK_GCP_SUBNET_IPS_AGENT_ENGINE_ID>` | Your `check-gcp-subnet-ips` Agent Engine ID (e.g. `2395879817389015040`) | **Mode 2** (Agent Platform $\rightarrow$ Agent Platform) & **Mode 3** (Hybrid) |

---

## 5. Step-by-Step Re-Deployment Recipes (`asia-southeast2`)

### Recipe A: Deploy Native Cloud Run Only (Mode 1: Cloud Run $\rightarrow$ Cloud Run)
```bash
# 1. Replace <REPLACE_WITH_CHECK_GCP_SUBNET_IPS_CLOUD_RUN_URL> in check_gcp_subnet_ips/agent.json,
#    then deploy check-gcp-subnet-ips to Cloud Run:
adk deploy cloud_run \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --service_name=check-gcp-subnet-ips \
  --app_name=check_gcp_subnet_ips \
  --with_ui \
  --a2a \
  ./check_gcp_subnet_ips \
  -- --allow-unauthenticated

gcloud run services update check-gcp-subnet-ips \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --update-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=gcp-demo-02-307713,GOOGLE_CLOUD_LOCATION=global"

# 2. Deploy network-agent to Cloud Run and point it to check-gcp-subnet-ips on Cloud Run:
adk deploy cloud_run \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --service_name=network-agent \
  --app_name=network_agent \
  --with_ui \
  --a2a \
  ./network_agent \
  -- --allow-unauthenticated

gcloud run services update network-agent \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --update-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=gcp-demo-02-307713,GOOGLE_CLOUD_LOCATION=global,SUBNET_AGENT_TARGET=cloud_run,CHECK_GCP_SUBNET_IPS_BASE_URL=https://check-gcp-subnet-ips-66063681189.asia-southeast2.run.app"
```

### Recipe B: Deploy Native Agent Platform Only (Mode 2: Agent Platform $\rightarrow$ Agent Platform, Zero Cloud Run)
```bash
# 1. Deploy check-gcp-subnet-ips to Agent Platform:
adk deploy agent_engine \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --display_name="check-gcp-subnet-ips" \
  ./check_gcp_subnet_ips

# 2. Copy the new reasoningEngines/<ID> printed above and paste it into
#    CHECK_GCP_SUBNET_IPS_AGENT_ENGINE_ID in network_agent/agent.py, then deploy network-agent:
adk deploy agent_engine \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --display_name="network-agent" \
  ./network_agent
```

### Recipe C: Hybrid (`network-agent` on Cloud Run $\rightarrow$ `check-gcp-subnet-ips` on Agent Platform)
```bash
# Point the Cloud Run `network-agent` service to the Agent Platform `check-gcp-subnet-ips` ReasoningEngine ID:
gcloud run services update network-agent \
  --project=gcp-demo-02-307713 \
  --region=asia-southeast2 \
  --update-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=gcp-demo-02-307713,GOOGLE_CLOUD_LOCATION=global,SUBNET_AGENT_TARGET=agent_platform,CHECK_GCP_SUBNET_IPS_AGENT_ENGINE_ID=projects/66063681189/locations/asia-southeast2/reasoningEngines/2395879817389015040"
```
