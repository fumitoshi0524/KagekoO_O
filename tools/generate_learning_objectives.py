"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random

    try:
        data = json.loads(payload)
        
        # Validate required fields
        required_fields = ['topic', 'audience_level', 'cognitive_level']
        for field in required_fields:
            if field not in data:
                return f'error: missing required field "{field}"'
        
        topic = data['topic']
        audience = data['audience_level']
        cognitive = data['cognitive_level']
        num = min(max(data.get('num_objectives', 5), 1), 10)
        subject = data.get('subject_area', 'general')
        
        # Bloom's taxonomy verb sets by cognitive level and audience
        verb_sets = {
            'remember': {
                'elementary': ['recall', 'list', 'identify', 'name', 'recognize'],
                'middle_school': ['recall', 'define', 'list', 'identify', 'name', 'label'],
                'high_school': ['recall', 'define', 'identify', 'state', 'list', 'describe'],
                'undergraduate': ['define', 'identify', 'recall', 'list', 'state', 'recognize'],
                'graduate': ['define', 'identify', 'recall', 'articulate', 'specify', 'enumerate'],
                'professional': ['identify', 'state', 'recall', 'specify', 'define', 'recognize']
            },
            'understand': {
                'elementary': ['explain', 'describe', 'summarize', 'paraphrase', 'give examples of'],
                'middle_school': ['explain', 'describe', 'summarize', 'interpret', 'paraphrase', 'compare'],
                'high_school': ['explain', 'summarize', 'interpret', 'classify', 'compare', 'describe in your own words'],
                'undergraduate': ['explain', 'summarize', 'interpret', 'differentiate', 'classify', 'compare and contrast'],
                'graduate': ['explain', 'synthesize', 'interpret', 'articulate', 'elucidate', 'contextualize'],
                'professional': ['articulate', 'interpret', 'explain', 'contextualize', 'relate', 'describe the significance of']
            },
            'apply': {
                'elementary': ['use', 'demonstrate', 'show', 'solve', 'implement'],
                'middle_school': ['apply', 'demonstrate', 'use', 'solve', 'implement', 'operationalize'],
                'high_school': ['apply', 'use', 'solve', 'demonstrate', 'calculate', 'implement', 'carry out'],
                'undergraduate': ['apply', 'use', 'solve', 'implement', 'execute', 'operationalize', 'calculate'],
                'graduate': ['apply', 'implement', 'operationalize', 'execute', 'utilize', 'carry out'],
                'professional': ['apply', 'implement', 'operationalize', 'execute', 'utilize', 'demonstrate proficiency in']
            },
            'analyze': {
                'elementary': ['compare', 'contrast', 'sort', 'categorize', 'distinguish'],
                'middle_school': ['analyze', 'compare and contrast', 'categorize', 'distinguish', 'examine', 'differentiate'],
                'high_school': ['analyze', 'differentiate', 'distinguish', 'examine', 'compare', 'deconstruct', 'identify relationships'],
                'undergraduate': ['analyze', 'differentiate', 'deconstruct', 'examine', 'distinguish', 'identify patterns', 'critique methodology'],
                'graduate': ['analyze', 'deconstruct', 'critically examine', 'distinguish', 'identify underlying assumptions', 'discern'],
                'professional': ['analyze', 'deconstruct', 'critically evaluate', 'distinguish', 'identify root causes', 'diagnose']
            },
            'evaluate': {
                'elementary': ['judge', 'decide', 'choose', 'rate', 'justify'],
                'middle_school': ['evaluate', 'judge', 'justify', 'defend', 'assess', 'critique', 'support with evidence'],
                'high_school': ['evaluate', 'assess', 'judge', 'justify', 'critique', 'defend', 'appraise', 'support with evidence'],
                'undergraduate': ['evaluate', 'assess', 'critique', 'judge', 'defend', 'appraise', 'evaluate the validity of'],
                'graduate': ['evaluate', 'critique', 'assess', 'judge', 'appraise', 'evaluate the soundness of', 'argue'],
                'professional': ['evaluate', 'assess', 'critique', 'appraise', 'judge', 'evaluate the effectiveness of', 'defend a position on']
            },
            'create': {
                'elementary': ['create', 'make', 'design', 'build', 'construct', 'invent'],
                'middle_school': ['create', 'design', 'develop', 'construct', 'produce', 'generate', 'invent'],
                'high_school': ['create', 'design', 'develop', 'construct', 'produce', 'generate', 'formulate', 'devise'],
                'undergraduate': ['create', 'design', 'develop', 'formulate', 'construct', 'produce', 'generate', 'devise'],
                'graduate': ['create', 'design', 'formulate', 'develop', 'generate', 'construct', 'synthesize', 'propose'],
                'professional': ['create', 'design', 'develop', 'formulate', 'generate', 'construct', 'produce', 'devise']
            }
        }
        
        # Objective templates by cognitive level
        templates = {
            'remember': 'By the end of this {audience_label} lesson, learners will be able to {verb} key {topic_noun} such as {detail}.',
            'understand': 'Through this {audience_label} course, learners will be able to {verb} the concept of {topic} in terms of {detail}.',
            'apply': 'After completing this {audience_label} unit, learners will be able to {verb} {topic} concepts to {detail}.',
            'analyze': 'By participating in this {audience_label} module, learners will be able to {verb} the {detail} of {topic}.',
            'evaluate': 'Upon completion of this {audience_label} program, learners will be able to {verb} {detail} related to {topic}.',
            'create': 'As a result of this {audience_label} course, learners will be able to {verb} {detail} that demonstrates understanding of {topic}.'
        }
        
        # Audience label mapping
        audience_labels = {
            'elementary': 'elementary',
            'middle_school': 'middle school',
            'high_school': 'high school',
            'undergraduate': 'undergraduate',
            'graduate': 'graduate-level',
            'professional': 'professional'
        }
        
        # Details by subject and cognitive level (just generating varied outputs)
        subject_details = {
            'science': ['core principles', 'experimental methods', 'theoretical frameworks', 'observational data', 'scientific models'],
            'mathematics': ['mathematical proofs', 'problem-solving strategies', 'theoretical models', 'computational methods', 'algebraic structures'],
            'language_arts': ['literary devices', 'rhetorical strategies', 'narrative structures', 'argumentation frameworks', 'textual analysis'],
            'history': ['historical contexts', 'causal relationships', 'primary sources', 'interpretive frameworks', 'chronological patterns'],
            'arts': ['creative techniques', 'aesthetic principles', 'compositional elements', 'expressive methods', 'artistic traditions'],
            'technology': ['technical architectures', 'computational processes', 'system designs', 'implementation patterns', 'algorithmic approaches'],
            'business': ['business models', 'market dynamics', 'organizational structures', 'strategic frameworks', 'financial concepts'],
            'health': ['health outcomes', 'physiological processes', 'clinical assessments', 'preventive strategies', 'therapeutic approaches'],
            'general': ['core concepts', 'foundational principles', 'key frameworks', 'primary theories', 'essential methods']
        }
        
        # Ensure we have verbs for the given cognitive level and audience
        level_verbs = verb_sets.get(cognitive, verb_sets['remember'])
        audience_verbs = level_verbs.get(audience, level_verbs['undergraduate'])
        
        if not audience_verbs:
            audience_verbs = ['identify', 'describe', 'explain']
        
        template = templates.get(cognitive, templates['remember'])
        aud_label = audience_labels.get(audience, 'educational')
        details = subject_details.get(subject, subject_details['general'])
        
        # Generate objectives
        objectives = []
        used_details = []
        for i in range(num):
            verb = random.choice(audience_verbs)
            # Pick a detail that hasn't been used recently if possible
            available = [d for d in details if d not in used_details[-3:]]
            if not available:
                available = details
            detail = random.choice(available)
            used_details.append(detail)
            
            objective_text = template.format(
                audience_label=aud_label,
                verb=verb,
                topic=topic,
                topic_noun=topic,
                detail=detail
            )
            objectives.append(objective_text)
        
        # Build result
        result = {
            'topic': topic,
            'audience_level': audience,
            'cognitive_level': cognitive,
            'num_objectives': len(objectives),
            'learning_objectives': objectives,
            'metadata': {
                'blooms_level': cognitive,
                'target_audience': aud_label,
                'subject_area': subject
            }
        }
        
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "generate_learning_objectives",
    "description": "Generate measurable, competency-based learning objectives for a given educational topic, target audience, and cognitive level according to Bloom's Taxonomy, returning a set of actionable objectives in structured format.",
    "category": "generate",
    "domain": "education",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "The educational topic for which learning objectives will be generated (e.g., 'Photosynthesis', 'Quadratic Equations', 'World War II')"
        },
        "audience_level": {
            "type": "string",
            "enum": [
                "elementary",
                "middle_school",
                "high_school",
                "undergraduate",
                "graduate",
                "professional"
            ],
            "description": "Target audience educational level for appropriate complexity and language"
        },
        "cognitive_level": {
            "type": "string",
            "enum": [
                "remember",
                "understand",
                "apply",
                "analyze",
                "evaluate",
                "create"
            ],
            "description": "Highest cognitive level according to Bloom's Taxonomy for the objectives"
        },
        "num_objectives": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "default": 5,
            "description": "Optional: Number of learning objectives to generate (default 5)"
        },
        "subject_area": {
            "type": "string",
            "enum": [
                "science",
                "mathematics",
                "language_arts",
                "history",
                "arts",
                "technology",
                "business",
                "health"
            ],
            "description": "Optional: Subject area to ensure domain-appropriate terminology and frameworks"
        }
    },
    "required": [
        "topic",
        "audience_level",
        "cognitive_level"
    ]
},
}
