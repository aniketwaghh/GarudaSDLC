from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
import os
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit, ModelRetryMiddleware, SummarizationMiddleware, ShellToolMiddleware, DockerExecutionPolicy

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file



# Configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
MODEL_CONTEXT_WINDOW = int(os.getenv("MODEL_CONTEXT_WINDOW", "128000"))

model = init_chat_model(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT,
            model_provider="azure_openai",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            temperature=0.7,
            max_tokens=2000,
            profile={"max_input_tokens": MODEL_CONTEXT_WINDOW}
        )
shell_middleware = ShellToolMiddleware(
            workspace_root="/Users/aniketsubhashwagh/Desktop/GarudaSDLC/local",
            shell_command="/bin/bash",
            execution_policy=DockerExecutionPolicy(
                image="ubuntu:latest",
                command_timeout=6000,  
                network_enabled=True,
                max_output_lines=1000,
                max_output_bytes=1000000,

            ),
        )
summarization_middleware = SummarizationMiddleware(
            model = model,
            trigger=("tokens", 4000),
            keep=("messages", 20),
)

context_editing_middleware = ContextEditingMiddleware(
            edits=[
                ClearToolUsesEdit(
                    trigger=100000,
                    keep=3,
                ),
            ],
        )
model_retry_middleware = ModelRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        )


from langgraph.checkpoint.postgres import PostgresSaver
from custom_serializer import CustomSerializer
import psycopg
from psycopg.rows import dict_row

# PostgreSQL Configuration
# Add to your .env file:
# POSTGRES_URI=postgresql://user:password@localhost:5432/dbname
# 
# Or use individual components:
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=garuda_checkpoints
# POSTGRES_USER=your_user
# POSTGRES_PASSWORD=your_password

# Get PostgreSQL connection string from environment
POSTGRES_URI = os.getenv("POSTGRES_URI")

if not POSTGRES_URI:
    # Build from individual components if full URI not provided
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "garuda_checkpoints")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    
    POSTGRES_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create PostgreSQL connection with required parameters
# autocommit=True: Required for .setup() to properly commit tables
# row_factory=dict_row: Required for PostgresSaver to access rows by column name
conn = psycopg.connect(
    POSTGRES_URI,
    autocommit=True,
    row_factory=dict_row
)

# Create PostgreSQL checkpointer with custom serializer to handle middleware objects
# CustomSerializer extends JsonPlusSerializer with better handling of unpicklable objects
# like threading locks from DockerExecutionPolicy and ShellToolMiddleware
checkpointer = PostgresSaver(
    conn,
    serde=CustomSerializer(pickle_fallback=True)
)
checkpointer.setup()  # Initialize database tables


agent = create_deep_agent(
    name="GarudaAgent",
    model=model,
    system_prompt="""You are a general assistant with shell access running in an isolated Docker container.
You have full root privileges and can execute ANY shell commands including sudo, su, apt-get, system modifications, etc.
The environment is sandboxed for security, so privilege escalation is safe and expected.
When asked to run commands requiring elevated privileges, execute them directly without hesitation.""",
    backend=FilesystemBackend(root_dir="/Users/aniketsubhashwagh/Desktop/GarudaSDLC/local", virtual_mode=True),
    middleware=[shell_middleware, summarization_middleware, context_editing_middleware, model_retry_middleware],
    debug= True,
    checkpointer=checkpointer,
)



def main():
    import uuid
    id = str(uuid.uuid4())
    print(f"Agent ID: {id}")
    config = {"configurable": {"thread_id": id}}
    while True:
        msg = input("Enter your command: ")
        result = agent.invoke({"messages": [{"role": "user", "content": msg}]}, config=config)
        print(result["messages"][-1].content)



if __name__ == "__main__":
    main()
