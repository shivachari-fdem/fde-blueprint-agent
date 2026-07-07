# fde-blueprint-agent
## Testing the Human-in-the-Loop (HITL) Workflow

To test the agent's tool execution guardrails via the Swagger UI (`/docs`), you must follow this exact 3-step sequence:

1. **POST `/init`**: Initialize a new session and generate a `session_id`.
2. **POST `/chat`**: Send a prompt that requires a tool (e.g., "Get me a cost estimate for Compute Engine at a High usage tier"). The agent will pause and return a `requires_approval` status.
3. **POST `/approve`**: Pass the `session_id`, `function_name`, `arguments`, and `"approve": true` to authorize the execution.

### Architectural Note: Database
Currently, this agent utilizes a local SQLite database (`conversations.db`) for session memory. Because Google Cloud Run instances are stateless, scaling events will clear the conversation history. For production use cases requiring persistent memory, migrate this to a managed database like Cloud SQL for PostgreSQL or Firestore.