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
    "work_branch": "string",
    "post_checkout": "string",
    "build_command": "string",
    "single_tu_command": "string",
    "timestamp": "ISO datetime"
  }
]
```

#### `POST /api/repos`
**Description**: Add a new repository configuration

**Request Body**:
```json
{
  "name": "string (required)",
  "url": "string (required)",
  "work_branch": "string (required)",
  "post_checkout": "string (optional)",
  "build_command": "string (optional)",
  "single_tu_command": "string (optional)"
}
```

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
  "work_branch": "string (required)",
  "type": "commit",
  "commit_hash": "string (required for commit type)",
  "description": "string (required)",
  "validators": ["asm", "ast", "warnings"],
  "allow_reorder": true/false
}
```

**Request Body** (for patch type):
- Content-Type: `multipart/form-data`
- Fields: Same as above (except commit_hash)
- File: `patch_file` (required for patch type)

**Response**:
```json
{
  "id": "uuid",
  "repo_name": "string",
  "repo_url": "string",
  "work_branch": "string",
  "type": "string",
  "description": "string",
  "validators": ["string"],
  "allow_reorder": boolean,
  "timestamp": "ISO datetime",
  "commit_hash": "string (if type=commit)",
  "patch_path": "string (if type=patch)"
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

### 2.3 Queue Management

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

### 2.4 CppDev Tools

#### `POST /api/cppdev/commit`
**Description**: Submit a direct commit from cppDev for validation

**Request Body**:
```json
{
  "repo_name": "string (required)",
  "repo_url": "string (required)",
  "work_branch": "string (required)",
  "commit_hash": "string (required)",
  "message": "string (optional)"
}
```

**Response**: Same as POST /api/mods response

---
