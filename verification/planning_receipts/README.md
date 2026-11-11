# Planning verification receipts

These receipts document actual checks of the verification inventory and initial release state. They are **planning evidence**, not evidence of an implemented or tested application.

- [Inventory lint receipt](2026-11-07-planning-verification-001-plan.json): command completed with exit 0; 80 requirements, 330 acceptance cases, complete 120-case baseline strategy matrix and no detected inventory/link/schema errors.
- [Initial release audit receipt](2026-11-07-planning-verification-001-release.json): command completed with exit 1; NOT READY, zero verified product cases and 330 unverified mandatory cases. Missing code/rulebook/test mappings and release subject are reported explicitly.

Command stdout/stderr artifacts, exact source/specification hashes and environment details are linked in each receipt. The receipt schema was checked with JSON Schema Draft 2020-12 validation. No credentials were read to produce this evidence.
