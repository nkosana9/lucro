# Architecture & Design Overview

## Design

The Lucro system is a Django REST API for ingesting financial transactions, categorizing them asynchronously, and providing account summaries via a BI endpoint

**Core Flow:**
1. **Ingestion** → POST to `/api/integrations/transactions/` with accounts + transactions (bulk upsert accounts, bulk create transactions with batch_id)
2. **Async Categorization** → Celery task processes batch, categorizes each transaction, updates status (pending → processing → completed/failed)
3. **Querying** → GET `/api/reports/account/{account_id}/summary/?start_date=...&end_date=...` returns metrics, top categories, processing status

**Auth:** Simple token auth included for all API endpoints

---

## Some Architecture/Design Decisions

### 1. **Database Layer (Django ORM + Models)**
- **Custom Manager** : `account_summary()` method encapsulates all query/aggregation logic
- Custom manager (`TransactionManager`) separates query logic from views/serializers (clean separation of concerns)
- Enum `IngestionStatus` prevents invalid statuses

### 2. **Async Processing (Celery + Redis)**
- `categorise_transactions(batch_id)` task processes only PENDING transactions in a batch
- Should we not be able to categorise a transaction, the ingestion is marked as `FAILED` in the DB to support future error-handling strategies (Re-runs, DQM vallidation, etc)

### 3. Infra
- Added health checks to the docker containers
- Volumes to persist data where appropriate


### 5. **Token Auth**
Token auth was used for authentication. 
- Simple stateless auth (no sessions needed in distributed setup)
- Token can be rotated/revoked at app level
- Works with API clients, mobile apps, CLI tools
- Relatively simple but effective authentication mechanism in this instance

---

## Scalability / Production

- Could switch to JWT auth which works better at scale
- Add pagination on the BI endpoint or limit allowable date ranges to prevent large lookups slowing down the DB
- Kubernetes for orchestration (multiple app/worker pods)
- Managed PostgreSQL instance
- Managed Redis instance.. or completely switch to full pubsub or event based processing (RabbitMQ, PubSub or Kafka)
- Add tracing & instrumentation for collecting appplication metrics
- Monitoring: Prometheus + Grafana for metrics; ELK / Victoria Logs / Sentry for application logging & exceptions (this would also mean switching to structured logging)
