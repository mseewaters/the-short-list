# Best Practices - Vue.js + FastAPI + AWS SAM

## Quick Reference

### CORS
- **Development**: Specific origins with credentials (`examples/cors/fastapi-cors-dev.py`)
- **Production**: Single domain with credentials (`examples/cors/fastapi-cors-prod.py`) 
- **Open**: All origins without credentials (`examples/cors/fastapi-cors-open.py`)
- **Rule**: Cannot use `allow_origins=["*"]` with `allow_credentials=True`

#### ⚠️ CORS Troubleshooting - API Gateway vs Lambda
**The Problem**: CORS can be configured in both API Gateway (SAM template) AND FastAPI (Lambda). This creates conflicts and debugging nightmares.

**Best Approach**: Choose ONE location based on your needs:

**Option 1: API Gateway Only (Recommended for simple CORS)**
```yaml
# In template.yaml - API Gateway handles all CORS
Globals:
  Api:
    Cors:
      AllowMethods: "'OPTIONS,GET,POST,PUT,DELETE'"
      AllowHeaders: "'Content-Type,Authorization'"
      AllowOrigin: "'https://yourdomain.com'"
```
- ✅ No FastAPI CORS middleware needed
- ✅ OPTIONS requests never reach Lambda (faster)
- ❌ Less flexible (same CORS for all endpoints)

**Option 2: FastAPI Only (Recommended for complex CORS)**
```python
# In main.py - Lambda handles all CORS
app.add_middleware(CORSMiddleware, ...)
```
```yaml
# In template.yaml - NO CORS section
# Let FastAPI handle everything
```
- ✅ Per-endpoint CORS control
- ✅ Dynamic origin validation
- ❌ OPTIONS requests hit Lambda (slower)

**Never Do Both**: Having CORS in both places causes:
- Duplicate headers (browser rejects)
- Preflight failures
- Inconsistent behavior between environments

### Imports & Structure
- **Always use absolute imports**: `from app.module import x` (never `from .module import x`)
- **Add `__init__.py`** to every Python folder
- **Handler path**: `app.main.handler` in template.yaml
- **Structure**: API → Services → DAL → DB

### Timezone
- **Store in UTC**: All database timestamps and API responses
- **Convert for display**: Frontend handles local timezone conversion
- **Always timezone-aware**: Use `datetime.now(timezone.utc)`, never `datetime.now()`

### Security
- **Input validation**: Pydantic models for ALL requests (`examples/security/input-validation.py`)
- **Secrets**: Environment variables + AWS Secrets Manager (`examples/security/secrets-management.py`)
- **Authentication**: Secure JWT with expiration (`examples/security/jwt-auth.py`)
- **Rate limiting**: Different limits per endpoint type (`examples/security/rate-limiting.py`)

### Logging
- **Structured JSON**: All logs as key-value pairs (`examples/logging/utils.py`)
- **Auto-request logs**: Middleware logs all HTTP requests (`examples/logging/request-middleware.py`)
- **Correlation IDs**: Track requests end-to-end
- **Debug toggle**: `DEBUG_MODE=true` environment variable

## Implementation Guidelines

### 1. CORS Setup
**Choose ONE approach** (never both):

**API Gateway CORS** (simple, recommended):
- Define CORS in `template.yaml` only (`examples/cors/sam-template-cors.yaml`)
- Remove all FastAPI CORS middleware
- Deploy: `sam build && sam deploy` after CORS changes
- Test: `curl -i -X OPTIONS https://your-api-url/endpoint`

**FastAPI CORS** (complex scenarios):
- Use FastAPI middleware only (`examples/cors/`)
- Remove CORS section from `template.yaml`
- Deploy: Only need `sam deploy` (no template changes)
- Test: Verify in browser DevTools Network tab

**Debugging CORS Issues**:
1. Check browser DevTools → Network → OPTIONS request
2. Look for duplicate `Access-Control-Allow-Origin` headers
3. Verify preflight response is 200 OK
4. Use `sam logs --tail` to see if OPTIONS hits Lambda

