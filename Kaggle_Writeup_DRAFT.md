# Evidence-Gated Code Repair: Evaluating Autonomous Patch Selection Under Incomplete Tests

**Subtitle:** A reproducible experimental protocol for distinguishing test-passing patches from independently verified repairs

> **DRAFT — NOT SUBMISSION READY.** The model-driven experiment has not yet been run. Square-bracket placeholders must be replaced with genuine measured observations, or explicitly omitted. The engineering demonstration is not evidence of a model-level improvement.

## Abstract

Autonomous coding agents increasingly use execution feedback to generate and validate software patches. However, passing a visible test suite does not guarantee that a patch solves the underlying issue. We propose to study a selection-stage intervention, **evidence-gated repair**, which requires candidate patches to pass both visible tests and independent specification-grounded verification checks. Our central question is whether stronger acceptance criteria reduce false acceptance when visible tests are insufficient, and at what cost in coverage and execution time. We implement a reproducible Python evaluation harness that controls candidate generation across methods, separates verification probes from held-out evaluation tests, and records per-task decisions. A 16-case hand-authored demonstration confirms the mechanics of the gate but is not evidence about any language model. **[Insert results from an actual paired LLM experiment before submitting.]**

## 1. Introduction

Software-engineering agents use language models to inspect code, generate patches, and iterate using test outcomes. Conventional issue-resolution metrics measure whether the final patch passes evaluation tests. Yet when a candidate passes only a partial visible suite, the agent can incorrectly infer that it has achieved a valid repair. Existing benchmarks such as SWE-bench Verified underscore the need to distinguish tests that a model can see from held-out validation tests (Chowdhury et al., 2024).

Our project investigates a narrow decision problem: **given identical candidate patches, does adding independent specification-derived checks change the reliability of patch selection?** This reframes validation as a selective prediction problem, where an agent may reject an apparently successful patch or abstain when evidence is insufficient. We explicitly avoid claiming that testing, fault localization, or patch filtering are new.

## 2. Related Work

TDFlow describes a structured multi-agent workflow that iterates between patch proposals, debugging, revisions, and tests, showing the importance of test-oriented software repair (Han et al., 2026). CGARF investigates causal reasoning, patch stability, and two-stage patch filtering for automated repair (Yuan et al., 2026). Research on patch conciseness also highlights that passing tests is not the only attribute of a desirable repair (Luo et al., 2026). These systems motivate our emphasis on independently justified verification and careful measurement of false acceptance. Unlike evaluations that change prompts, tools and generation budgets simultaneously, our planned paired experiment isolates the acceptance policy on a *shared candidate pool*.

## 3. Method

For each task, the system receives an issue description, buggy Python source code, and a set of visible input-output tests. A model generates two candidate source-code patches. To compare methods fairly, **both acceptance policies receive the exact same candidate pair**.

**Direct policy:** choose the first candidate that passes the visible tests. Reject all candidates if none pass.

**Evidence-gated policy:** choose the first candidate that passes both the visible tests and an independently constructed probe suite. Reject all candidates if none pass.

The probes represent explicit boundary conditions or invariants inferred from the issue specification and are not presented during candidate generation. Hidden tests are held out from both candidate generation and selection. A strict execution environment with timeouts and an audit log is used. The candidate generator is a replaceable OpenAI-compatible model endpoint, enabling experiments on different models without changing validation logic.

## 4. Initial Implementation Check (NOT a Model Evaluation)

To verify the harness, we authored 16 simple Python bug-fix exercises. Each includes a buggy implementation, a deliberately overfitted patch that passes visible tests but fails independent checks, and a correct patch. We also created separate held-out tests that are never used for selection.

The deterministic demo produced the following raw observations:

| Condition | Tasks | Accepted | Passed held-out tests |
|---|---:|---:|---:|
| Visible tests only | 16 | 16 | 5 |
| Visible + probe gate | 16 | 16 | 16 |

**Interpretation:** these figures confirm that the implementation identifies the hand-authored shortcuts. The outcomes are largely guaranteed by dataset construction and candidate ordering. They are **not evidence that an AI coding agent is improved** and must not be presented as competitive performance results. The real experiment is still pending.

## 5. Planned Model Evaluation — RESULTS PENDING

Model: **[actual model and version]**. Endpoint and inference environment: **[details]**. Tasks: **[number and sampling method]**. Candidate pool: 2 independently prompted generations per issue. Generation temperature: 0.2. Evaluation: public tests determine eligibility; probes are accessible only to the evidence-gated acceptance policy; held-out tests determine final resolution success.

Report for each method: coverage, held-out resolution, false acceptance among accepted patches, selection mistakes, inference tokens, and test runtime. Use paired per-task comparisons and uncertainty intervals. Test sensitivity to probe quality and count. Make raw experimental logs available and audit for prompt/test leakage.

**[Insert actual experiment table, uncertainty, failure examples, and discussion only after executing the model. No placeholders should remain in a final Kaggle submission.]**

## 6. Discussion and Limitations

The engineering prototype demonstrates how a patch-selection layer can be audited separately from generation. Whether such a layer improves real-world repair depends on the quality of candidate patches, adequacy of visible tests, errors in probe design, computational budget, and the complexity of repository-scale issues. Independent probes can themselves be incorrect and may reject a valid repair. The current fixture set consists only of small hand-authored functions, with deliberate overfitting and no model-generated patches; it has no demonstrated external validity. Broader claims require evaluation on genuine software issues and multiple models or settings.

## 7. Conclusion

We provide an auditable architecture and experimental protocol for studying evidence-gated code repair under incomplete tests. The next scientific step is to measure its reliability–coverage tradeoff on actual language-model candidates and real-world software issues. Claims about improvements, generalization, or state of the art must await that evidence.

## References

1. Chowdhury, N. et al. (2024, updated 2025). *Introducing SWE-bench Verified.* https://openai.com/index/introducing-swe-bench-verified/
2. Han, K., Maddikayala, S., Knappe, T., Patel, O., Liao, A., and Barati Farimani, A. (2026). *TDFlow: Agentic Workflows for Test Driven Development.* Proceedings of EACL 2026. https://aclanthology.org/2026.eacl-long.70/
3. Yuan, L. et al. (2026). *CGARF: a causality-guided framework for reliable automated program repair.* *Empirical Software Engineering.* https://doi.org/10.1007/s10664-026-10940-1
4. Luo, W. et al. (2026). *Refine After Generation: Toward Correct and Concise Patches in LLM-based Program Repair.* https://arxiv.org/abs/2608.13292
5. Google DeepMind (2026). *Gemma 4 Developer Agent Paper Track: Rules and Evaluation.* https://www.kaggle.com/competitions/gemma-4-developer-agent-paper
