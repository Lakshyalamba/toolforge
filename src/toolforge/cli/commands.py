import json
import os
import sys
from pathlib import Path
from typing import Any

from toolforge.errors import ConfigurationError
from toolforge.project import Project, load_server_from_file, load_server_from_project


def resolve_server_instance(file_path: str | None) -> tuple[Any, Project | None]:
    """Resolve the MCPServer instance and the discovered Project config context."""
    if file_path is not None:
        server = load_server_from_file(Path(file_path))
        try:
            project = Project.discover()
        except Exception:
            project = None
        return server, project

    try:
        project = Project.discover()
        server = load_server_from_project(project)
        return server, project
    except ConfigurationError as e:
        # If configuration error was raised (like invalid entrypoint or transport), bubble it up
        raise e
    except Exception:
        # Fallback to default "server.py" in current working directory
        default_path = Path.cwd() / "server.py"
        server = load_server_from_file(default_path)
        return server, None


def init_command(directory: str, force: bool = False) -> None:
    """Initialize a new ToolForge project directory with a working MCPServer template."""
    target_dir = os.path.abspath(directory)
    project_name = os.path.basename(target_dir.rstrip(os.sep)) or "my-server"

    if os.path.exists(target_dir) and os.listdir(target_dir):
        conflicts = [
            f
            for f in ["server.py", "pyproject.toml", "README.md", ".gitignore"]
            if os.path.exists(os.path.join(target_dir, f))
        ]
        if conflicts and not force:
            print(
                f"Error: Destination contains conflicts (e.g. '{conflicts[0]}' already exists). "
                "Use --force to overwrite.",
                file=sys.stderr,
            )
            sys.exit(1)

    os.makedirs(target_dir, exist_ok=True)

    server_content = f"""from toolforge import MCPServer

server = MCPServer("{project_name}")

@server.tool
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

if __name__ == "__main__":
    server.run()
"""

    pyproject_content = f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{project_name}"
version = "0.1.0"
dependencies = [
    "toolforge",
]

[tool.toolforge]
name = "{project_name}"
entrypoint = "server.py"
transport = "stdio"
"""

    readme_content = f"""# {project_name}

A ToolForge MCP tool server.

## Running

```bash
python server.py
```
"""

    gitignore_content = """__pycache__/