### 2. Project Architecture
```
backend/src/app/
├── __init__.py
├── main.py              # FastAPI app + handler
├── auth/                # JWT middleware & validation
├── dal/                 # Data access layer  
├── models/              # Pydantic models
└── routes/              # API endpoints
```

### 3. Error Handling
- **Internal errors**: Log full details, return generic message (`examples/security/error-handling.py`)
- **Validation errors**: Safe to return Pydantic error details
- **Include correlation IDs**: For support troubleshooting

### 4. Database Best Practices
- **DynamoDB**: Use least-privilege IAM policies per function
- **Queries**: Use KeyConditionExpression (not scans)
- **Encryption**: Enable encryption at rest
- **Connection**: Use boto3 resource, not client for DynamoDB

### 5. Development Workflow
Ask 3 clarifying questions about:
- Edge cases and error scenarios
- Data models and validation rules  
- UX/UI behavior and states
- Infrastructure and deployment needs

Propose implementation plan:
- Files to create/modify
- Functions and their responsibilities
- Dependencies to add
- Test strategy

Generate code with:
- Docstrings and type hints
- Paired tests for every feature
- Separation of concerns (API → Service → DAL)

## Master Checklist

### Before Coding
- [ ] Figma mockups or wireframes ready
- [ ] API endpoints + data shapes defined
- [ ] Repo skeleton matches architecture (API → Service → DAL)
- [ ] Test framework initialized (pytest, vitest, moto for AWS mocks)

### Security
- [ ] All inputs validated with Pydantic models
- [ ] No secrets in code or git history  
- [ ] JWT tokens properly signed and verified
- [ ] Rate limiting on sensitive endpoints
- [ ] Generic error messages for users, detailed logs for developers
- [ ] IAM roles follow least privilege principle
- [ ] Database encryption enabled
- [ ] CORS configured for specific origins (not *)
- [ ] HTTPS enforced (API Gateway handles this)
- [ ] Dependency scanning enabled (npm audit, safety)

### Code Quality
- [ ] Vue: No prop mutation; use ref/reactive; :key on v-for
- [ ] Python: Type hints + Pydantic schemas; routers separated from services/DAL  
- [ ] AWS SAM: CORS in template.yaml; scoped IAM roles
- [ ] Unit tests for core functions
- [ ] API tests with FastAPI TestClient
- [ ] Mock AWS resources (S3/DynamoDB) in tests
- [ ] Frontend: test props/events with Vitest

### Infrastructure
- [ ] No hardcoded secrets—use .env or AWS Secrets Manager
- [ ] Test locally with `sam local` + Vue dev server before deploying
- [ ] Pin dependencies in requirements.txt and package.json
- [ ] Structured logs (JSON key-value)
- [ ] Automatic request logs (method, path, latency, status)
- [ ] Toggleable debug logs via DEBUG_MODE
- [ ] Correlation IDs in logs and responses

### End-of-Day
- [ ] Run lint, type-check, and pytest before commit
- [ ] Tag commit with feature and state (login_v1_working)
- [ ] Summarize lessons in README for next session

## Code Examples
See `/examples/` folder for working implementations:
- `cors/` - CORS configurations for different environments
- `logging/` - Structured logging and middleware  
- `security/` - Input validation, secrets, JWT, rate limiting, error handling
- `timezone/` - UTC storage and frontend conversion utilities

## Common Pitfalls
❌ **Never Do This**:
- Use `allow_origins=["*"]` with `allow_credentials=True`
- Use relative imports in Lambda functions
- Log sensitive data (passwords, tokens, PII)
- Return stack traces to end users
- Skip input validation "just for internal APIs"
- Use naive datetime objects (without timezone)
- Grant overly broad IAM permissions
- Test only in Postman (bypasses browser CORS)

## Key Mantras
- **Ship thin slices, test early**
- **Let LLMs do boilerplate, not architecture**  
- **Pause & review every 2 hours**
- **Ask edge-case questions before coding**
- **Store in UTC, convert for display only**
- **Always use timezone-aware datetimes**