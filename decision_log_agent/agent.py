from google.adk.agents import Agent
from google.adk.apps import App
import os

from decision_log_agent.tools import save_decision_log, query_decision_logs

# Load the system prompt from system_prompt.md
current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, "system_prompt.md")

with open(prompt_path, "r") as f:
    system_instruction = f.read()

# Define the root extractor agent
root_agent = Agent(
    name="decision_log_extractor",
    instruction=system_instruction,
    model="gemini-2.5-flash",  # Fast and excellent at tool calling
    tools=[save_decision_log, query_decision_logs]
)

app = App(root_agent=root_agent, name="decision_log_agent")
