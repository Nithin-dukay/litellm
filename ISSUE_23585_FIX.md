# Fix for Issue #23585: Tool Registry Writer Timestamp Type Mismatch

## Problem

The `tool_registry_writer.py` was throwing a PostgreSQL type mismatch error when inserting into `LiteLLM_ToolTable`:

```
ERROR: column "created_at" is of type timestamp without time zone but expression is of type text
```

## Root Cause

The issue occurred in two functions:

1. **`batch_upsert_tools()`** - Lines 86-120
2. **`update_tool_policy()`** - Lines 180-220

Both functions were explicitly passing Python `datetime.now(timezone.utc)` objects to Prisma's `upsert()` method for the `created_at`, `updated_at`, and `last_used_at` fields. When Prisma serialized these datetime objects to SQL, they were being converted to text strings instead of proper PostgreSQL timestamp types.

## Solution

The fix leverages Prisma's built-in timestamp handling:

### 1. Removed Explicit Timestamp Assignments

- **`created_at`**: Removed from create data - handled by Prisma's `@default(now())` decorator
- **`updated_at`**: Removed from both create and update data - handled by Prisma's `@updatedAt` decorator
- **`last_used_at`**: Removed from both create and update data (was causing the same issue)

### 2. Let Prisma Handle Timestamps Automatically

The Prisma schema defines these fields with automatic timestamp management:

```prisma
model LiteLLM_ToolTable {
  // ...
  last_used_at   DateTime?          // Optional timestamp
  created_at     DateTime @default(now())
  updated_at     DateTime @default(now()) @updatedAt
  // ...
}
```

- `@default(now())` - Automatically sets the current timestamp on creation
- `@updatedAt` - Automatically updates the timestamp on every update operation

### 3. Conditional Field Assignment

For optional fields like `key_hash`, `team_id`, `key_alias`, and `user_agent`, the fix now only includes them in the create data if they are not `None`. This prevents passing `None` values explicitly and lets Prisma handle the defaults.

## Changes Made

### File: `litellm/proxy/db/tool_registry_writer.py`

#### `batch_upsert_tools()` function:
- Removed `now = datetime.now(timezone.utc)` variable
- Removed `last_used_at: now` from create data
- Removed `updated_at: now` and `last_used_at: now` from update data
- Added conditional assignment for optional fields (`key_hash`, `team_id`, `key_alias`, `user_agent`)

#### `update_tool_policy()` function:
- Removed `now = datetime.now(timezone.utc)` variable
- Removed `created_at: now` and `updated_at: now` from create data
- Removed `updated_at: now` from update data

### File: `tests/test_litellm/proxy/db/test_tool_registry_writer.py`

Updated the test `test_batch_upsert_tools_calls_upsert()` to verify that:
- `created_at` is NOT in the create data (Prisma handles it)
- `updated_at` is NOT in the update data (Prisma handles it)

## Expected Behavior After Fix

1. **No Type Mismatch Errors**: Prisma will generate proper PostgreSQL timestamp values instead of text strings
2. **Automatic Timestamp Management**: All timestamp fields will be managed by Prisma's decorators
3. **Cleaner Code**: Removed manual datetime handling that was causing the issue
4. **Tests Pass**: Updated tests reflect the correct behavior

## Verification

To verify the fix works:

1. Run the unit tests:
   ```bash
   pytest tests/test_litellm/proxy/db/test_tool_registry_writer.py -v
   ```

2. Test with actual database operations:
   - Start the LiteLLM proxy with PostgreSQL
   - Make LLM calls that use tools
   - Verify no timestamp errors appear in logs
   - Check that tool registry entries are created correctly in the database

## Additional Notes

- The error message mentioned `call_policy` which doesn't exist in the current schema. This suggests there may be old migrations or cached SQL. After applying this fix, ensure database migrations are up to date.
- The schema correctly defines `input_policy` and `output_policy` fields, not `call_policy`.
