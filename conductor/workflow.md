# Workflow: Goblin Development

## Standard Methodology
Development follows a **Research -> Strategy -> Execution** lifecycle.

### 1. Research & Analysis
- Deep-dive into target sources or vulnerability patterns.
- Map existing codebase dependencies for the change.
- Perform empirical reproduction for bug fixes.

### 2. Strategy & Design
- Formulate a clear implementation plan.
- Identify impact on existing modules (e.g., `scrape.py`, `database.py`).
- Define the testing strategy.

### 3. Execution (Iterative Plan-Act-Validate)
- **Plan:** Define the atomic sub-task and its specific implementation approach.
- **Act:** Surgical implementation of the change.
- **Validate:** Verify through unit tests and manual checks.

## Phase Completion Verification
At the end of each **Phase** in a Track Plan, a **User Manual Verification** must occur:
- `- [ ] Task: Conductor - User Manual Verification '<Phase Name>' (Protocol in workflow.md)`
- This ensures the developer (AI) pauses for manual confirmation or specific visual checks if required.

## Git Protocol
- Create feature branches for all new tracks.
- Atomic commits with clear messages: `feat(module): description` or `fix(module): description`.
- **NEVER** push without explicit permission.
