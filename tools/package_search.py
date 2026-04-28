"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for software packages across multiple programming language registries."""
    import json
    import urllib.request
    import urllib.error
    import urllib.parse
    
    try:
        data = json.loads(payload)
        
        # Validate required inputs
        if "query" not in data or not isinstance(data["query"], str) or not data["query"].strip():
            return json.dumps({"error": "'query' is required and must be a non-empty string"}, ensure_ascii=False)
        
        query = data["query"].strip()
        registries = data.get("registries", ["npm", "pypi", "crates.io", "rubygems", "nuget"])
        max_results = min(data.get("max_results", 5), 20)
        exact_match = data.get("exact_match", False)
        
        # Registry API configurations
        registry_apis = {
            "npm": {
                "search_url": "https://registry.npmjs.org/-/v1/search",
                "package_url": "https://registry.npmjs.org/{package}",
                "parse_fn": lambda r, exact: _parse_npm(r, exact)
            },
            "pypi": {
                "search_url": "https://pypi.org/simple/",
                "package_url": "https://pypi.org/pypi/{package}/json",
                "parse_fn": lambda r, exact: _parse_pypi(r, exact)
            },
            "crates.io": {
                "search_url": "https://crates.io/api/v1/crates",
                "package_url": "https://crates.io/api/v1/crates/{package}",
                "parse_fn": lambda r, exact: _parse_crates(r, exact)
            },
            "rubygems": {
                "search_url": "https://rubygems.org/api/v1/search.json",
                "package_url": "https://rubygems.org/api/v1/gems/{package}.json",
                "parse_fn": lambda r, exact: _parse_rubygems(r, exact)
            },
            "nuget": {
                "search_url": "https://api.nuget.org/v3/query",
                "package_url": "https://api.nuget.org/v3/registration5-gz-semver2/{package}/index.json",
                "parse_fn": lambda r, exact: _parse_nuget(r, exact)
            }
        }
        
        def _fetch_json(url, headers=None):
            """Fetch and parse JSON from a URL."""
            req = urllib.request.Request(url)
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    return json.loads(response.read().decode('utf-8'))
            except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
                raise Exception(f"Failed to fetch from {url}: {str(e)}")
        
        def _parse_npm(data, exact):
            """Parse npm registry search results."""
            results = []
            objects = data.get("objects", [])
            for obj in objects:
                pkg = obj.get("package", {})
                name = pkg.get("name", "")
                if exact and name.lower() != query.lower():
                    continue
                results.append({
                    "name": name,
                    "version": pkg.get("version", "unknown"),
                    "description": pkg.get("description", ""),
                    "registry": "npm"
                })
            return results[:max_results]
        
        def _parse_pypi(data, exact):
            """Parse PyPI registry search results."""
            results = []
            # PyPI simple API returns HTML, use JSON API for specific packages
            try:
                pkg_url = registry_apis["pypi"]["package_url"].format(package=query)
                pkg_data = _fetch_json(pkg_url)
                info = pkg_data.get("info", {})
                name = info.get("name", "")
                if not exact or name.lower() == query.lower():
                    results.append({
                        "name": name,
                        "version": info.get("version", "unknown"),
                        "description": info.get("summary", ""),
                        "registry": "pypi"
                    })
            except Exception:
                pass
            return results[:max_results]
        
        def _parse_crates(data, exact):
            """Parse crates.io registry search results."""
            results = []
            crates = data.get("crates", [])
            for crate in crates:
                name = crate.get("name", "")
                if exact and name.lower() != query.lower():
                    continue
                results.append({
                    "name": name,
                    "version": crate.get("max_version", "unknown"),
                    "description": crate.get("description", ""),
                    "registry": "crates.io"
                })
            return results[:max_results]
        
        def _parse_rubygems(data, exact):
            """Parse RubyGems registry search results."""
            results = []
            for gem in data:
                name = gem.get("name", "")
                if exact and name.lower() != query.lower():
                    continue
                results.append({
                    "name": name,
                    "version": gem.get("version", "unknown"),
                    "description": gem.get("info", ""),
                    "registry": "rubygems"
                })
            return results[:max_results]
        
        def _parse_nuget(data, exact):
            """Parse NuGet registry search results."""
            results = []
            items = data.get("data", [])
            for item in items:
                name = item.get("id", "")
                if exact and name.lower() != query.lower():
                    continue
                results.append({
                    "name": name,
                    "version": item.get("version", "unknown"),
                    "description": item.get("description", ""),
                    "registry": "nuget"
                })
            return results[:max_results]
        
        # Execute search across requested registries
        all_results = []
        errors = []
        
        for registry in registries:
            if registry not in registry_apis:
                errors.append(f"Unknown registry: {registry}")
                continue
            
            try:
                api_config = registry_apis[registry]
                if exact_match and not api_config.get("package_url"):
                    continue
                
                url = api_config["package_url"].format(package=query) if exact_match else api_config["search_url"]
                headers = {"Accept": "application/json"}
                
                # Add query parameters for search endpoints
                if not exact_match:
                    params = urllib.parse.urlencode({"q": query})
                    url = f"{url}?{params}"
                
                response_data = _fetch_json(url, headers)
                results = api_config["parse_fn"](response_data, exact_match)
                all_results.extend(results)
            except Exception as e:
                errors.append(f"{registry}: {str(e)}")
        
        # Prepare response
        response = {
            "query": query,
            "results": all_results,
            "total": len(all_results)
        }
        
        if errors:
            response["warnings"] = errors
        
        return json.dumps(response, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return f"error: Invalid JSON input - {str(e)}"
    except Exception as e:
        return f"error: {str(e)}"


TOOL_SPEC = {
    "name": "package_search",
    "description": "Search for software packages across multiple programming language registries (npm, PyPI, crates.io, rubygems, nuget) by name or keywords, returning the top matching packages with their latest version, description, and registry metadata.",
    "category": "search",
    "domain": "technology",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search term, package name, or keywords to search for in package registries.",
            "examples": [
                "flask",
                "react",
                "serde",
                "rails",
                "newtonsoft.json"
            ]
        },
        "registries": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "npm",
                    "pypi",
                    "crates.io",
                    "rubygems",
                    "nuget"
                ]
            },
            "description": "Optional: Filter search to specific package registries. If omitted, searches across all available registries.",
            "examples": [
                [
                    "npm",
                    "pypi"
                ]
            ]
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "description": "Optional: Maximum number of results to return per registry (default: 5).",
            "examples": [
                10
            ]
        },
        "exact_match": {
            "type": "boolean",
            "description": "Optional: If true, only return exact package name matches instead of fuzzy/keyword search (default: false).",
            "examples": [
                true
            ]
        }
    },
    "required": [
        "query"
    ]
},
}
