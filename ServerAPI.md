# LevelUp Server Interface

## 1. Introduction (TBD)

## 2. API Documentation

### Base URL: `/api`

### 2.1 Repository Management

#### `GET /api/repos`
**Description**: Retrieve all configured repositories

**Response**:
```json
[
  {
    "id": "uuid",
    "name": "string",
    "url": "string",
    "post_checkout": "string",
    "build_command": "string",
    "single_tu_command": "string",
    "timestamp": "ISO datetime"
  }
]
```

**Note**: Work branch is hardcoded to "levelup-work" and is not configurable.

#### `POST /api/repos`
**Description**: Add a new repository configuration

**Request Body**:
```json
{
  "url": "string (required)",
  "post_checkout": "string (optional)",
  "build_command": "string (optional)",
  "single_tu_command": "string (optional)"
}
```

**Note**: Repository name is automatically extracted from the URL.

**Response**: Same as single repository object above

---

### 2.2 Mod Management

#### `POST /api/mods`
**Description**: Submit a new mod for processing

**Request Body** (for commit type):
```json
{
  "repo_name": "string (required)",
  "repo_url": "string (required)",
  "type": "commit",
  "commit_hash": "string (required for commit type)",
  "description": "string (required)",
  "validators": ["asm", "ast", "warnings"]
}
```

**Request Body** (for builtin type):
```json
{
  "repo_name": "string (required)",
  "repo_url": "string (required)",
  "type": "builtin",
  "mod_type": "string (required for builtin type)",
  "description": "string (required)",
  "validators": ["asm", "ast", "warnings"]
}
```

**Response**:
```json
{
  "id": "uuid",
  "repo_name": "string",
  "repo_url": "string",
  "type": "string",
  "description": "string",
  "validators": ["string"],
  "timestamp": "ISO datetime",
  "commit_hash": "string (if type=commit)",
  "mod_type": "string (if type=builtin)"
}
```

#### `GET /api/mods/{mod_id}/status`
**Description**: Get the status of a specific mod

**Response**:
```json
{
  "status": "queued|processing|success|failed|error",
  "message": "string",
  "validation_results": [
    {
      "file": "string",
      "valid": boolean
    }
  ],
  "timestamp": "ISO datetime"
}
```

---

### 2.4 Queue Management

#### `GET /api/queue/status`
**Description**: Get overall queue status and all results

**Response**:
```json
{
  "queue_size": integer,
  "results": {
    "mod_id": {
      "status": "string",
      "message": "string",
      "validation_results": [...],
      "timestamp": "string"
    }
  },
  "timestamp": "ISO datetime"
}
```

---

### 2.3 Available Resources

#### `GET /api/available/mods`
**Description**: Get list of available mod types

**Response**:
```json
[
  {
    "id": "remove_inline",
    "name": "Remove Inline Keywords"
  },
  {
    "id": "add_override",
    "name": "Add Override Keywords"
  },
  {
    "id": "replace_ms_specific",
    "name": "Replace MS-Specific Syntax"
  }
]
```

#### `GET /api/available/validators`
**Description**: Get list of available validator types

**Response**:
```json
[
  {
    "id": "asm",
    "name": "Assembly Comparison"
  }
]
```

#### `GET /api/available/compilers`
**Description**: Get list of available compiler types

**Response**:
```json
[
  {
    "id": "msvc",
    "name": "Microsoft Visual C++"
  }
]
```

**Note**: The `id` field for each resource is stable and should be used when referencing these resources in API requests. The `name` field is human-readable and may change.

---

### 2.5 CppDev Tools

#### `POST /api/cppdev/commit`
**Description**: Submit a direct commit from cppDev for validation

**Request Body**:
```json
{
  "repo_name": "string (required)",
  "repo_url": "string (required)",
  "commit_hash": "string (required)",
  "message": "string (optional)"
}
```

**Response**: Same as POST /api/mods response

---
