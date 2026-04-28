"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a scientific hypothesis from a research question and context."""
    import json
    try:
        data = json.loads(payload)
        research_question = data.get("research_question", "")
        background_context = data.get("background_context", "")
        field_of_study = data.get("field_of_study", "biology")
        hypothesis_type = data.get("hypothesis_type", "directional")
        include_design = data.get("include_experimental_design", True)

        if not research_question or len(research_question) < 10:
            return json.dumps({"error": "research_question must be at least 10 characters."}, ensure_ascii=False)

        # Simulate hypothesis generation logic based on field and type
        hypothesis_map = {
            "biology": {
                "directional": "It is hypothesized that [independent variable] significantly affects [dependent variable] due to [mechanism], leading to [predicted outcome].",
                "null": "There is no statistically significant relationship between [independent variable] and [dependent variable] under the given conditions.",
                "causal": "Exposure to [treatment] causes a change in [outcome] through [proposed causal pathway].",
                "correlational": "There is a positive/negative correlation between [variable A] and [variable B] such that [directional prediction].",
                "exploratory": "Exploratory analysis will investigate potential associations between [factors] and [outcome] without directional expectation."
            },
            "physics": {
                "directional": "It is predicted that [parameter] will increase/decrease with respect to [variable] due to [physical principle], deviating from classical predictions by [amount].",
                "null": "No measurable difference in [observable] is expected between [conditions] within experimental uncertainty.",
                "causal": "Applying [force/field] causes [change] in [system] as dictated by [physical law].",
                "correlational": "A linear relationship is expected between [variable X] and [variable Y] with slope proportional to [constant].",
                "exploratory": "Measurements of [phenomenon] will be gathered to detect unknown patterns or anomalies."
            },
            "psychology": {
                "directional": "Participants in [condition A] will show significantly higher [cognitive measure] compared to [condition B], as predicted by [theory].",
                "null": "There is no difference in [behavioral outcome] between the experimental and control groups.",
                "causal": "Priming with [stimulus] causes an increase in [response] through activation of [neural pathway].",
                "correlational": "Higher scores on [measure A] are associated with higher scores on [measure B] in the sample.",
                "exploratory": "The study will explore whether [variable] moderates the relationship between [X] and [Y]."
            },
            "environmental_science": {
                "directional": "Increasing [pollutant] concentration leads to a decrease in [species diversity] due to [mechanism].",
                "null": "No significant effect of [factor] on [ecosystem metric] will be observed.",
                "causal": "Raising [environmental variable] by X units causes [ecosystem response] to shift by Y.",
                "correlational": "A positive correlation exists between [temperature anomaly] and [ice melt rate] over the study period.",
                "exploratory": "Field surveys will characterize unknown inter-species interactions under [conditions]."
            },
            "medicine": {
                "directional": "Patients receiving [treatment] will show improved [outcome] compared to placebo due to [biological mechanism].",
                "null": "There is no difference in [clinical endpoint] between the treatment and control groups.",
                "causal": "Administration of [drug] induces [physiological change] which mediates the therapeutic effect.",
                "correlational": "Higher expression of [biomarker] is associated with worse prognosis in [disease].",
                "exploratory": "An exploratory analysis will identify potential biomarkers predictive of [response]."
            }
        }

        # Fallback for other fields
        if field_of_study not in hypothesis_map:
            hypothesis_map[field_of_study] = {
                "directional": "It is hypothesized that [variable A] influences [variable B] in a positive/negative manner under [conditions].",
                "null": "No relationship exists between [variable A] and [variable B] in the defined context.",
                "causal": "[Factor X] causes [effect Y] through [proposed mechanism].",
                "correlational": "[Variable A] and [Variable B] covary in a predictable direction.",
                "exploratory": "The research will explore unanticipated associations or patterns in the data."
            }

        # Generate the hypothesis string templated with placeholders replaced contextually
        template = hypothesis_map[field_of_study].get(hypothesis_type, hypothesis_map[field_of_study]["directional"])

        # Replace placeholders with actual content from question/context (simplified)
        # Extract key terms: first few words of question
        words = research_question.split()
        if len(words) > 5:
            independent_var = words[0] + " " + words[1] if len(words) > 1 else words[0]
            dependent_var = words[-3] + " " + words[-2] if len(words) > 3 else words[-1]
        else:
            independent_var = words[0] if words else "variable"
            dependent_var = words[-1] if words else "outcome"

        hypothesis_text = template.replace("[independent variable]", independent_var)
        hypothesis_text = hypothesis_text.replace("[dependent variable]", dependent_var)
        hypothesis_text = hypothesis_text.replace("[variable A]", independent_var)
        hypothesis_text = hypothesis_text.replace("[variable B]", dependent_var)
        hypothesis_text = hypothesis_text.replace("[outcome]", dependent_var)
        hypothesis_text = hypothesis_text.replace("[treatment]", independent_var)
        hypothesis_text = hypothesis_text.replace("[condition A]", "experimental condition")
        hypothesis_text = hypothesis_text.replace("[condition B]", "control condition")
        hypothesis_text = hypothesis_text.replace("[variable]", independent_var)
        hypothesis_text = hypothesis_text.replace("[parameter]", "the measured parameter")
        hypothesis_text = hypothesis_text.replace("[mechanism]", "a proposed biological mechanism")
        hypothesis_text = hypothesis_text.replace("[physical principle]", "known physical laws")
        hypothesis_text = hypothesis_text.replace("[physiological change]", "physiological change")
        hypothesis_text = hypothesis_text.replace("[biological mechanism]", "biological mechanism")
        hypothesis_text = hypothesis_text.replace("[theory]", "relevant theory")
        hypothesis_text = hypothesis_text.replace("[cognitive measure]", "performance")
        hypothesis_text = hypothesis_text.replace("[behavioral outcome]", "behavior")
        hypothesis_text = hypothesis_text.replace("[neural pathway]", "neural pathway")
        hypothesis_text = hypothesis_text.replace("[stimulus]", "stimulus")
        hypothesis_text = hypothesis_text.replace("[response]", "response")
        hypothesis_text = hypothesis_text.replace("[pollutant]", "specific pollutant")
        hypothesis_text = hypothesis_text.replace("[species diversity]", "biodiversity")
        hypothesis_text = hypothesis_text.replace("[ecosystem metric]", "ecosystem health")
        hypothesis_text = hypothesis_text.replace("[ecosystem response]", "ecosystem response")
        hypothesis_text = hypothesis_text.replace("[environmental variable]", "environmental variable")
        hypothesis_text = hypothesis_text.replace("[temperature anomaly]", "temperature anomaly")
        hypothesis_text = hypothesis_text.replace("[ice melt rate]", "ice melt rate")
        hypothesis_text = hypothesis_text.replace("[clinical endpoint]", "primary clinical outcome")
        hypothesis_text = hypothesis_text.replace("[biomarker]", "biomarker")
        hypothesis_text = hypothesis_text.replace("[disease]", "the disease of interest")
        hypothesis_text = hypothesis_text.replace("[drug]", "the candidate drug")
        hypothesis_text = hypothesis_text.replace("[measure A]", "variable A")
        hypothesis_text = hypothesis_text.replace("[measure B]", "variable B")
        hypothesis_text = hypothesis_text.replace("[factor]", "factor")
        hypothesis_text = hypothesis_text.replace("[factors]", "multiple factors")
        hypothesis_text = hypothesis_text.replace("[conditions]", "controlled conditions")
        hypothesis_text = hypothesis_text.replace("[proposed causal pathway]", "a proposed causal pathway")
        hypothesis_text = hypothesis_text.replace("[causal pathway]", "causal pathway")
        hypothesis_text = hypothesis_text.replace("[phenomenon]", "the phenomenon")
        hypothesis_text = hypothesis_text.replace("[amount]", "a measurable amount")
        hypothesis_text = hypothesis_text.replace("[constant]", "a constant")
        hypothesis_text = hypothesis_text.replace("[factor X]", independent_var)
        hypothesis_text = hypothesis_text.replace("[effect Y]", dependent_var)
        hypothesis_text = hypothesis_text.replace("[Factor X]", independent_var.capitalize())
        hypothesis_text = hypothesis_text.replace("[Effect Y]", dependent_var.capitalize())
        hypothesis_text = hypothesis_text.replace("[Variable A]", independent_var)
        hypothesis_text = hypothesis_text.replace("[Variable B]", dependent_var)
        hypothesis_text = hypothesis_text.replace("[X]", independent_var)
        hypothesis_text = hypothesis_text.replace("[Y]", dependent_var)

        # Build result
        result = {
            "hypothesis": hypothesis_text,
            "rationale": f"Based on the research question '{research_question}' in the field of {field_of_study}, the hypothesis predicts a {hypothesis_type} relationship. " + (f"Contextual background: {background_context[:200]}..." if len(background_context) > 0 else ""),
            "field": field_of_study,
            "type": hypothesis_type
        }

        if include_design:
            result["suggested_experimental_design"] = f"A controlled experiment with randomized groups comparing {independent_var} and measuring {dependent_var} is recommended. Sample size calculation, blinding, and proper controls should be implemented to ensure validity."

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to generate hypothesis: {str(e)}"}, ensure_ascii=False)


