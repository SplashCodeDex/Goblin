TypeError: select() got an unexpected keyword argument 'default'
Traceback:
File "W:\CodeDeX\Goblin\ui.py", line 35, in <module>
model = ui.select(
options=["gpt4o", "gpt-4.1", "claude-3-5-sonnet-latest", "llama3.1", "gemini-2.5-flash", "gemini-2.5-flash-preview-09-2025", "gemini-2.5-flash-lite"],
default="gpt4o",
label="Select LLM Model",
)
