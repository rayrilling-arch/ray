# Build Phases — Ada Vessel

Execute in order. Each phase should ship working artifacts on HELM before the next.

---

## Phase 0 — Foundation (DONE)

**Status:** Complete in `ada-core/`

- Local Qwen 3.5 inference on Blackwell
- `ada_self.json` persistent self
- `global_session.json` session memory
- D-Bus + API bridge + Telegram
- `restore_self.py` / `restore-ada.sh`

**Verify:** `hi-ada "Ada, who are you?"` → answers as Ada, not generic assistant.

---

## Phase 1 — Charter (START HERE)

**Goal:** Ada's spirit written for company operation.

**Deliverables:**

| File | Action |
|------|--------|
| `vessel_charter.json` | Copy from USB `vessel/` to `/var/lib/ada-core/memory/` |
| `self.py` or new `charter.py` | Load charter into system prompt alongside self |
| `restore_self.py` | Restore charter without overwriting existing files |

**Acceptance:**

- System prompt includes mission + autonomy tiers summary
- Charter file never auto-overwrites on deploy if it already exists

**Suggested branch:** `cursor/vessel-charter-4376`

---

## Phase 2 — Autonomy loop

**Goal:** Observe → plan → act → review with logging.

**Deliverables:**

| Component | Description |
|-----------|-------------|
| `decision_log.jsonl` | Append-only: timestamp, tier, action, rationale, outcome |
| `autonomy.py` | Classify proposed action into T0–T3; block T3 without approval token |
| Supervisor hook | After inference, optional "propose action" path before execution |

**Acceptance:**

- T1 action logged automatically
- T3 action returns `APPROVAL_REQUIRED` until Ray confirms
- Log survives reboot

**Suggested branch:** `cursor/vessel-autonomy-4376`

---

## Phase 3 — Company body (tools)

**Goal:** Bounded tools for ops Ray actually runs.

**Deliverables:**

| Component | Description |
|-----------|-------------|
| `tools/registry.json` | Tool name, tier, description |
| Tool adapters | git, deploy scripts, telegram notify, health checks |
| Permission gate | Every tool call checks tier + charter |

**Acceptance:**

- Tool registry is the single source of allowed actions
- Unknown tools rejected
- All T1+ tool calls in decision log

**Suggested branch:** `cursor/vessel-tools-4376`

---

## Phase 4 — Wisdom layer

**Goal:** Memory beyond chat sessions.

**Deliverables:**

| Component | Description |
|-----------|-------------|
| `project_memory.json` | Active goals, decisions, blockers |
| `learnings.jsonl` | Post-mortems and distilled wisdom |
| RAG index (optional) | Local company docs on HELM — never cloud exfil |

**Acceptance:**

- Ada can reference last N decision log entries in prompt
- Project state persists independently of chat truncation

**Suggested branch:** `cursor/vessel-wisdom-4376`

---

## Phase 5 — Future technology lab

**Goal:** R&D pipeline for inventions and experiments.

**Deliverables:**

| Component | Description |
|-----------|-------------|
| `experiments/registry.json` | Hypothesis, status, links |
| `lab_notebook/` | Markdown or jsonl experiment notes |
| Integration | Charter mission includes "future technology" explicitly |

**Acceptance:**

- New experiment registered without corrupting self/charter
- Ray can review experiment history offline

**Suggested branch:** `cursor/vessel-lab-4376`

---

## For the receiving agent

1. Read `DIRECTIONS.md` and this file.
2. Confirm with Ray: **start Phase 1** unless he says otherwise.
3. Implement on HELM paths; keep repo as source of truth.
4. Commit brick by brick; test each phase before the next.