TOOL_SPEC = {
    "name": "generate_hypothesis",
    "description": "Generate a scientific hypothesis from a research question and context, including a falsifiable prediction, rationale, and suggested experimental approach, used to accelerate research proposal development.",
    "category": "generate",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "research_question": {
            "type": "string",
            "description": "The specific research question to derive a hypothesis from, typically in the form of a question about a relationship or phenomenon.",
            "minLength": 10,
            "maxLength": 500
        },
        "background_context": {
            "type": "string",
            "description": "Optional: Relevant background information, existing theories, or prior findings that should inform the hypothesis. Provide key references or observations.",
            "maxLength": 2000
        },
        "field_of_study": {
            "type": "string",
            "description": "The scientific discipline or field (e.g., 'biology', 'physics', 'psychology', 'environmental science').",
            "enum": [
                "biology",
                "chemistry",
                "physics",
                "psychology",
                "neuroscience",
                "environmental_science",
                "medicine",
                "astronomy",
                "geology",
                "sociology",
                "economics",
                "computer_science",
                "mathematics",
                "engineering",
                "other"
            ]
        },
        "hypothesis_type": {
            "type": "string",
            "description": "Optional: The type of hypothesis to generate, influencing its structure and testability.",
            "enum": [
                "directional",
                "None",
                "causal",
                "correlational",
                "exploratory"
            ],
            "default": "directional"
        },
        "include_experimental_design": {
            "type": "boolean",
            "description": "Optional: Whether to include a brief suggested experimental design alongside the hypothesis.",
            "default": True
        }
    },
    "required": [
        "research_question",
        "field_of_study"
    ]
},
}
