import logging

from .orchestrator_service import orchestrator_mcp

logger = logging.getLogger(__name__)

RULES = """

# ORCHESTRATOR WORKFLOW CREATION INSTRUCTIONS

## Planning Phase
1) Analyze the user request and identify the workflow steps
2) Plan the workflow flow: initial state → intermediate states → end state
3) Identify required functions, their types, and operations. **Use orchestrator_orchestrator_get_sample_workflow() for reference examples when unsure about implementation patterns.**
4) Define error scenarios and error handling states
5) Map out state transitions and ensure proper flow validation
6) **MANDATORY**: Always run workflow validation using **orchestrator_compile_workflow()** tool to check compilation and structural integrity. The workflow MUST compile successfully before completion.
7) **MANDATORY**: Always provide a structured workflow preview using **orchestrator_orchestrator_preview_workflow()** tool in PNG format. The format should be like: ![Workflow Preview]($tool_response)


## Validation Rules

### Required Root Fields (ALL MANDATORY):
- `id`: Unique workflow identifier (string, no spaces, alphanumeric + underscores)
- `version`: Always "1.0"
- `specVersion`: Always "0.8"
- `name`: Human-readable workflow name (string)
- `description`: Clear workflow description (string)
- `start`: Name of the initial state (must match a state name in the states array)
- `functions`: Array of function definitions (can be empty but must be present)
- `states`: Array of state definitions (must have at least one state)
- `errors`: Array of error definitions (can be empty but must be present)
- `events`: Array of event definitions (optional but recommended for event-driven workflows)

### Workflow Flow Rules:
- Every state MUST either have `"end": true` OR a valid `transition` field
- The `start` field value MUST match exactly one state name in the states array
- All `transition` values MUST reference existing state names
- All `errorRef` values in `onErrors` MUST reference existing error names
- Functions referenced in `functionRef.refName` MUST exist in the functions array
- No orphaned states (unreachable states) are allowed
- Ensure proper error handling for all critical operations
```json
{
    "id": "myworkflowid",
    "version": "1.0",
    "specVersion": "0.8",
    "name": "User example workflow",
    "description": "And empty workflow",
    "start": "CheckApplication",
    "functions": [ ],
    "states":[],
    "errors": [],
    "events": []
}
```

## Functions

### Function Definition Structure
Each function MUST have exactly these three fields:
- `name`: Unique function identifier (string, used in functionRef.refName)
- `type`: Function type (must be one of: "asyncapi", "custom" "expression", "graphql", "odata", "rest", "rpc")
- `operation`: Operation specification (format depends on type)

### Function Types & Operations

#### 1. Custom Functions (`"type": "custom"`)
For simple operations and logging. Allowed operations:
- `rest:get:<URL>` - HTTP GET request
- `rest:post:<URL>` - HTTP POST request
- `rest:put:<URL>` - HTTP PUT request
- `rest:delete:<URL>` - HTTP DELETE request
- `sysout:INFO` - Log info message
- `sysout:DEBUG` - Log debug message
- `sysout:ERROR` - Log error message

Example:
```json
{
  "name": "getPublicIP",
  "type": "custom",
  "operation": "rest:get:https://ipinfo.io/json"
}
```

#### 2. REST Functions (`"type": "rest"`)
For OpenAPI-based services: `<openapi-url>#<operation-id>`
```json
{
  "name": "getPetById",
  "type": "rest",
  "operation": "https://petstore.swagger.io/v2/swagger.json#getPetById"
}
```

#### 3. RPC Functions (`"type": "rpc"`)
For gRPC services: `<proto-file>#<ServiceName>#<MethodName>`
```json
{
  "name": "listUsers",
  "type": "rpc",
  "operation": "file://myuserservice.proto#UserService#ListUsers"
}
```

#### 4. Expression Functions (`"type": "expression"`)
For gRPC services: `<proto-file>#<ServiceName>#<MethodName>`
```json
{
  "name": "increasePlanRetries",
  "type": "expression",
  "operation": ".planRetries=.planRetries + 1"
}
```

### Function Arguments & Data Binding
Functions can receive arguments from workflow state data:

```json
{
  "functionRef": {
    "refName": "pushData",
    "arguments": {
      "city": ".ip_info.city",
      "ip": ".ip_info.ip",
      "timestamp": ".current_time"
    }
  }
}
```

**Data Binding Rules:**
- Use dot notation to reference state data: `.field_name` or `.nested.field`
- Arguments are optional but must be inside the `functionRef` object when used
- State data from previous actions is accessible using the action result key
- Literal values can be passed without dot notation: `"status": "active"`

## Error Handling

### Error Definition Structure
Errors MUST be defined in the root `errors` array with these required fields:
- `name`: Unique error identifier (string, used in errorRef)
- `code`: Error code (string, typically HTTP status codes)

```json
"errors": [
  {
    "name": "serviceUnavailable",
    "code": "503"
  },
  {
    "name": "unauthorized",
    "code": "401"
  },
  {
    "name": "notFound",
    "code": "404"
  }
]
```

### Error Handling in States
Use `onErrors` array in states to handle specific errors:

```json
"onErrors": [
  {
    "errorRef": "serviceUnavailable",
    "transition": "retryState"
  },
  {
    "errorRef": "unauthorized",
    "transition": "authErrorState"
  }
]
```

**Error Handling Rules:**
- Every `errorRef` MUST reference an existing error name from the errors array
- Every `transition` in onErrors MUST reference an existing state name
- Error handling states should have proper transitions or end conditions
- Consider implementing retry logic for transient failures
- Always provide meaningful error states for critical workflow paths

## States

### State Structure Requirements
Every state MUST have these required fields:
- `name`: Unique state identifier (string, used in transitions)
- `type`: State type (must be "operation", "switch", "event", "delay", or "parallel")
- Either `end: true` OR `transition: "nextStateName"`

### State Types & Examples

#### Operation State (most common)
Executes functions and handles business logic:
```json
{
  "name": "getPublicIP",
  "type": "operation",
  "actions": [
    {
      "functionRef": {
        "refName": "getIP"
      }
    }
  ],
  "onErrors": [
    {
      "errorRef": "serviceUnavailable",
      "transition": "retryState"
    }
  ],
  "transition": "processIPData"
}
```

#### End State Example
```json
{
  "name": "workflowComplete",
  "type": "operation",
  "actions": [
    {
      "functionRef": {
        "refName": "logCompletion"
      }
    }
  ],
  "end": true
}
```

### State Validation Rules:
- `actions` array MUST have at least one entry for operation states
- All `functionRef.refName` values MUST reference existing functions
- `transition` values MUST reference existing state names
- States without transitions MUST have `"end": true`
- State names MUST be unique within the workflow
- The workflow MUST have exactly one state with `"end": true` (the terminal state)

## Events

### Event Definition Structure
Events enable asynchronous, event-driven workflows. Each event MUST have these required fields:
- `name`: Unique event identifier (string, used in event references)
- `source`: CloudEvent source (required for consumed events)
- `type`: CloudEvent type (string, defines the event category)
- `kind`: Event direction - "consumed" (default) or "produced"

### Event Definition Examples

#### Consumed Event (receives external events)
```json
{
  "name": "orderReceived",
  "source": "orders.service",
  "type": "com.example.orders.received",
  "kind": "consumed"
}
```

#### Produced Event (sends events to external systems)
```json
{
  "name": "orderProcessed",
  "type": "com.example.orders.processed",
  "kind": "produced"
}
```

### Event States
Event states wait for and handle CloudEvents:

```json
{
  "name": "WaitForOrder",
  "type": "event",
  "onEvents": [
    {
      "eventRefs": ["orderReceived"],
      "actions": [
        {
          "functionRef": {
            "refName": "processOrder"
          }
        }
      ]
    }
  ],
  "timeouts": {
    "eventTimeout": "PT1H"
  },
  "transition": "OrderProcessed"
}
```

### Event Handling Rules:
- All `eventRefs` MUST reference existing event names from the events array
- Event states MUST have `onEvents` array with at least one entry
- Use `timeouts.eventTimeout` for event waiting limits (ISO 8601 duration format)
- Consider error handling for event timeout scenarios
- Events can carry data accessible in subsequent states via `.eventData`
"""  # noqa: E501


@orchestrator_mcp.tool()
def creation_workflow_rules(session_id: str) -> str:
    """
    **CRITICAL: CALL THIS TOOL FIRST** - Essential orchestrator workflow creation rules.

    This is the PRIMARY reference tool that MUST be called before any workflow creation task.
    Provides comprehensive specifications for creating valid orchestrator workflows:
    - Complete JSON structure with all mandatory fields
    - Function types (custom, rest, rpc, expression) with correct operation formats
    - State definitions, transitions, and flow validation rules
    - Error handling patterns and event management
    - Validation requirements and compilation guidelines

    **Always use this tool at the start of any workflow-related task to ensure compliance.**
    Contains essential context that prevents common workflow creation errors.
    """
    logger.info(f"orchestrator_creation_workflow_rules for session_id='{session_id}'")

    return RULES