.venv/
*.pyc
"""

    with open(os.path.join(target_dir, "server.py"), "w") as f:
        f.write(server_content)
    with open(os.path.join(target_dir, "pyproject.toml"), "w") as f:
        f.write(pyproject_content)
    with open(os.path.join(target_dir, "README.md"), "w") as f:
        f.write(readme_content)
    with open(os.path.join(target_dir, ".gitignore"), "w") as f:
        f.write(gitignore_content)

    print(f"Initialized ToolForge project in '{target_dir}'", file=sys.stderr)


def run_command(file_path: str | None) -> None:
    """Execute the discovered MCPServer instance loop."""
    try:
        server, _ = resolve_server_instance(file_path)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    server.run()


def list_command(file_path: str | None) -> None:
    """Print all registered tools, resources, and prompts in the project.

    Does so without booting the server.
    """
    try:
        server, _ = resolve_server_instance(file_path)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"ToolForge Server: {server.name}")
    print()
    print("Tools")
    print("─────────────────────────")
    for tool in server.tools:
        desc = tool.description or ""
        first_line = desc.split("\n")[0] if desc else ""
        print(f"{tool.name:<9} {first_line}")

    resources = server.list_resources()
    if resources:
        print()
        print("Resources")
        print("─────────────────────────")
        for res in resources:
            desc = res.description or ""
            first_line = desc.split("\n")[0] if desc else ""
            print(f"{res.uri:<15} {first_line}")

    prompts = server.list_prompts()
    if prompts:
        print()
        print("Prompts")
        print("─────────────────────────")
        for pr in prompts:
            desc = pr.description or ""
            first_line = desc.split("\n")[0] if desc else ""
            print(f"{pr.name:<15} {first_line}")


def inspect_command(file_path: str | None, tool_name: str | None = None) -> None:
    """Inspect the server configuration, specific tool, resource, or prompt detail."""
    try:
        server, project = resolve_server_instance(file_path)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if tool_name is None:
        print("ToolForge Project")
        print("─────────────────────────")
        if project is not None:
            print(f"Name: {project.config.name}")
            print(f"Root: {project.root}")
            print(f"Entrypoint: {project.config.entrypoint}")
            print(f"Transport: {project.config.transport}")
        else:
            print(f"Name: {server.name}")
            print(f"Root: {Path.cwd()}")
            print(f"Entrypoint: {Path(file_path or 'server.py').name}")
            print("Transport: stdio")
        print()
        print("Tools")
        print("─────────────────────────")
        for tool in server.tools:
            print(tool.name)

        resources = server.list_resources()
        if resources:
            print()
            print("Resources")
            print("─────────────────────────")
            for res in resources:
                print(res.uri)

        prompts = server.list_prompts()
        if prompts:
            print()
            print("Prompts")
            print("─────────────────────────")
            for pr in prompts:
                print(pr.name)
    else:
        # 1. Try to find a matching tool
        target_tool = None
        for tool in server.tools:
            if tool.name == tool_name:
                target_tool = tool
                break

        if target_tool is not None:
            print(f"Tool: {target_tool.name}")
            print()
            print("Description:")
            print(target_tool.description or "")
            print()
            print("Parameters:")
            print()
            for p_name, p in target_tool.parameters.items():
                required_str = "yes" if p.required else "no"
                type_name = getattr(p.annotation, "__name__", str(p.annotation))
                print(f"{p_name}")
                print(f"  type: {type_name}")
                print(f"  required: {required_str}")
                print()
            print("Input Schema:")
            print(json.dumps(target_tool.input_schema, indent=4))
            return

        # 2. Try to find a matching resource
        target_resource = None
        for res in server.list_resources():
            if res.uri == tool_name:
                target_resource = res
                break

        if target_resource is not None:
            print(f"Resource: {target_resource.uri}")
            print()
            print(f"  Name: {target_resource.name}")
            print(f"  MIME: {target_resource.mime_type or 'unspecified'}")
            print(f"  Description: {target_resource.description or ''}")
            return

        # 3. Try to find a matching prompt
        target_prompt = None
        for pr in server.list_prompts():
            if pr.name == tool_name:
                target_prompt = pr
                break

        if target_prompt is not None:
            print(f"Prompt: {target_prompt.name}")
            print()
            print("Description:")
            print(target_prompt.description or "")
            print()
            print("Arguments:")
            for p_name, p in target_prompt.parameters.items():
                required_str = "yes" if p.required else "no"
                type_name = getattr(p.annotation, "__name__", str(p.annotation))
                if type_name == "str":
                    type_name = "string"
                print(f"  {p_name}")
                print(f"    type: {type_name}")
                print(f"    required: {required_str}")
                print()
            return

        print(
            f"Error: tool, resource, or prompt '{tool_name}' is not registered.",
            file=sys.stderr,
        )
        sys.exit(1)


def map_command(file_path: str | None, tool_name: str | None = None, as_json: bool = False) -> None:
    """Run semantic mapping on registered tools and print enriched metadata."""
    try:
        server, project = resolve_server_instance(file_path)
    except ConfigurationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    tools = server.tools
    if tool_name is not None:
        tools = [t for t in tools if t.name == tool_name]
        if not tools:
            print(f"Error: tool '{tool_name}' is not registered.", file=sys.stderr)
            sys.exit(1)

    # Initialize mapper
    mapper: Any = None
    if (
        project is not None
        and project.config is not None
        and project.config.dspy is not None
        and project.config.dspy.enabled
    ):
        from toolforge.intelligence import DSPyToolMapper, is_dspy_available

        if is_dspy_available():
            project.config.dspy.configure_lm()
            mapper = DSPyToolMapper.from_config(project.config.dspy)

    if mapper is None:
        from toolforge.intelligence import StaticToolMapper

        mapper = StaticToolMapper()

    results = mapper.map_tools(tools)

    if as_json:
        data = []
        for r in results:
            item: dict[str, Any] = {
                "name": r.name,
                "mapping_source": r.mapping_source,
                "confidence": r.confidence,
                "is_enriched": r.is_enriched,
                "original_description": r.original_description,
                "effective_description": r.effective_description,
            }
            if r.semantics:
                item["semantics"] = {
                    "domain": r.semantics.domain,
                    "category": r.semantics.category,
                    "risk_level": r.semantics.risk_level.value,
                    "primary_intent": r.semantics.primary_intent,
                    "negative_examples": r.semantics.negative_examples,
                }
            data.append(item)
        print(json.dumps(data, indent=2))
        return

    print(f"ToolForge Semantic Mapping ({mapper.__class__.__name__})")
    print("─────────────────────────────────────────────────────────────────")
    for r in results:
        risk_str = r.semantics.risk_level.value if r.semantics else "unknown"
        dom_str = r.semantics.domain if r.semantics else "general"
        cat_str = r.semantics.category if r.semantics else "utility"
        print(f"Tool: {r.name}")
        print(f"  Source: {r.mapping_source} (confidence: {r.confidence:.2f})")
        print(f"  Domain: {dom_str} | Category: {cat_str} | Risk: {risk_str}")
        print(f"  Effective Description: {r.effective_description}")
        if r.semantics and r.semantics.negative_examples:
            print(f"  Avoid when: {', '.join(r.semantics.negative_examples)}")
        print()


def evaluate_command(
    dataset_path: str,
    file_path: str | None = None,
    threshold: float = 0.7,
    as_json: bool = False,
) -> None:
    """Evaluate semantic tool mapping performance against a benchmark dataset."""
    from toolforge.intelligence import (
        DSPyToolMapper,
        MappingDataset,
        MappingEvaluator,
        StaticToolMapper,
        is_dspy_available,
    )

    try:
        dataset = MappingDataset.from_file(dataset_path)
    except Exception as e:
        print(f"Error loading dataset '{dataset_path}': {e}", file=sys.stderr)
        sys.exit(1)

    try:
        _, project = resolve_server_instance(file_path)
    except Exception:
        project = None

    mapper: Any = None
    if (
        project is not None
        and project.config is not None
        and project.config.dspy is not None
        and project.config.dspy.enabled
    ):
        if not is_dspy_available():
            print(
                "Error: DSPy is enabled in project configuration, but 'dspy' is not installed.\n"
                "Install via 'pip install \"mcptoolforge[dspy]\"'.",
                file=sys.stderr,
            )
            sys.exit(1)
        project.config.dspy.configure_lm()
        mapper = DSPyToolMapper.from_config(project.config.dspy)
    elif is_dspy_available():
        import dspy

        if dspy.settings.lm is not None:
            mapper = DSPyToolMapper()

    if mapper is None:
        mapper = StaticToolMapper()

    evaluator = MappingEvaluator(threshold=threshold)
    result = evaluator.evaluate(mapper, dataset)

    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
        return

    print("ToolForge Semantic Mapping Evaluation")
    print("─────────────────────────────────────────────────────────────────")
    print(f"Mapper: {mapper.__class__.__name__}")
    print(f"Dataset: {dataset_path} ({result.total} examples)")
    print(f"Threshold: {threshold:.2f}")
    print(f"Passed: {result.passed}/{result.total} ({result.pass_rate:.1f}%)")
    print(f"Mean Score: {result.mean_score:.3f}")
    print(f"Domain Accuracy:   {result.domain_accuracy * 100:.1f}%")
    print(f"Category Accuracy: {result.category_accuracy * 100:.1f}%")
    print(f"Risk Accuracy:     {result.risk_accuracy * 100:.1f}%")
    print()

    failures = [d for d in result.details if not d.passed]
    if failures:
        print("Mismatched / Sub-threshold Cases:")
        for f in failures:
            print(f"  • {f.tool_name} (Score: {f.score:.2f})")
            if f.expected_domain and f.expected_domain != f.predicted_domain:
                print(f"      Domain: expected '{f.expected_domain}', got '{f.predicted_domain}'")
            if f.expected_category and f.expected_category != f.predicted_category:
                print(
                    f"      Category: expected '{f.expected_category}', "
                    f"got '{f.predicted_category}'"
                )
            if f.expected_risk and f.expected_risk != f.predicted_risk:
                print(f"      Risk: expected '{f.expected_risk}', got '{f.predicted_risk}'")
        print()


def optimize_command(
    dataset_path: str,
    output_path: str | None = None,
    valset_path: str | None = None,
    file_path: str | None = None,
) -> None:
    """Compile and optimize semantic tool mapping using DSPy teleprompters."""
    from toolforge.intelligence import (
        DSPyToolMapper,
        MapperOptimizer,
        MappingDataset,
        MappingEvaluator,
        is_dspy_available,
        save_optimized_program,
    )

    if not is_dspy_available():
        print(
            "Error: Optimizing semantic tool mapping requires DSPy.\n"
            "Install via 'pip install \"mcptoolforge[dspy]\"'.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        trainset = MappingDataset.from_file(dataset_path)
    except Exception as e:
        print(f"Error loading training dataset '{dataset_path}': {e}", file=sys.stderr)
        sys.exit(1)

    valset = None
    if valset_path:
        try:
            valset = MappingDataset.from_file(valset_path)
        except Exception as e:
            print(f"Error loading validation dataset '{valset_path}': {e}", file=sys.stderr)
            sys.exit(1)

    try:
        _, project = resolve_server_instance(file_path)
    except Exception:
        project = None

    if project is not None and getattr(project.config, "dspy", None):
        project.config.dspy.configure_lm()
        mapper = DSPyToolMapper.from_config(project.config.dspy)
        max_bootstrapped = project.config.dspy.optimization.max_bootstrapped_demos
        max_labeled = project.config.dspy.optimization.max_labeled_demos
    else:
        mapper = DSPyToolMapper()
        max_bootstrapped = 2
        max_labeled = 2

    import dspy

    if dspy.settings.lm is None:
        print(
            "Error: No Language Model is configured for DSPy optimization.\n"
            "Configure 'dspy.model' in pyproject.toml (e.g. model = 'openai/gpt-4o-mini').",
            file=sys.stderr,
        )
        sys.exit(1)

    print("ToolForge Semantic Mapping Optimizer")
    print("─────────────────────────────────────────────────────────────────")
    print(f"Training dataset:   {dataset_path} ({len(trainset)} examples)")
    if valset:
        print(f"Validation dataset: {valset_path} ({len(valset)} examples)")
    print(f"Output artifact:    {output_path}")
    print()

    evaluator = MappingEvaluator()
    eval_target = valset if valset else trainset
    score_before = evaluator.evaluate(mapper, eval_target).mean_score
    print(f"Baseline mean score: {score_before:.3f}")
    print("Optimizing with DSPy BootstrapFewShot teleprompter...")

    try:
        optimizer = MapperOptimizer(
            max_bootstrapped_demos=max_bootstrapped,
            max_labeled_demos=max_labeled,
        )
        compiled_mapper = optimizer.compile(mapper, trainset=trainset, valset=valset)
        score_after = evaluator.evaluate(compiled_mapper, eval_target).mean_score
        print(f"Optimized mean score: {score_after:.3f} (Δ: {score_after - score_before:+.3f})")

        out_file = output_path or "optimized_mapper.json"
        save_optimized_program(
            compiled_mapper,
            out_file,
            metadata={
                "score_before": round(score_before, 4),
                "score_after": round(score_after, 4),
                "train_examples": len(trainset),
            },
        )
        print(
            "To use this program in production, configure 'compiled_program_path' in "
            "pyproject.toml:"
        )
        print(f'  [tool.toolforge.dspy]\n  compiled_program_path = "{output_path}"\n')
    except Exception as e:
        print(f"Optimization failed: {e}", file=sys.stderr)
        sys.exit(1)


def benchmark_command(
    dataset_path: str | None = None,
    output_json: str | None = None,
    output_csv: str | None = None,
    file_path: str | None = None,
) -> None:
    """Run quantitative side-by-side benchmark comparing Baseline vs DSPy tool mapping."""
    from toolforge.intelligence import (
        BenchmarkRunner,
        DSPyToolMapper,
        MappingDataset,
        StaticToolMapper,
        get_default_benchmark_dataset,
        is_dspy_available,
    )

    try:
        _, project = resolve_server_instance(file_path)
    except Exception:
        project = None

    # Determine DSPy configuration
    dspy_mapper = None
    if (
        project is not None
        and project.config is not None
        and project.config.dspy is not None
        and project.config.dspy.enabled
    ):
        if is_dspy_available():
            project.config.dspy.configure_lm()
            dspy_mapper = DSPyToolMapper.from_config(project.config.dspy)
    elif is_dspy_available():
        dspy_mapper = DSPyToolMapper()

    static_mapper = StaticToolMapper()
    if dspy_mapper is None:
        dspy_mapper = DSPyToolMapper()

    # Load dataset
    if dataset_path:
        try:
            dataset = MappingDataset.from_file(dataset_path)
        except Exception as e:
            print(f"Error loading benchmark dataset '{dataset_path}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        dataset = get_default_benchmark_dataset()

    ds_label = f"custom ({dataset_path})" if dataset_path else "default built-in (10 diverse tools)"
    print("ToolForge Quantitative Benchmark")
    print("─────────────────────────────────────────────────────────────────")
    print(f"Dataset:            {ds_label}")
    print(f"Sample Count:       {len(dataset)} examples")
    print(f"Baseline System:    {static_mapper.__class__.__name__} (Deterministic Passthrough)")
    print(f"DSPy System:        {dspy_mapper.__class__.__name__} (Semantic Understanding)")
    print()
    print("Running evaluations...")

    runner = BenchmarkRunner(static_mapper=static_mapper, dspy_mapper=dspy_mapper)
    comparison = runner.run(dataset=dataset)

    print()
    print("Results Summary:")
    print(comparison.to_markdown_table())
    print()

    acc_diff = (comparison.dspy.mapping_accuracy - comparison.baseline.mapping_accuracy) * 100
    lat_diff = comparison.dspy.avg_latency_ms - comparison.baseline.avg_latency_ms
    print(f"• Accuracy Impact:    {acc_diff:+.1f}% semantic mapping accuracy")
    print(f"• Latency Trade-off:  {lat_diff:+.2f} ms per tool mapping")
    if comparison.dspy.total_tokens > 0:
        d_tok = comparison.dspy.total_tokens
        d_p = comparison.dspy.prompt_tokens
        d_c = comparison.dspy.completion_tokens
        d_calls = comparison.dspy.llm_calls
        print(
            f"• LLM Consumption:    {d_tok} tokens ({d_p} prompt, {d_c} completion) "
            f"across {d_calls} calls"
        )
    print()

    if output_json:
        comparison.to_json(output_json)
        print(f"Saved machine-readable JSON results to: {output_json}")

    if output_csv:
        comparison.to_csv(output_csv)
        print(f"Saved machine-readable CSV results to:  {output_csv}")
