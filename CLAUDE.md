# CLAUDE.md — OmniView
> EGOS Kernel rules apply. See `~/.claude/CLAUDE.md` for full rules.
> Critical: no force-push main · no secret logging · no git add -A in agents

**Project:** OmniView — Local-first forensic video analysis
**Type:** Standalone tool (NOT part of EGOS kernel)
**Stack:** Python 3.12 + FastAPI + OpenCV (engine/) + React 18 + TypeScript + Tailwind v4 (ui/)
**Classification:** ACTIVE-DEV (see `~/egos/docs/REPO_MAP.md`)

---

## Princípios Hard-Coded (não negociar)

1. **Original imutável** após ingest (`chmod 444`)
2. **Sem cloud** por padrão — funciona offline
3. **Motion-first gating** — MOG2 dual-threshold; detector pesado só Phase 4
4. **Chain-of-custody** em todo output (SHA-256 + provenance JSON + HMAC audit)
5. **Funciona sem LLM** no MVP

## Módulos JÁ EXISTENTES — NÃO recriar

```
engine/app/core/
  integrity.py, ingest.py, pii_gate.py, motion.py, event_grouping.py
  thumbnails.py, clips.py, video_probe.py, auth.py, errors.py, config.py

engine/app/services/
  audit_service.py     — HMAC append-only log (alinhado com @egos/audit schema)
  provenance_service.py — JSON chain-of-custody

engine/app/workers/scan_worker.py
engine/app/api/ — 19 rotas (routes_videos, routes_events, routes_auth, routes_health)
engine/app/cli/main.py  — omniview-cli ingest/process/list/verify
engine/app/db/models.py — 9 tabelas + Alembic migrations
```

## EGOS Packages usados

- **guard-brasil-python** — PII scan em filenames/metadata (LGPD). Graceful degradation se API offline.
  Instalado: `.venv` via cópia de `~/egos/packages/guard-brasil-python/guard_brasil/`
- **@egos/audit schema** — `audit_service.py` alinha campos `result` + `reasoning` para cross-repo

## Patterns candidatos a extração (pós Phase 2)

- `provenance_service.py` → `@egos/provenance` package (Intelink também precisa)
- WebSocket scan progress → padrão reutilizável
- Hotkey reviewer → reutilizável em Gem Hunter

## Como rodar

```bash
cd engine && .venv/bin/uvicorn app.main:app --reload
cd engine && .venv/bin/python -m pytest tests/ -q
cd ui && npm run dev   # proxy /api → :8000 automático
```

## Estado das fases

- **Phase 0+1:** ✅ Completa — 26 testes, 81 arquivos
- **Phase 2:** Em andamento — ui/src/{types,i18n,lib/api.ts} prontos
- **Phase 3:** Backlog — export ZIP assinado
- **Phase 4+:** Backlog — YOLO11n, benchmark, LLM on-demand

NÃO misturar com sprint Delegacia/Lídia — projetos independentes.
