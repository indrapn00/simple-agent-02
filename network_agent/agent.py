import os
from google.adk.agents.llm_agent import Agent

# Ensure Gemini model calls inside Cloud Run or Vertex AI Agent Engine (asia-southeast2)
# route to Vertex AI's global endpoint in Argolis projects:
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"


# ============================================================================
# FORK 1 (NOW AN AGENT!): Sub-Agent for GCP Subnet IP Calculation
# ============================================================================
# In simple-agent-01, `check_gcp_subnet_ips` was a plain Python function (🔧).
# In simple-agent-02, `check_gcp_subnet_ips` is promoted to a full AI Sub-Agent (🤖)
# with its own Gemini model and instructions, delegated to by `network_agent`!

check_gcp_subnet_ips = Agent(
    model="gemini-2.5-flash",
    name="check_gcp_subnet_ips",
    description=(
        "A dedicated GCP Subnet Calculator Sub-Agent that calculates total IPs, "
        "usable IPs, netmask, and the 4 GCP-reserved IP addresses for any IPv4 CIDR block."
    ),
    instruction=(
        "You are the `check_gcp_subnet_ips` specialist Sub-Agent. "
        "Whenever `network_agent` delegates a subnet CIDR question to you (for example, '10.10.0.0/28'):\n"
        "1. Calculate the total IPv4 addresses in the CIDR block (2^(32 - prefix)).\n"
        "2. Subtract the 4 IP addresses reserved by Google Cloud VPC in every primary subnet range:\n"
        "   - Network address (first IP, e.g. .0)\n"
        "   - Default gateway (second IP, e.g. .1)\n"
        "   - Second-to-last address (reserved by GCP, e.g. .14 in a /28)\n"
        "   - Broadcast address (last IP, e.g. .15 in a /28)\n"
        "3. Present a clear summary showing: CIDR, Netmask, Total Addresses, Usable IPs in GCP VPC, "
        "and the exact 4 GCP-Reserved IP addresses.\n"
        "4. If the user later asks about Agent Gateway architecture or traffic modes, transfer control back to `network_agent`."
    ),
)


# ============================================================================
# FORK 2 (KEPT AS A FUNCTION!): Python Function Tool in `network_agent`
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
# MAIN AGENT (`network_agent`): Connects Sub-Agent (Fork 1) + Function (Fork 2)
# ============================================================================

root_agent = Agent(
    model="gemini-2.5-flash",
    name="network_agent",
    description="Main Google Cloud Networking & Agent Gateway orchestrator agent.",
    instruction=(
        "You are `network_agent`, the Main Google Cloud Networking & Agent Gateway Assistant. "
        "Keep answers clear, structured, and beginner-friendly.\n"
        "- Whenever the user asks about subnet CIDRs, IP sizing, or usable GCP IPs, delegate/transfer the task "
        "to your Sub-Agent `check_gcp_subnet_ips`.\n"
        "- Whenever the user asks about Agent Gateway architecture, deployment modes, or traffic flows, "
        "call your function tool `recommend_agent_gateway_mode`."
    ),
    sub_agents=[check_gcp_subnet_ips],          # <-- Fork 1: Formed as an Agent (🤖)
    tools=[recommend_agent_gateway_mode],       # <-- Fork 2: Kept as a Function (🔧)
)
