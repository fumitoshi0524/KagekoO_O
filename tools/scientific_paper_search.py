"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Search for scientific papers across research databases by keywords, authors, publication year range, and scientific domain."""
    import json
    import random
    from datetime import datetime

    try:
        data = json.loads(payload)
        query = data.get("query", "")
        if not query:
            return json.dumps({"error": "Missing required parameter: query"}, ensure_ascii=False)

        authors = data.get("authors", "")
        year_min = data.get("year_min", 1990)
        year_max = data.get("year_max", datetime.now().year)
        domain_filter = data.get("domain_filter", None)
        max_results = min(data.get("max_results", 10), 50)

        # Simulated paper database (in production, this would query real APIs like arXiv, PubMed, etc.)
        sample_papers = [
            {"title": "Deep Learning in Protein Structure Prediction", "authors": ["J. Smith", "M. Johnson", "L. Chen"], "journal": "Nature", "year": 2023, "doi": "10.1038/s41586-023-06234-5", "domain": "biology", "abstract": "We present a novel deep learning approach for predicting protein tertiary structures from amino acid sequences with unprecedented accuracy."},
            {"title": "Quantum Entanglement in Many-Body Systems", "authors": ["A. Garcia", "P. Patel"], "journal": "Physical Review Letters", "year": 2022, "doi": "10.1103/PhysRevLett.128.120401", "domain": "physics", "abstract": "We investigate the entanglement properties of quantum many-body systems using tensor network methods."},
            {"title": "Climate Change Impact on Global Crop Yields", "authors": ["R. Williams", "S. Kim", "T. Nakamura", "K. O'Brien"], "journal": "Science", "year": 2024, "doi": "10.1126/science.adk3472", "domain": "environmental_science", "abstract": "A comprehensive analysis of climate change effects on major crop yields across different geographic regions."},
            {"title": "Graph Neural Networks for Molecular Property Prediction", "authors": ["L. Zhang", "X. Li"], "journal": "Journal of Chemical Information and Modeling", "year": 2023, "doi": "10.1021/acs.jcim.3c00123", "domain": "chemistry", "abstract": "We develop a new graph neural network architecture for accurate prediction of molecular properties."},
            {"title": "Advances in Reinforcement Learning for Robotics", "authors": ["M. Brown", "E. Davis", "H. Suzuki"], "journal": "IEEE Transactions on Robotics", "year": 2023, "doi": "10.1109/TRO.2023.3278945", "domain": "engineering", "abstract": "A survey of recent advances in reinforcement learning algorithms applied to robotic control tasks."},
            {"title": "Genome-Wide Association Study of Alzheimer's Disease", "authors": ["C. Martinez", "J. Lee", "B. Anderson"], "journal": "Nature Genetics", "year": 2021, "doi": "10.1038/s41588-021-00921-3", "domain": "medicine", "abstract": "We identify 42 new genetic loci associated with Alzheimer's disease through a genome-wide association study."},
            {"title": "Cryptographic Protocols for Secure Multi-Party Computation", "authors": ["D. Wilson", "F. Zhao"], "journal": "Communications of the ACM", "year": 2022, "doi": "10.1145/3544548.3581322", "domain": "computer_science", "abstract": "We present efficient protocols for secure multi-party computation with improved communication complexity."},
            {"title": "Topological Data Analysis for Neuroscience Applications", "authors": ["G. Fischer", "H. Mueller"], "journal": "Neuron", "year": 2023, "doi": "10.1016/j.neuron.2023.05.012", "domain": "neuroscience", "abstract": "Application of topological data analysis methods to understand neural activity patterns."},
            {"title": "Numerical Solutions to Navier-Stokes Equations", "authors": ["A. Petrova", "I. Tanaka"], "journal": "Journal of Computational Physics", "year": 2021, "doi": "10.1016/j.jcp.2021.110567", "domain": "mathematics", "abstract": "We develop new numerical schemes for solving Navier-Stokes equations with improved stability properties."},
            {"title": "Exoplanet Detection via Transit Photometry", "authors": ["N. Clark", "O. Williams", "P. Singh"], "journal": "Astronomy & Astrophysics", "year": 2022, "doi": "10.1051/0004-6361/202244124", "domain": "astronomy", "abstract": "We report the detection of three new exoplanets using transit photometry from the TESS mission."},
            {"title": "CRISPR-Cas9 Gene Editing in Human Stem Cells", "authors": ["S. Yamamoto", "T. Reed"], "journal": "Cell", "year": 2023, "doi": "10.1016/j.cell.2023.03.045", "domain": "biology", "abstract": "Efficient CRISPR-Cas9 mediated gene editing in human induced pluripotent stem cells."},
            {"title": "Machine Learning for Drug Discovery", "authors": ["K. Park", "J. Thompson", "R. Gupta", "L. Wang"], "journal": "Nature Reviews Drug Discovery", "year": 2024, "doi": "10.1038/s41573-024-00089-5", "domain": "medicine", "abstract": "Review of machine learning approaches accelerating drug discovery pipelines."}
        ]

        # Filter papers based on query
        query_lower = query.lower()
        matched_papers = []
        for paper in sample_papers:
            # Check title and abstract against query
            if query_lower in paper["title"].lower() or query_lower in paper["abstract"].lower():
                # Check domain filter
                if domain_filter and paper["domain"] != domain_filter:
                    continue
                # Check year range
                if paper["year"] < year_min or paper["year"] > year_max:
                    continue
                # Check authors filter
                if authors:
                    author_list = [a.strip().lower() for a in authors.split(",")]
                    paper_authors_lower = [a.lower() for a in paper["authors"]]
                    if not any(auth in paper_authors_lower for auth in author_list):
                        continue
                matched_papers.append(paper)

        # Sort by year descending and limit results
        matched_papers.sort(key=lambda x: x["year"], reverse=True)
        matched_papers = matched_papers[:max_results]

        result = {
            "status": "success",
            "total_results": len(matched_papers),
            "papers": matched_papers,
            "search_metadata": {
                "query": query,
                "authors_filter": authors if authors else None,
                "year_range": f"{year_min}-{year_max}",
                "domain_filter": domain_filter,
                "timestamp": datetime.now().isoformat()
            }
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON input: {str(e)}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "scientific_paper_search",
    "description": "Search for scientific papers across research databases by keywords, authors, publication year range, and scientific domain. Returns a list of matching papers with title, authors, journal, publication date, DOI, and abstract.",
    "category": "search",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search keywords or phrases for paper title and abstract content"
        },
        "authors": {
            "type": "string",
            "description": "Optional: Filter by author name(s), comma-separated for multiple authors"
        },
        "year_min": {
            "type": "integer",
            "description": "Optional: Earliest publication year to include (e.g., 2015)"
        },
        "year_max": {
            "type": "integer",
            "description": "Optional: Latest publication year to include (e.g., 2023)"
        },
        "domain_filter": {
            "type": "string",
            "enum": [
                "biology",
                "chemistry",
                "physics",
                "computer_science",
                "mathematics",
                "medicine",
                "engineering",
                "environmental_science",
                "astronomy",
                "neuroscience"
            ],
            "description": "Optional: Restrict search to a specific scientific domain"
        },
        "max_results": {
            "type": "integer",
            "description": "Optional: Maximum number of papers to return (1-50, default 10)",
            "minimum": 1,
            "maximum": 50
        }
    },
    "required": [
        "query"
    ]
},
}
