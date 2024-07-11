# %% Imports
import os
from typing_extensions import override
from openai import AssistantEventHandler
from openai import AzureOpenAI

# %% Constants
FILES_DIR = "/home/sabacherli/dev/gunvor-surveys/data"

# East US 2
API_KEY = "7df1f37456ac4831b42ad9717d8a3829"
AZURE_OPENAI_ENDPOINT = "https://zgebs-eus2.openai.azure.com/"

# East US
# API_KEY = "6628e7a5bf61412db4e80cafa408d91c"
# AZURE_OPENAI_ENDPOINT = "https://zgebs.openai.azure.com/"

# %% Functions
def get_assistant(name: str):
    """Retrieve an existing assistant or create a new one."""


    assistant = client.beta.assistants.create(
  name="Business Analyst Assistant",
  instructions="You are a business analyst for a consulting company that is analysing the current state of affairs and the key challenges of an commodity trading company with respect to data, analytics and AI.",
  model="zgebs",
  tools=[{"type": "file_search"}],
)

# %% Create a new Assistant with File Search Enabled
client = AzureOpenAI(
    api_key= API_KEY,
    api_version="2024-05-01-preview",
    azure_endpoint = AZURE_OPENAI_ENDPOINT
  )


# %% Upload files and add them to a Vector Store
vector_store = client.beta.vector_stores.create(name="Use Cases")

file_paths = [os.path.join(FILES_DIR, filename) for filename in os.listdir(FILES_DIR)]
file_streams = [open(path, "rb") for path in file_paths]

file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
  vector_store_id=vector_store.id, files=file_streams
)
 
print(file_batch.status)
print(file_batch.file_counts)

# %% Update the assistant to to use the new Vector Store
assistant = client.beta.assistants.update(
  assistant_id=assistant.id,
  tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
)

# %% Create a thread 
thread = client.beta.threads.create(
  messages=[
    {
      "role": "user",
      "content": "Analyse the use cases of a commodity trading company.",
    }
  ]
)
 
# The thread now has a vector store with that file in its tool resources.
print(thread.tool_resources.file_search)

# %% Run the thread without streaming
run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
)

messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

message_content = messages[0].content[0].text
annotations = message_content.annotations
citations = []
for index, annotation in enumerate(annotations):
    message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
    if file_citation := getattr(annotation, "file_citation", None):
        cited_file = client.files.retrieve(file_citation.file_id)
        citations.append(f"[{index}] {cited_file.filename}")

print(message_content.value)
print("\n".join(citations))

