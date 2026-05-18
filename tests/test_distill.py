from __future__ import annotations

from qaoa.skills.distill import DistillEngine, DistilledSkill


def test_distill_extracts_category_and_domain():
    engine = DistillEngine()
    markdown = """---
name: data-analyzer
description: Analyze data and produce reports
category: analysis
domain: science
tools:
  - file.read
  - file.write
permissions:
  - read
  - write
---

# data-analyzer

## Objective
Analyze data files and produce structured reports.

## Steps
1. Read the input data file
2. Analyze the contents
3. Write the report
4. Respond with summary
"""
    result = engine.distill(markdown)
    assert result.category == "analysis"
    assert result.domain == "science"
    assert result.name == "data-analyzer"
    assert "file.read" in result.tool_bindings
    assert "data" in result.intent.lower()


def test_distill_infers_from_content_when_metadata_missing():
    engine = DistillEngine()
    markdown = """# web-scraper

Scrape web pages and extract structured data.

## Steps
1. Fetch the URL content
2. Parse HTML and extract data
3. Save results to file
"""
    result = engine.distill(markdown)
    assert result.category in ("operations", "search", "generate")
    assert result.name == "web-scraper"


def test_distill_extracts_instruction_intent():
    engine = DistillEngine()
    markdown = """---
name: deploy-app
description: Deploy application to production
category: operations
domain: technology
---
# deploy-app

## Steps
1. Build the Docker image
2. Push to registry
3. Deploy to Kubernetes cluster
4. Verify health checks pass
"""
    result = engine.distill(markdown)
    assert len(result.intent) > 0  # should capture first meaningful line
    assert result.tool_bindings == []
