from typing import Any
from app.domain.models import Gift

# Whitelisted field paths and their allowed operations and target types
ALLOWED_FIELDS = {
    "full_name": {"type": str, "ops": {"set", "clear", "confirm"}},
    "home_address": {"type": str, "ops": {"set", "clear", "confirm"}},
    "covers_worldwide_assets": {"type": bool, "ops": {"set", "clear", "confirm"}},
    "has_children": {"type": bool, "ops": {"set", "clear", "confirm"}},
    "children": {"type": list, "item_type": str, "ops": {"set", "add", "remove", "clear", "confirm"}},
    "executor.name": {"type": str, "ops": {"set", "clear", "confirm"}},
    "executor.relationship": {"type": str, "ops": {"set", "clear", "confirm"}},
    "specific_gifts": {"type": list, "item_type": Gift, "ops": {"set", "add", "remove", "clear", "confirm"}},
    "additional_wishes": {"type": list, "item_type": str, "ops": {"set", "add", "remove", "clear", "confirm"}},
}


class ValidationError(ValueError):
    """Raised when field path, operation, or value fails validation."""
    pass


def validate_operation_and_value(field: str, op: str, value: Any) -> Any:
    """Validate field path, operation type, and value type.
    Returns validated/coerced value.
    """
    if field not in ALLOWED_FIELDS:
        raise ValidationError(f"Unknown field path: '{field}'")

    field_spec = ALLOWED_FIELDS[field]
    allowed_ops = field_spec["ops"]
    if op not in allowed_ops:
        raise ValidationError(f"Operation '{op}' is not allowed for field '{field}'. Allowed: {sorted(allowed_ops)}")

    if op in ("clear", "confirm"):
        return value

    expected_type = field_spec["type"]

    # String scalar validation
    if expected_type is str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"Field '{field}' expects a non-empty string, got {type(value).__name__}: {value!r}")
        return value.strip()

    # Boolean scalar validation
    if expected_type is bool:
        if not isinstance(value, bool):
            raise ValidationError(f"Field '{field}' expects a boolean (True/False), got {type(value).__name__}: {value!r}")
        return value

    # List validation
    if expected_type is list:
        item_type = field_spec["item_type"]

        if op == "remove":
            # For remove, allow either item or string identifier
            if item_type is Gift and isinstance(value, str) and value.strip():
                return value.strip()
            return _validate_list_item(field, item_type, value)

        if op == "add":
            return _validate_list_item(field, item_type, value)

        if op == "set":
            if not isinstance(value, list):
                # If a single item was provided for set, allow it if it can be coerced or wrap it
                if item_type is str and isinstance(value, str) and value.strip():
                    return [value.strip()]
                if item_type is Gift and isinstance(value, (dict, Gift)):
                    return [_validate_list_item(field, item_type, value)]
                raise ValidationError(f"Field '{field}' expects a list, got {type(value).__name__}: {value!r}")

            validated_list = []
            for item in value:
                validated_list.append(_validate_list_item(field, item_type, item))
            return validated_list

    raise ValidationError(f"Unsupported validation for field '{field}'")


def _validate_list_item(field: str, item_type: Any, item: Any) -> Any:
    if item_type is str:
        if not isinstance(item, str) or not item.strip():
            raise ValidationError(f"Item in '{field}' must be a non-empty string, got {item!r}")
        return item.strip()

    if item_type is Gift:
        if isinstance(item, Gift):
            if not item.item.strip():
                raise ValidationError(f"Gift item in '{field}' must have a non-empty description.")
            return item
        if isinstance(item, dict):
            if "item" not in item or not str(item["item"]).strip():
                raise ValidationError(f"Gift in '{field}' must have a non-empty 'item' string.")
            return Gift(
                item=str(item["item"]).strip(),
                recipient=str(item["recipient"]).strip() if item.get("recipient") else None,
            )
        raise ValidationError(f"Item in '{field}' must be a Gift object or dict with 'item', got {type(item).__name__}")

    raise ValidationError(f"Unknown item type for '{field}'")
