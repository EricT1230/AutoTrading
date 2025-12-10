# Architecture and Performance Optimization Recommendations

This document summarizes pragmatic steps to keep the current FastAPI + React/Vite + trading-bot architecture efficient while avoiding a full framework rewrite. The focus is latency, resource usage, and operational robustness for real-time trading workloads.

## Keep the split architecture
- Preserve FastAPI as the system-of-record for trading logic and account state; keep UI concerns in the web client or a dedicated Next.js/React layer.
- If adopting Next.js for SEO or faster first paint, treat it as a **UI-only replacement** and continue consuming the existing APIs/WebSockets. Avoid re-implementing trading logic in JavaScript runtimes.

## Real-time data delivery
- Replace 2s polling with WebSockets or Server-Sent Events for ticker and candle updates to cut HTTP overhead and reduce chart re-renders.
- Use delta payloads (only changed candles/bars) and client-side buffering to minimize redraw work for charts.
- Apply backpressure: cap max outstanding messages per client and drop/aggregate bursts to protect the browser and server.

## Caching and data shaping
- Introduce a read cache (Redis) for hot paths like latest ticker, last N candles, and account snapshots. Keep cache TTL short (e.g., 1–5s) to avoid staleness while offloading DB/API reads.
- Normalize historical queries: pre-bucket candles on the server and return pre-aggregated series for common intervals to reduce client CPU.

## Workload isolation and resiliency
- Run market data ingestion, order routing, and strategy evaluation in separate workers (processes/containers) and communicate via a message bus/queue (Redis Streams, NATS, or Kafka). This prevents UI/API spikes from impacting trading loops.
- Implement supervised reconnect and replay for the OKX stream so short disconnects do not require manual intervention.

## Observability and guardrails
- Track P50/P95 latency for API routes, WebSocket publish time, and strategy loop duration; alert when thresholds breach.
- Add circuit breakers/timeouts when calling upstream exchanges; wrap retries with jitter to avoid thundering herd.
- Log and expose metrics for dropped/aggregated market data to detect overload conditions early.

## When to introduce Next.js
- Use it if you need SEO or faster initial render for public dashboards. Render initial snapshots server-side, then hydrate live widgets as client components using the existing WebSocket feed.
- Keep expensive or high-frequency components (`use client`) to avoid forcing SSR of rapidly changing data.

## Immediate low-risk wins
1. Switch polling to WebSockets/SSE for live market data and orders.
2. Add Redis caching for latest ticker/candle snapshots with short TTLs.
3. Add latency/error metrics plus alerts for trading loops and API routes.
4. Separate ingestion/trading workers from the API/UI container to isolate CPU/memory spikes.

## Execution and confirmation guide
- **Can be executed autonomously**: code/config changes that stay inside the repo and do not touch real accounts or secrets (e.g., swap polling for WebSockets, add Redis caching layer, add metrics/alerts, split services into dedicated containers, tune charting to use delta payloads/buffering/backpressure).
- **Requires your confirmation**: anything that needs live API keys, modifies trading limits, places orders, rotates secrets, or alters infrastructure outside this repo (cloud resources, DNS, CI/CD credentials). For these, please confirm environments, credentials, and blast radius before execution.

## 30/60/90-day action plan
- **Next 30 days**: Enable WebSocket/SSE delivery for live quotes and orders, add Redis caching for hot reads, and instrument latency/error metrics with alerts in Grafana/Prometheus.
- **Next 60 days**: Split ingestion/trading workers from the API/UI container, add supervised reconnect/replay for OKX streams, and introduce circuit breakers/timeouts around upstream exchange calls.
- **Next 90 days**: Evaluate whether public/SEO-facing surfaces warrant a Next.js UI layer (SSR/ISR for snapshots) while keeping FastAPI as the system-of-record; otherwise double down on charting optimizations (delta payloads, buffering, backpressure) in the existing React client.
