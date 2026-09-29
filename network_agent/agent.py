import os
import warnings
from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

warnings.filterwarnings("ignore", message=".*EXPERIMENTAL.*")

# Ensure Gemini model calls inside Cloud Run or Vertex AI Agent Engine (asia-southeast2)
# route to Vertex AI's global endpoint in Argolis projects:
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

# ============================================================================
# IMPORTANT: CONFIGURE YOUR `check-gcp-subnet-ips` A2A AGENT URL HERE
# ============================================================================
# If you delete and recreate the `check-gcp-subnet-ips` Cloud Run service and get
# a new URL, either:
#   1. Replace `<REPLACE_WITH_CHECK_GCP_SUBNET_IPS_CLOUD_RUN_URL>` below with your
#      new Cloud Run base URL (e.g. "https://check-gcp-subnet-ips-xxxxx.asia-southeast2.run.app"), OR
#   2. Pass `--update-env-vars="CHECK_GCP_SUBNET_IPS_BASE_URL=https://..."` on Cloud Run.
#
# NOTE: This URL is used by `network_agent` in BOTH Cloud Run AND Agent Platform
# (Vertex AI Agent Engine) whenever `network_agent` calls `check_gcp_subnet_ips` via A2A!
CHECK_GCP_SUBNET_IPS_BASE_URL = os.environ.get(
    "CHECK_GCP_SUBNET_IPS_BASE_URL",
    "https://<REPLACE_WITH_CHECK_GCP_SUBNET_IPS_CLOUD_RUN_URL>",
)

CHECK_GCP_SUBNET_IPS_CARD_URL = os.environ.get(
    "CHECK_GCP_SUBNET_IPS_AGENT_CARD_URL",
    f"{CHECK_GCP_SUBNET_IPS_BASE_URL.rstrip('/')}/a2a/check_gcp_subnet_ips/.well-known/agent-card.json",
)


# ============================================================================
# FORK 1 (SEPARATELY DEPLOYED REMOTE AGENT!): `check_gcp_subnet_ips` via A2A
# ============================================================================
# Instead of running inside the same container/process, `check_gcp_subnet_ips`
# is deployed as its own standalone Agent service in asia-southeast2.
# `network_agent` calls it over the network using the Agent-to-Agent (A2A) protocol!

check_gcp_subnet_ips = RemoteA2aAgent(
    name="check_gcp_subnet_ips",
    description=(
        "Separately deployed GCP Subnet Calculator Agent that calculates total IPs, "
        "usable IPs, netmask, and the 4 GCP-reserved IP addresses for any IPv4 CIDR block."
    ),
    agent_card=CHECK_GCP_SUBNET_IPS_CARD_URL,
)


# ============================================================================
# FORK 2 (KEPT AS A LOCAL FUNCTION!): Python Function Tool in `network_agent`
# ============================================================================

def recommend_agent_gateway_mode(traffic_pattern: str) -> dict:
    """Recommends the Google Cloud Agent Gateway deployment mode for a given networking scenario.

    Args:
        traffic_pattern: Description of traffic flow (e.g., 'client to agent', 'agent to mcp tool', 'existing ALB', 'existing SWP').
    """
    pattern = traffic_pattern.lower()
    if "alb" in pattern or "load balancer" in pattern or "swp" in pattern or "secure web proxy" in pattern:
        return {
            "recommended_mode": "Self-Managed Agent Gateway (selfManaged)",
            "attachment_target": "Existing Application Load Balancer (ALB) or Secure Web Proxy (SWP)",
            "how_it_works": (
                "Attaches Agent Gateway governance policies via Service Extensions to your existing "
                "Cloud Load Balancing or Secure Web Proxy infrastructure while binding to Agent Registry."
            ),
        }
    elif "egress" in pattern or "tool" in pattern or "mcp" in pattern or "anywhere" in pattern:
        return {
            "recommended_mode": "Google-Managed Agent Gateway (googleManaged: AGENT_TO_ANYWHERE)",
            "networking_features": "PSC-Interface Egress (networkAttachment) + DNS Peering to your VPC",
            "how_it_works": (
                "Google orchestrates a managed proxy in a tenant project with an mTLS endpoint, "
                "governing outbound Agent-to-Tool (MCP) and Agent-to-Agent (A2A) calls using Agent Registry bindings."
            ),
        }
    else:
        return {
            "recommended_mode": "Google-Managed Agent Gateway (googleManaged: CLIENT_TO_AGENT)",
            "networking_features": "Managed mTLS Endpoint + Root CA validation + Agent Registry governance",
            "how_it_works": (
                "Protects inbound Client-to-Agent or Agent-to-Agent (A2A) traffic with Google-managed "
                "proxy orchestration and identity/registry enforcement."
            ),
        }


# ============================================================================
# MAIN AGENT (`network_agent`): Calls Remote Agent (Fork 1) + Local Function (Fork 2)
# ============================================================================

root_agent = Agent(
    model="gemini-2.5-flash",
    name="network_agent",
    description="Main Google Cloud Networking & Agent Gateway orchestrator agent.",
    instruction=(
        "You are `network_agent`, the Main Google Cloud Networking & Agent Gateway Assistant. "
        "Keep answers clear, structured, and beginner-friendly.\n"
        "- Whenever the user asks about subnet CIDRs, IP sizing, or usable GCP IPs, delegate/transfer the task "
        "to the remote `check_gcp_subnet_ips` agent.\n"
        "- Whenever the user asks about Agent Gateway architecture, deployment modes, or traffic flows, "
        "call your local function tool `recommend_agent_gateway_mode`."
    ),
    sub_agents=[check_gcp_subnet_ips],          # <-- Fork 1: Remote Agent over A2A (🤖)
    tools=[recommend_agent_gateway_mode],       # <-- Fork 2: Local Python Function (🔧)
)
