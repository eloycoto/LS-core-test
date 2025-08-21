import json
import logging
from pathlib import Path

from .orchestrator_service import orchestrator_mcp

logger = logging.getLogger(__name__)


def filter_schema_for_id_workflows(schema_dict):
    """
    Filter the schema to only include ID-based workflow variant.

    Args:
        schema_dict (dict): The full serverless workflow schema

    Returns:
        dict: Filtered schema with only ID-based workflow support
    """
    # Create a deep copy to avoid modifying original
    filtered_schema = json.loads(json.dumps(schema_dict))

    # Remove the "key" property from the main properties
    if "properties" in filtered_schema and "key" in filtered_schema["properties"]:
        del filtered_schema["properties"]["key"]

    # Update the oneOf constraint to only require ID-based workflow
    if "oneOf" in filtered_schema:
        # Keep only the ID-based variant
        filtered_schema["oneOf"] = [
            {
                "required": [
                    "id",
                    "specVersion",
                    "states"
                ]
            }
        ]

    # Update description to reflect the filtering
    if "description" in filtered_schema:
        filtered_schema["description"] = (
            "Serverless Workflow specification - workflow schema (ID-based workflows only)"
        )

    return filtered_schema


def count_tokens_estimate(text):
    """
    Rough estimate of tokens for comparison.
    This is a simple approximation - actual token count depends on the tokenizer used.
    """
    # Simple approximation: ~4 characters per token for JSON
    return len(text) // 4


@orchestrator_mcp.tool()
def get_filtered_schema_rules(session_id: str) -> str:
    """
    Extract and filter the serverless workflow JSON schema to only include ID-based workflows.
    
    This tool reads the full consolidated serverless workflow schema and creates a filtered
    version that removes the "key"-based workflow variant, keeping only the ID-based variant.
    This significantly reduces the schema size and token count for more efficient processing.
    
    The tool:
    1. Loads the full JSON schema from serverless-workflow/consolidated_workflow_schema.json
    2. Removes the "key" property from root properties
    3. Updates the oneOf constraint to only allow ID-based workflows (requiring "id", "specVersion", "states")
    4. Keeps all shared definitions and properties intact
    5. Saves the filtered schema to serverless-workflow/id_based_workflow_schema.json
    6. Provides token count reduction statistics
    
    Returns the filtered schema as a JSON string along with reduction statistics.
    """
    logger.info(f"get_filtered_schema_rules for session_id='{session_id}'")

    try:
        # Define paths
        input_path = Path("serverless-workflow/consolidated_workflow_schema.json")
        output_path = Path("serverless-workflow/id_based_workflow_schema.json")

        # Check if input file exists
        if not input_path.exists():
            return f"❌ Error: Input file does not exist: {input_path.resolve()}"

        # Load the original schema
        with open(input_path, 'r', encoding='utf-8') as f:
            original_schema = json.load(f)

        # Filter the schema
        filtered_schema = filter_schema_for_id_workflows(original_schema)
        import ipdb; ipdb.set_trace()
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the filtered schema
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_schema, f, indent=2, ensure_ascii=False)

        # Calculate token reduction statistics
        original_json = json.dumps(original_schema, separators=(',', ':'))
        filtered_json = json.dumps(filtered_schema, separators=(',', ':'))

        original_tokens = count_tokens_estimate(original_json)
        filtered_tokens = count_tokens_estimate(filtered_json)
        reduction = original_tokens - filtered_tokens
        reduction_percent = (reduction / original_tokens) * 100 if original_tokens > 0 else 0

        # Calculate file size reduction
        original_size = len(original_json)
        filtered_size = len(filtered_json)
        size_reduction = original_size - filtered_size
        size_reduction_percent = (size_reduction / original_size) * 100 if original_size > 0 else 0

        result = f"""✅ Filtered schema successfully created!

📁 Files:
- Input:  {input_path.resolve()}
- Output: {output_path.resolve()}

📊 Token Count Reduction:
- Original schema: ~{original_tokens:,} tokens
- Filtered schema: ~{filtered_tokens:,} tokens
- Reduction: ~{reduction:,} tokens ({reduction_percent:.1f}%)

📁 File Size Reduction:
- Original schema: {original_size:,} bytes
- Filtered schema: {filtered_size:,} bytes
- Reduction: {size_reduction:,} bytes ({size_reduction_percent:.1f}%)

🎯 Schema Changes Made:
- Removed 'key' property from root properties
- Updated oneOf constraint to only allow ID-based workflows
- Kept all shared definitions and properties intact
- Updated description to reflect ID-only support

The filtered schema now only supports workflows with the ID-based variant requiring:
["id", "specVersion", "states"]

This makes the schema more token-efficient for future processing while maintaining
all the necessary definitions for building valid serverless workflows."""

        return result

    except json.JSONDecodeError as e:
        return f"❌ Error: Invalid JSON in input file: {e}"
    except Exception as e:
        return f"❌ Error: {e}"
