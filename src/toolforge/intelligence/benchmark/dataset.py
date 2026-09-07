from __future__ import annotations

from toolforge.intelligence.dataset import MappingDataset, MappingExample

BENCHMARK_EXAMPLES: list[dict] = [
    {
        "tool_name": "drop_database_partition",
        "description": "Permanently delete a database partition and remove all stored rows.",
        "input_schema": {
            "type": "object",
            "properties": {
                "partition_id": {"type": "string"},
                "force": {"type": "boolean"},
            },
            "required": ["partition_id"],
        },
        "expected_service": "database",
        "expected_operation": "drop_partition",
        "expected_domain": "database",
        "expected_category": "mutation",
        "expected_risk_level": "destructive",
    },
    {
        "tool_name": "get_user_profile",
        "description": "Retrieve user profile details, email, and authentication status.",
        "input_schema": {
            "type": "object",
            "properties": {"user_id": {"type": "integer"}},
            "required": ["user_id"],
        },
        "expected_service": "identity",
        "expected_operation": "query_profile",
        "expected_domain": "identity",
        "expected_category": "query",
        "expected_risk_level": "safe",
    },
    {
        "tool_name": "write_file_contents",
        "description": "Write text or binary data directly to the specified filesystem path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["file_path", "content"],
        },
        "expected_service": "filesystem",
        "expected_operation": "write_file",
        "expected_domain": "filesystem",
        "expected_category": "mutation",
        "expected_risk_level": "idempotent",
    },
    {
        "tool_name": "charge_payment_card",
        "description": "Process an instant credit card transaction for the designated invoice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_cents": {"type": "integer"},
                "currency": {"type": "string"},
                "customer_id": {"type": "string"},
            },
            "required": ["amount_cents", "customer_id"],
        },
        "expected_service": "billing",
        "expected_operation": "process_charge",
        "expected_domain": "payment",
        "expected_category": "transaction",
        "expected_risk_level": "financial",
    },
    {
        "tool_name": "query_vector_index",
        "description": "Execute semantic k-nearest neighbors search across embedding vector index.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query_vector": {"type": "array"},
                "top_k": {"type": "integer"},
            },
            "required": ["query_vector"],
        },
        "expected_service": "search",
        "expected_operation": "vector_search",
        "expected_domain": "search",
        "expected_category": "query",
        "expected_risk_level": "safe",
    },
    {
        "tool_name": "restart_service_container",
        "description": "Forcefully reboot a container instance in the infrastructure cluster.",
        "input_schema": {
            "type": "object",
            "properties": {
                "container_id": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": ["container_id"],
        },
        "expected_service": "infrastructure",
        "expected_operation": "restart_container",
        "expected_domain": "infrastructure",
        "expected_category": "lifecycle",
        "expected_risk_level": "destructive",
    },
    {
        "tool_name": "fetch_weather_forecast",
        "description": "Fetch current weather conditions and 7-day atmospheric forecast.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
            },
            "required": ["latitude", "longitude"],
        },
        "expected_service": "weather",
        "expected_operation": "get_forecast",
        "expected_domain": "weather",
        "expected_category": "query",
        "expected_risk_level": "safe",
    },
    {
        "tool_name": "revoke_access_token",
        "description": "Invalidate and revoke an active OAuth token immediately.",
        "input_schema": {
            "type": "object",
            "properties": {"token_id": {"type": "string"}},
            "required": ["token_id"],
        },
        "expected_service": "auth",
        "expected_operation": "revoke_token",
        "expected_domain": "security",
        "expected_category": "mutation",
        "expected_risk_level": "destructive",
    },
    {
        "tool_name": "generate_audit_report",
        "description": "Compile audit trails into a structured summary report over a date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
            "required": ["start_date", "end_date"],
        },
        "expected_service": "analytics",
        "expected_operation": "generate_report",
        "expected_domain": "analytics",
        "expected_category": "reporting",
        "expected_risk_level": "safe",
    },
    {
        "tool_name": "update_account_settings",
        "description": "Update user preferences such as notification toggles and interface theme.",
        "input_schema": {
            "type": "object",
            "properties": {
                "theme": {"type": "string"},
                "notifications": {"type": "boolean"},
            },
        },
        "expected_service": "identity",
        "expected_operation": "update_settings",
        "expected_domain": "identity",
        "expected_category": "configuration",
        "expected_risk_level": "idempotent",
    },
]


def get_default_benchmark_dataset() -> MappingDataset:
    """Return the reproducible 10-tool benchmark dataset."""
    return MappingDataset.from_list([MappingExample(**ex) for ex in BENCHMARK_EXAMPLES])
