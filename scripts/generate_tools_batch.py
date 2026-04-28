"""Batch tool generation server script — UniToolCall-style scalable generation.

Usage:
    python scripts/generate_tools_batch.py --count 200 --provider openai --api-key sk-xxx
    python scripts/generate_tools_batch.py --count 500 --provider deepseek --api-key sk-xxx --model deepseek-chat
    python scripts/generate_tools_batch.py --count 100 --resume  # resume from last checkpoint

The script:
1. Loads existing tools from tools/<category>/ recursively as the reference pool
2. Uses inverse-frequency sampling to pick under-represented domain/category targets
3. Picks 5 random reference tools as few-shot examples
4. Generates 1 new tool per iteration targeting the sampled domain+category
5. Saves to tools/<category>/ and adds to the growing pool
6. Checkpoints progress to tools/.generation_state.json for resume
7. Logs everything to tools/generation.log
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from collections import Counter
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────

ALL_DOMAINS = [
    "finance", "technology", "education", "healthcare", "entertainment",
    "travel", "business", "lifestyle", "science", "social",
    "sports", "environment", "culture",
]

ALL_CATEGORIES = [
    "analysis", "operations", "system", "visualization", "search", "generate",
]

CATEGORY_DEFINITIONS = {
    "analysis": "Data analysis and insights (statistical analysis, trend analysis, data mining, predictive analysis, business intelligence)",
    "operations": "Business process operations (create, update, delete, workflow management, business logic execution)",
    "system": "System administration and maintenance (system configuration, user management, system monitoring, technical maintenance)",
    "visualization": "Data visualization and presentation (chart generation, report creation, data display, dashboard creation)",
    "search": "Information retrieval and search (full-text search, fuzzy search, index query, structured query, data lookup)",
    "generate": "Content and data generation (content generation, code generation, intelligent recommendation, AI generation, automated creation)",
}

DOMAIN_DEFINITIONS = {
    "finance": "Finance related (payment, investment, wealth management, insurance, trading)",
    "technology": "Technology and software development (programming, system management, software tools, IT infrastructure)",
    "education": "Education and learning (academic courses, training programs, educational content, learning management)",
    "healthcare": "Medical and health services (medical treatment, health monitoring, medical devices, healthcare management)",
    "entertainment": "Entertainment and media (music, games, film/TV, social entertainment, news, content creation)",
    "travel": "Travel and transportation (tourism, transportation, accommodation, attractions, travel planning)",
    "business": "Business management (enterprise operations, marketing, customer relations, business processes)",
    "lifestyle": "Daily life services (shopping, food, housekeeping, personal tools, consumer services)",
    "science": "Scientific research and analysis (research projects, scientific experiments, academic studies, data analysis)",
    "social": "Social communication and community (social networking, communication tools, community management, collaboration)",
    "sports": "Sports and fitness (sports activities, fitness training, sports events, athletic performance)",
    "environment": "Environment and sustainability (environmental protection, climate monitoring, ecology, sustainable development)",
    "culture": "Culture and arts (art, literature, history, cultural events, language learning, creative content)",
}

# ── Logging ─────────────────────────────────────────────────────────

def setup_logging(log_path: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ── Tool loading from tools/ directory ──────────────────────────────

def load_existing_tools(tools_dir: Path) -> list[dict]:
    """Load TOOL_SPEC from all *.py files in tools/ recursively."""
    tools: list[dict] = []
    for path in sorted(tools_dir.rglob("*.py")):
        if path.name.startswith("_") or path.name.startswith("."):
            continue
        spec = _extract_tool_spec(path)
        if spec:
            tools.append(spec)
    return tools


def _extract_tool_spec(path: Path) -> dict | None:
    """Extract TOOL_SPEC dict from a Python module file."""
    import ast
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return None
    start = content.find("TOOL_SPEC = {")
    if start == -1:
        return None
    brace_start = content.find("{", start)
    if brace_start == -1:
        return None
    depth = 0
    i = brace_start
    while i < len(content):
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                dict_str = content[brace_start : i + 1]
                try:
                    return ast.literal_eval(dict_str)
                except (ValueError, SyntaxError):
                    return None
        i += 1
    return None


# ── Inverse frequency sampling ──────────────────────────────────────

def compute_inverse_weights(labels: list[str], universe: list[str], alpha: float = 1.0) -> dict[str, float]:
    """Inverse frequency weights: rarer labels get higher probability."""
    counter = Counter(l for l in labels if l in universe)
    weights = {}
    for label in universe:
        count = counter.get(label, 0) + alpha
        weights[label] = 1.0 / count
    total = sum(weights.values())
    return {k: v / total for k, v in weights.items()}


def sample_balanced_target(tools: list[dict], universe: list[str], field: str) -> str:
    """Sample a target label using inverse frequency weighting."""
    labels = [t.get(field, "") for t in tools if t.get(field) in universe]
    weights = compute_inverse_weights(labels, universe)
    items = list(weights.keys())
    probs = [weights[d] for d in items]
    return random.choices(items, weights=probs, k=1)[0]


# ── Prompt building ─────────────────────────────────────────────────

def build_tool_generation_prompt(
    *,
    reference_tools: list[dict],
    target_domain: str,
    target_category: str,
) -> str:
    """Build the UniToolCall-style few-shot generation prompt."""
    ref_json = json.dumps(
        [
            {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "category": t.get("category", ""),
                "domain": t.get("domain", ""),
            }
            for t in reference_tools
        ],
        ensure_ascii=False,
        indent=2,
    )

    return (
        "You are a professional tool concept generation expert for an AI agent runtime.\n"
        "Generate exactly 1 new tool concept following these strict specifications.\n\n"

        "## Output Format\n"
        "Return pure JSON only, no markdown markers, directly parseable by json.loads().\n\n"

        "## Required Fields\n"
        "- name: Tool identifier (lowercase + underscores)\n"
        "- description: Detailed functional description with clear verbs, business entities, and what the tool returns\n"
        "- category: Must be exactly '{target_category}'\n"
        "- domain: Must be exactly '{target_domain}'\n"
        "- inputSchema: Complete JSON Schema (type: object, properties with type/description for each param, required array)\n\n"

        f"## Category: {target_category}\n"
        f"{CATEGORY_DEFINITIONS.get(target_category, target_category)}\n\n"

        f"## Domain: {target_domain}\n"
        f"{DOMAIN_DEFINITIONS.get(target_domain, target_domain)}\n\n"

        "## Description Rules\n"
        "1. Use one sentence to clearly summarize the core functionality\n"
        "2. Include the core business entities the tool operates on\n"
        "3. Describe what the tool returns and what it's used for\n"
        "4. Do NOT include technical implementation details\n"
        "5. Make the description distinguishable from other similar tools\n\n"

        "## InputSchema Rules\n"
        "1. Each parameter needs type, description (business meaning, format, constraints)\n"
        "2. Use enum for fixed option sets\n"
        "3. Optional parameters: start description with 'Optional:'\n"
        "4. Do NOT put example values in description — use examples field instead\n"
        "5. Mark required parameters in the required array\n\n"

        "## Implementation\n"
        "Provide a complete Python function:\n"
        'def run(payload: str) -> str:\n'
        '    """Tool description."""\n'
        "    import json\n"
        "    try:\n"
        "        data = json.loads(payload)\n"
        "        # ... business logic ...\n"
        "        return json.dumps(result, ensure_ascii=False)\n"
        "    except Exception as e:\n"
        "        return f'error: {e}'\n\n"

        "The implementation must:\n"
        "- Parse JSON payload\n"
        "- Validate required inputs\n"
        "- Execute real business logic (not stubs)\n"
        "- Return structured results as JSON string\n"
        "- Handle errors gracefully\n\n"

        "## Reference Tools (for context, generate something DIFFERENT)\n"
        f"```json\n{ref_json}\n```\n\n"

        "## Target\n"
        f"Category: {target_category}\n"
        f"Domain: {target_domain}\n\n"

        "Generate a tool that is clearly different from all reference tools. "
        "Focus on a different business scenario or use case within the target domain.\n\n"

        "Return ONLY this JSON:\n"
        '{"name": "...", "description": "...", "category": "' + target_category + '", "domain": "' + target_domain + '", '
        '"inputSchema": {"type": "object", "properties": {...}, "required": [...]}, '
        '"implementation": "def run(payload: str) -> str:\\n    ...", "risk_level": "read"}'
    )


# ── Tool module writer ──────────────────────────────────────────────

def write_tool_module(tool_data: dict, tools_dir: Path) -> Path:
    """Write a generated tool dict to a Python module file in the correct category subdirectory."""
    name = str(tool_data.get("name", "unnamed")).strip().replace(".", "_")
    category = str(tool_data.get("category", "operations"))
    if category not in ("analysis", "operations", "system", "visualization", "search", "generate"):
        category = "operations"
    out_dir = tools_dir / category
    out_dir.mkdir(parents=True, exist_ok=True)
    description = str(tool_data.get("description", ""))
    category = str(tool_data.get("category", "operations"))
    domain = str(tool_data.get("domain", "technology"))
    input_schema = tool_data.get("inputSchema", tool_data.get("schema", {}))
    implementation = str(tool_data.get("implementation", "def run(payload: str) -> str:\n    return payload"))
    risk_level = str(tool_data.get("risk_level", "read"))

    if not implementation.startswith("def run("):
        body_lines = implementation.splitlines()
        indented = "\n".join(f"    {line}" for line in body_lines)
        implementation = f'def run(payload: str) -> str:\n    """{description}"""\n{indented}'

    schema_json = json.dumps(input_schema, indent=4, ensure_ascii=False)

    module = (
        '"""Auto-generated tool module."""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n\n\n"
        f"{implementation}\n\n\n"
        "TOOL_SPEC = {\n"
        f'    "name": {json.dumps(name, ensure_ascii=False)},\n'
        f'    "description": {json.dumps(description, ensure_ascii=False)},\n'
        f'    "category": {json.dumps(category, ensure_ascii=False)},\n'
        f'    "domain": {json.dumps(domain, ensure_ascii=False)},\n'
        f'    "risk_level": {json.dumps(risk_level, ensure_ascii=False)},\n'
        f'    "schema": {schema_json},\n'
        "}\n"
    )

    output_path = out_dir / f"{name}.py"
    output_path.write_text(module, encoding="utf-8")
    return output_path


# ── LLM Adapter ─────────────────────────────────────────────────────

def create_llm(provider: str, api_key: str, model: str | None = None, base_url: str | None = None):
    """Create an LLM adapter compatible with Kageko's interface."""
    from qaoa.adapters.llm import create_llm_adapter
    return create_llm_adapter(provider=provider, api_key=api_key, model=model, base_url=base_url)


