# Changelog

## [0.2.0](https://github.com/Lakshyalamba/toolforge/compare/v0.1.0...v0.2.0) (2026-09-07)


### Features

* **agent:** implement DSPyToolAdapter with safety gate, observable trace, and server exports ([d05ded8](https://github.com/Lakshyalamba/toolforge/commit/d05ded88a0a6879105710af4fcc14efa46d8efeb))
* **agent:** implement ToolForgeAgent ReAct execution layer with safety validation tests ([c982dd5](https://github.com/Lakshyalamba/toolforge/commit/c982dd58b3b493016be94e438368f986d2244d5a))
* **benchmark:** implement side-by-side empirical benchmark runner and tests ([084094d](https://github.com/Lakshyalamba/toolforge/commit/084094dba932d9dafc64a6a9fad728d86d931b32))
* **cli:** add map, evaluate, optimize, and benchmark CLI commands with tests ([6f90459](https://github.com/Lakshyalamba/toolforge/commit/6f904599f0e833a03df140b254f21aab871e24ad))
* **config:** add DSPyConfig and DSPyOptimizationConfig with strict validation ([87548aa](https://github.com/Lakshyalamba/toolforge/commit/87548aacc8af3b6a39424516b9ef4824ca786ce2))
* **dataset:** implement dataset format and loading utilities for mapping examples ([19fd5cf](https://github.com/Lakshyalamba/toolforge/commit/19fd5cfc080802ca76d0b0fc08f8a15903422794))
* **evaluation:** implement semantic mapping evaluation metric and evaluator pipeline ([27731d6](https://github.com/Lakshyalamba/toolforge/commit/27731d68eff477e2efdaaffb0356f42852734056))
* **intelligence:** define semantic data models, ToolRiskLevel enum, and intelligence errors ([fadcd8d](https://github.com/Lakshyalamba/toolforge/commit/fadcd8d19a88929197104e6faa4a3926a6c4050e))
* **intelligence:** implement DSPy signatures for tool enrichment and ambiguity resolution ([b09f4e8](https://github.com/Lakshyalamba/toolforge/commit/b09f4e846bb59e5fffcb623c815a602967eeed25))
* **intelligence:** implement ToolEnricherModule and ToolDisambiguatorModule ([365a62f](https://github.com/Lakshyalamba/toolforge/commit/365a62f1b6b95ec2e4dd58582abde85350485c4a))
* **mapper:** implement DSPyToolMapper with in-memory caching and concurrent mapping ([8b79cf5](https://github.com/Lakshyalamba/toolforge/commit/8b79cf5b71fa899d4ecdd6f0999ce8abc24326b4))
* **mapper:** implement zero-overhead StaticToolMapper with heuristic ambiguity fallback ([447793c](https://github.com/Lakshyalamba/toolforge/commit/447793cbeb7f98731b9d8e8a80d4a16d6f429cd8))
* **optimizer:** implement DSPy teleprompter optimization workflow and tests ([7f2f135](https://github.com/Lakshyalamba/toolforge/commit/7f2f13543d00b150f2341e8a34956de0e1b3cbba))
* **project:** support dspy configuration discovery in pyproject.toml and reject secrets ([ffce650](https://github.com/Lakshyalamba/toolforge/commit/ffce65038e471a438908c9cfcc329c09039e4b34))


### Documentation

* add environment activation tip to getting-started guide ([#3](https://github.com/Lakshyalamba/toolforge/issues/3)) ([28c5d02](https://github.com/Lakshyalamba/toolforge/commit/28c5d02397fa8bee1dac6947ff8c4e7546779ca8))
* update documentation for DSPy intelligence, configuration, benchmarking, and contributing ([68fa324](https://github.com/Lakshyalamba/toolforge/commit/68fa32497526177bf6707e23ef795e5125e049a4))
