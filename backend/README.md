# Backend - Shared Service Code

**This is NOT a standalone service!**

This folder contains shared service code used by the microservices architecture.

## Structure

```
backend/
└── app/
    └── services/
        └── annoteator_service.py   # Drum transcription logic (used by worker-service)
```

## Usage

The `worker-service` imports this code:

```python
# worker-service/worker.py
sys.path.append('/app/backend')
from app.services.annoteator_service import AnNOTEatorService
```

## Why This Exists

This folder used to be a monolithic backend that did everything (API + processing).
Now we use microservices:
- `api-service/` - Handles HTTP requests
- `worker-service/` - Does ML processing (imports this code)

The `backend/` folder remains because it contains the shared processing logic.

## Do NOT Add

❌ API routes (use `api-service/` instead)  
❌ Config files (each service has its own)  
❌ Main entrypoint (services have their own)

## Do Add

✅ Shared processing logic  
✅ Shared utilities used by multiple services  
✅ ML model interfaces
