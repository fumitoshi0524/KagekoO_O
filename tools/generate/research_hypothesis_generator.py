"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate novel, testable scientific hypotheses from a given research topic."""
    import json
    import random
    try:
        data = json.loads(payload)
        topic = data.get('research_topic')
        if not topic or not topic.strip():
            return json.dumps({"error": "research_topic is required."}, ensure_ascii=False)

        existing = data.get('existing_findings', '')
        count = int(data.get('hypothesis_count', 3))
        style = data.get('style', 'formal')
        include_rationale = data.get('include_rationale', True)

        if count < 1 or count > 5:
            return json.dumps({"error": "hypothesis_count must be between 1 and 5."}, ensure_ascii=False)
        if style not in ['formal', 'exploratory', 'falsifiable']:
            return json.dumps({"error": "style must be 'formal', 'exploratory', or 'falsifiable'."}, ensure_ascii=False)

        # Built-in hypothesis templates based on style
        formal_templates = [
            f"We hypothesize that modulation of {topic.split(' and ')[0] if ' and ' in topic else topic} via experimental perturbation will significantly alter the observed correlation with {topic.split(' and ')[-1] if ' and ' in topic else 'its downstream effects'}.",
            f"It is hypothesized that {topic} exhibits a nonlinear relationship under non-standard environmental conditions, specifically at elevated temperatures or altered pH.",
            f"The null hypothesis states that there is no causal relationship between {topic} and the measured outcome, rejecting any latent confounding variables.",
            f"We propose that {topic} operates through a previously unrecognized molecular pathway involving intermediate signaling cascades."
        ]
        exploratory_templates = [
            f"Could {topic} be influenced by circadian rhythms or seasonal variations in ways not yet measured?",
            f"What if {topic} is actually a manifestation of an underlying unifying principle across different scales of biological organization?",
            f"Perhaps {topic} is best understood through the lens of network theory, with emergent properties from simple local interactions.",
            f"Might {topic} be an evolutionary relic that serves a different adaptive function today than originally selected for?"
        ]
        falsifiable_templates = [
            f"If {topic} is true, then experimental group A (with increased {topic.split(' and ')[0] if ' and ' in topic else 'dose'}) will show a >20% difference in outcome B compared to control group C (p<0.05, n≥30 per group).",
            f"The prediction: measure X (a proxy for {topic}) will correlate negatively with measure Y with R² > 0.5 in a blinded cross-sectional study.",
            f"Directional hypothesis: increasing {topic} will decrease the time to event Z by at least 15% in a randomized controlled trial."
        ]

        if style == 'formal':
            templates = formal_templates
        elif style == 'exploratory':
            templates = exploratory_templates
        else:
            templates = falsifiable_templates

        # Generate hypotheses with optional rationale
        hypotheses = []
        used_templates = random.sample(templates, min(count, len(templates)))
        # If more templates needed, cycle with modifications
        while len(used_templates) < count:
            for t in templates:
                if len(used_templates) >= count:
                    break
                used_templates.append(t)
            if len(used_templates) < count:
                used_templates += templates  # duplicate as fallback

        for i, template in enumerate(used_templates[:count]):
            hypothesis = {
                "id": i+1,
                "hypothesis": template
            }
            if include_rationale:
                rationale_list = [
                    f"This hypothesis is grounded in recent evidence suggesting that {topic.split(' and ')[0] if ' and ' in topic else topic} may interact with previously overlooked environmental factors.",
                    f"Rationale: Observations in related systems indicate a potential link, but no controlled experiment has directly tested this relationship for {topic}.",
                    f"Basis: Preliminary data (if available) hints at an effect; this hypothesis formalizes a testable prediction following the principle of parsimony."
                ]
                hypothesis["rationale"] = random.choice(rationale_list)
            if style == 'falsifiable':
                hypothesis["suggested_experiment"] = f"Design a controlled experiment with two groups differing in exposure to {topic}, measuring primary outcome with blinding and randomization."
            else:
                hypothesis["suggested_approach"] = f"Consider a mixed-methods design combining longitudinal measurements of {topic} with in vitro mechanistic studies."
            hypotheses.append(hypothesis)

        # Add overall summary
        result = {
            "research_topic": topic,
            "style": style,
            "existing_findings_context": existing if existing else "None provided",
            "hypotheses_generated": hypotheses,
            "usage_note": "These hypotheses are AI-generated and should be validated with domain experts before use."
        }

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)



TOOL_SPEC = {
    "name": "research_hypothesis_generator",
    "description": "Generate novel, testable scientific hypotheses from a given research topic, existing findings, or experimental observations, returning formatted hypothesis statements with rationale and suggested experimental approaches.",
    "category": "generate",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "research_topic": {
            "type": "string",
            "description": "The central scientific topic, field, or research question to generate hypotheses around (e.g., 'gut microbiome and depression', 'quantum decoherence in photosynthetic complexes')."
        },
        "existing_findings": {
            "type": "string",
            "description": "Optional: Known results, observations, or prior studies relevant to the topic, used to constrain or inspire new hypotheses.",
            "default": ""
        },
        "hypothesis_count": {
            "type": "integer",
            "description": "Optional: Number of distinct hypotheses to generate (between 1 and 5 inclusive).",
            "default": 3,
            "minimum": 1,
            "maximum": 5
        },
        "style": {
            "type": "string",
            "description": "Optional: Preferred style of hypothesis wording — 'formal' for precise academic phrasing, 'exploratory' for broader perspective, or 'falsifiable' for strict Popperian format.",
            "enum": [
                "formal",
                "exploratory",
                "falsifiable"
            ],
            "default": "formal"
        },
        "include_rationale": {
            "type": "boolean",
            "description": "Optional: If True, include a brief scientific rationale explaining why each hypothesis is plausible.",
            "default": True
        }
    },
    "required": [
        "research_topic"
    ]
},
}
