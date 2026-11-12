# Research Protocol — Evidence-Gated Autonomous Code Repair

Status: **registered project design / working engineering demonstration**. Model experiment **not executed**.

Prepared: 2026-11-11.

## Primary research question

On repository-repair or function-level code-fix tasks where several proposed patches pass the original visible test suite, does a second, specification-grounded evidence gate reduce the proportion of accepted patches that fail held-out validation?

## Contribution we seek to evaluate

A selective policy rather than a new code generator:

- **Direct**: choose the first candidate patch passing the visible tests.
- **Evidence-gated**: choose the first patch passing the same visible tests **and** separate checks derived independently from the natural-language issue contract.
- Both methods receive **the identical candidate pool in identical order**, generated under matched prompt, inference and temperature settings. The gate does not access hidden tests. When neither candidate qualifies, it abstains instead of claiming success.

The novelty claim must be restricted. Fault localization, iterative feedback and patch filtering are well studied (Han et al., 2026; Yuan et al., 2026). Our proposed experimental focus is the **reliability–coverage tradeoff under test insufficiency** and evidence-based abstention. A literature audit is required before any stronger novelty statement.

## Testable hypotheses

- H1: The evidence gate reduces false acceptance: `accepted AND heldout_fail`, divided by `accepted`.
- H2: The evidence gate can increase precision among accepted patches but may decrease acceptance coverage.
- H3: Benefits depend on the **quality and cost** of independent probes (sensitivity analysis).

## Dataset and splits

Current: 16 small **hand-authored, synthetic** Python function repair tasks, each containing a bug, two handcrafted candidate patches, visible tests, probe tests, and a separate hidden split. The incorrect candidate is intentionally tailored to pass visible tests while failing probes. This is an engineering fixture designed to exercise selection logic, **not** unbiased statistical evidence.

Model evaluation: generate two independent candidates per task using an actual model; use the same candidates for direct and gated selection; evaluate both once against hidden tests. Under this design the number of model calls is exactly matched and any difference arises from selection policy, not the generation budget. However, the gated method does use extra test execution; disclose this separately.

For publishable evidence: enlarge to independently sampled real issues with reference fixes, add leakage controls, ensure probe creation is blinded to the true fixes and hidden tests, and compare across >1 model, >1 seed, and multiple probe budgets. Suggested external benchmarks: SWE-bench Verified or other human-reviewed tasks, with a subset whose tests run within the computing budget. Avoid claiming external validity from the 16 toy functions.

## Metrics

1. **Held-out resolution rate**: proportion of all tasks where selected patch passes hidden validation; abstentions count as failure.
2. **Coverage**: proportion of tasks for which a patch is accepted.
3. **False-acceptance rate**: fraction of accepted patches that fail hidden validation (with denominator shown).
4. **Conditional precision**: fraction of accepted patches that pass hidden validation.
5. **Resource costs**: model calls, tokens, CPU time, test-execution time, and timeouts.
6. **Patch disruption**: files changed and edit size (future repository-scale extension).

All results should be shown with per-task records. Use paired McNemar testing for binary held-out success when sample size is sufficient, and paired bootstrap intervals for differences; avoid overinterpreting tiny samples. Display raw counts alongside percentages. If no cases are accepted, conditional precision is undefined rather than zero.

## Ablations and validity checks

- Direct vs evidence-gated on exact same generated patch candidates.
- 0/1/2/3+ independent probes of increasing quality / cost.
- Random or weakly relevant probes compared with carefully specified probes.
- Contrast model-generated probes, manually audited probes, and mutation-guided probes.
- Include under-specified or conflicting requirements where gate must abstain.
- Examine false negatives: valid solutions rejected by incorrect or overly strict probes.
- Isolate held-out test suites from generation and gating. Never tune prompts using held-out labels.

## Scientific approval checkpoints

A. Researcher approves issue selection, random seeds, probe-development procedure, and evaluation metrics **before** real runs.

B. Researcher reviews model-generated cases and any probe specification changes **before** reported results are interpreted.

C. Researcher verifies raw execution logs and endorses statistical conclusions **before** submitting.

## Current limitations

The initial benchmark is intentionally constructed such that every task has an incorrect patch passing visible tests but failing extra probes and hidden tests. Therefore the large relative performance difference seen with the hand-authored candidates is **guaranteed by design**. It demonstrates an obvious mechanism but does not measure its empirical effect on AI-generated patches. Model availability, domain realism, generalization, fairness of probe budgets, and novelty remain untested.

## Existing relevant research (verified URLs)

- Han, K., et al. (2026). *TDFlow: Agentic Workflows for Test Driven Development.* EACL 2026. https://aclanthology.org/2026.eacl-long.70/
- Yuan, L., et al. (2026). *CGARF: a causality-guided framework for reliable automated program repair.* Empirical Software Engineering. https://doi.org/10.1007/s10664-026-10940-1
- Chowdhury, N., et al. (2024/2025 update). *Introducing SWE-bench Verified.* https://openai.com/index/introducing-swe-bench-verified/
- Luo, W., et al. (2026). *Refine After Generation: Toward Correct and Concise Patches in LLM-based Program Repair.* https://arxiv.org/abs/2608.13292
- *On Coding Agent Issue Localization Accuracy — An Exploratory Study.* ESEM 2026. https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.59

## Submission control

Kaggle Paper Track: https://www.kaggle.com/competitions/gemma-4-developer-agent-paper

Close: 2026-11-12 23:59 UTC. Word limit 3,000. The final writeup must be submitted, not merely saved. Submit only findings that have actually been measured; explicitly report limitations.