# ── State management for resume ─────────────────────────────────────

def load_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"generated": 0, "errors": 0, "names": []}


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Main generation loop ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch tool generation — UniToolCall style")
    parser.add_argument("--count", type=int, default=100, help="Number of tools to generate")
    parser.add_argument("--provider", default="openai", help="LLM provider")
    parser.add_argument("--api-key", help="API key (or set env var)")
    parser.add_argument("--model", help="Model name")
    parser.add_argument("--base-url", help="Custom base URL")
    parser.add_argument("--tools-dir", default="./tools", help="Output directory for generated tools")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between API calls")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries per tool")
    args = parser.parse_args()

    tools_dir = Path(args.tools_dir).resolve()
    tools_dir.mkdir(parents=True, exist_ok=True)
    state_path = tools_dir / ".generation_state.json"
    log_path = tools_dir / "generation.log"
    setup_logging(log_path)

    # Resolve API key
    import os
    api_key = args.api_key or os.getenv("KAGEKO_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: No API key. Set --api-key or env var.")
        return 1

    # Load state
    if args.resume:
        state = load_state(state_path)
        logging.info(f"Resuming: {state['generated']} generated, {state['errors']} errors")
    else:
        if state_path.exists():
            logging.warning("State file exists. Use --resume to continue, or delete .generation_state.json to start fresh.")
            return 1
        state = {"generated": 0, "errors": 0, "names": []}

    # Create LLM adapter
    logging.info(f"Creating LLM adapter: provider={args.provider}, model={args.model}")
    llm = create_llm(args.provider, api_key, args.model, args.base_url)

    target = args.count
    start_count = state["generated"]
    logging.info(f"Target: {target} tools (starting from {start_count})")

    for i in range(start_count, target):
        logging.info(f"--- Tool {i + 1}/{target} ---")

        # Load current tools as reference pool
        existing = load_existing_tools(tools_dir)
        if not existing:
            logging.warning("No existing tools found. Please generate a seed set first.")
            return 1

        # Inverse-frequency sampling for balanced distribution
        target_domain = sample_balanced_target(existing, ALL_DOMAINS, "domain")
        target_category = sample_balanced_target(existing, ALL_CATEGORIES, "category")
        logging.info(f"Target: domain={target_domain}, category={target_category}")

        # Pick 5 random reference tools
        ref_tools = random.sample(existing, min(5, len(existing)))

        # Build prompt
        prompt = build_tool_generation_prompt(
            reference_tools=ref_tools,
            target_domain=target_domain,
            target_category=target_category,
        )

        # Generate with retries
        success = False
        for retry in range(args.max_retries):
            try:
                raw = llm.complete(prompt)
                # Extract JSON
                parsed = _extract_json_from_response(raw)
                if parsed is None:
                    logging.warning(f"Retry {retry + 1}: failed to parse JSON response")
                    time.sleep(args.delay)
                    continue

                # Validate required fields
                required = ["name", "description", "category", "domain", "inputSchema", "implementation"]
                missing = [f for f in required if f not in parsed]
                if missing:
                    logging.warning(f"Retry {retry + 1}: missing fields {missing}")
                    time.sleep(args.delay)
                    continue

                # Validate category/domain match
                if parsed["category"] != target_category or parsed["domain"] != target_domain:
                    logging.warning(
                        f"Retry {retry + 1}: wrong labels "
                        f"(got {parsed.get('category')}/{parsed.get('domain')}, "
                        f"expected {target_category}/{target_domain})"
                    )
                    time.sleep(args.delay)
                    continue

                # Skip if name already exists
                if parsed["name"] in state["names"]:
                    logging.info(f"Skipping duplicate name: {parsed['name']}")
                    success = True
                    break

                # Write the tool module
                output_path = write_tool_module(parsed, tools_dir)
                state["generated"] += 1
                state["names"].append(parsed["name"])
                save_state(state_path, state)

                logging.info(
                    f"Generated: {parsed['name']} [{parsed['category']}/{parsed['domain']}] "
                    f"-> {output_path.name}"
                )
                success = True
                break

            except Exception as e:
                logging.error(f"Retry {retry + 1}: {e}")
                time.sleep(args.delay * (retry + 1))

        if not success:
            state["errors"] += 1
            save_state(state_path, state)
            logging.error(f"Failed after {args.max_retries} retries")

        # Current stats
        existing = load_existing_tools(tools_dir)
        cat_dist = Counter(t.get("category", "?") for t in existing)
        dom_dist = Counter(t.get("domain", "?") for t in existing)
        logging.info(f"Progress: {len(existing)} tools | cats: {dict(cat_dist)} | doms: {dict(dom_dist)}")

        # Pace API calls
        time.sleep(args.delay)

    logging.info(f"Done. Generated {state['generated'] - start_count} new tools ({state['errors']} errors).")
    logging.info(f"Total tools: {len(load_existing_tools(tools_dir))}")
    return 0


def _extract_json_from_response(raw: str) -> dict | None:
    """Extract JSON dict from LLM response, handling markdown code blocks."""
    candidate = raw.strip()
    if not candidate:
        return None
    # Try extracting from ```json ... ``` blocks first
    if "```json" in candidate:
        start = candidate.find("```json") + 7
        end = candidate.find("```", start)
        if end > start:
            candidate = candidate[start:end].strip()
    elif "```" in candidate:
        start = candidate.find("```") + 3
        end = candidate.find("```", start)
        if end > start:
            candidate = candidate[start:end].strip()
    # Find JSON object
    brace_start = candidate.find("{")
    brace_end = candidate.rfind("}")
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        candidate = candidate[brace_start : brace_end + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
