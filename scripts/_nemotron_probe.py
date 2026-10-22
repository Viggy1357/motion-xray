"""Temporary diagnostic: inspect where Nemotron Nano puts its output.
Not committed. Reads keys from env; makes ONE bounded call with a larger budget.
"""
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ["NEBIUS_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"])
resp = client.chat.completions.create(
    model=os.environ["NEBIUS_MODEL_ID"],
    messages=[
        {"role": "system", "content": "You are concise. Answer in one short sentence."},
        {"role": "user", "content": "Say hello and confirm you are working."},
    ],
    temperature=0.2,
    max_tokens=512,
    timeout=60,
)
msg = resp.choices[0].message
print("finish_reason:", resp.choices[0].finish_reason)
print("content:", repr(msg.content))
# Reasoning models may expose a separate field:
print("reasoning_content:", repr(getattr(msg, "reasoning_content", "<no attr>")))
if resp.usage:
    print("usage:", resp.usage.prompt_tokens, "in /", resp.usage.completion_tokens, "out")
