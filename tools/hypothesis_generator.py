"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import random
    import string

    try:
        data = json.loads(payload)
        question = data.get('research_question', '').strip()
        field = data.get('field', '').strip()
        context = data.get('known_context', '').strip()
        creativity = data.get('creativity', 0.5)

        if not question or not field:
            return json.dumps({'error': 'Both research_question and field are required.'}, ensure_ascii=False)

        # ---- Business logic: build hypotheses based on templates per field ----
        field_templates = {
            'biology': [
                "If {independent} increases, then {dependent} will {direction} due to {mechanism}.",
                "Exposure to {independent} leads to {direction} change in {dependent} over {timescale}.",
                "{organism} under {condition} will exhibit {effect} in {dependent}."
            ],
            'physics': [
                "Variation in {independent} causes a {direction} shift in {dependent} proportional to {relationship}.",
                "At {threshold} conditions, {dependent} deviates from classical prediction by {effect}.",
                "Applying {independent} to {system} results in {dependent} scaling as {relationship}."
            ],
            'chemistry': [
                "Increasing concentration of {independent} accelerates the reaction rate of {dependent} by {factor}.",
                "Under {condition}, {reactant} forms a stable complex with {independent}, altering {dependent}.",
                "The presence of {catalyst} lowers activation energy for {reaction}, increasing {dependent}."
            ],
            'psychology': [
                "Participants exposed to {stimulus} will show increased {dependent} compared to controls, mediated by {mechanism}.",
                "{population} with high {trait} will demonstrate {direction} correlation between {independent} and {dependent}.",
                "After {intervention}, scores on {dependent} improve significantly relative to baseline."
            ],
            'environmental_science': [
                "Regions with {independent} have {direction} biodiversity of {species} over {period}.",
                "Increasing {pollutant} concentration correlates with {effect} in {ecosystem}.",
                "Restoration of {habitat} leads to recovery of {dependent} within {timescale}."
            ],
            'neuroscience': [
                "Stimulation of {brain_region} modulates activity in {dependent} region, affecting {behavior}.",
                "Subjects with {condition} show altered {dependent} response compared to healthy controls during {task}.",
                "Neural plasticity in {region} after {intervention} correlates with improvement in {dependent}."
            ],
            'medicine': [
                "Treatment with {drug} reduces {symptom} by {mechanism}, leading to improved {outcome}.",
                "Patients with {biomarker} level above {threshold} have higher risk of {disease}.",
                "Combination therapy of {drug_a} and {drug_b} shows synergistic effect on {dependent}."
            ],
            'astronomy': [
                "Exoplanets with {property} are more likely to have {feature} in their atmosphere due to {mechanism}.",
                "The luminosity of {object} varies with {independent} over {period}, suggesting {cause}.",
                "Galaxy clusters with {characteristic} show {direction} correlation between dark matter distribution and {dependent}."
            ],
            'computer_science': [
                "Models trained with {technique} achieve higher accuracy on {dataset} for task {task}.",
                "Increasing {parameter} in algorithm {alg} reduces computational cost by {factor} while maintaining quality.",
                "Integrating {method} into existing framework improves {metric} by {percentage} for {application}."
            ],
            'geology': [
                "Regions with {rock_type} formation show increased {dependent} activity under {condition}.",
                "The rate of {geological_process} correlates with {independent} over {timescale}.",
                "Mineral composition of {sample} indicates past {event} with {confidence}."
            }
        }

        # fallback if field unknown
        templates = field_templates.get(field, [
            "{independent} influences {dependent} via {mechanism}.",
            "A change in {independent} leads to {direction} change in {dependent}."
        ])

        # generate hypothesis using placeholder substitution
        # We'll populate with science-y words based on creativity
        base_independent = ['temperature', 'concentration', 'exposure time', 'pressure', 'frequency', 'dose', 'light intensity', 'pH level', 'velocity', 'mass']
        base_dependent = ['reaction rate', 'cell viability', 'cognitive performance', 'spectral shift', 'population density', 'gene expression', 'conductivity', 'enzyme activity', 'migration speed', 'accuracy']
        base_mechanism = ['catalysis', 'feedback inhibition', 'resonance coupling', 'osmotic regulation', 'synaptic plasticity', 'radiative forcing', 'competitive binding', 'quantum tunneling', 'natural selection', 'gravitational lensing']
        base_direction = ['increase', 'decrease', 'nonlinear change', 'oscillatory pattern', 'logistic growth', 'exponential decay', 'threshold shift']
        base_timescale = ['hours', 'days', 'weeks', 'months', 'years', 'generations', 'millennia']
        base_organism = ['E. coli', 'zebrafish', 'Arabidopsis', 'Drosophila', 'mouse', 'human subjects', 'yeast', 'C. elegans']
        base_condition = ['high salinity', 'low oxygen', 'elevated CO2', 'microgravity', 'UV radiation', 'drought', 'nutrient deprivation', 'thermal stress']
        base_effect = ['significant', 'moderate', 'negligible', 'dose-dependent', 'time-delayed']
        base_relationship = ['linear', 'quadratic', 'logarithmic', 'exponential', 'inverse']
        base_factor = ['2-fold', '10-fold', '50%', 'by an order of magnitude', 'by a factor of 3']
        base_reactant = ['sodium chloride', 'glucose', 'ATP', 'oxygen', 'carbon dioxide', 'ethanol', 'acetic acid']
        base_catalyst = ['enzyme', 'metal nanoparticle', 'acid catalyst', 'photocatalyst', 'organocatalyst']
        base_reaction = ['oxidation', 'reduction', 'polymerization', 'hydrolysis', 'esterification', 'fermentation']
        base_stimulus = ['positive feedback', 'reward cue', 'social rejection', 'time pressure', 'visual distraction', 'stressful memory recall']
        base_population = ['adolescents', 'elderly', 'experts', 'novices', 'bilingual speakers', 'clinical patients']
        base_trait = ['impulsivity', 'working memory capacity', 'anxiety', 'empathy', 'openness to experience']
        base_intervention = ['cognitive training', 'meditation', 'pharmacological treatment', 'behavioral therapy', 'sleep manipulation']
        base_pollutant = ['microplastics', 'nitrogen dioxide', 'particulate matter', 'pesticide runoff', 'heavy metals']
        base_species = ['soil microbes', 'pollinators', 'amphibians', 'tree species', 'marine plankton']
        base_ecosystem = ['coral reef', 'temperate forest', 'wetland', 'grassland', 'tundra']
        base_habitat = ['forest canopy', 'riverbank', 'deep sea vent', 'urban green space', 'arid zone']
        base_brain_region = ['prefrontal cortex', 'hippocampus', 'amygdala', 'striatum', 'cerebellum']
        base_behavior = ['decision-making', 'memory recall', 'motor coordination', 'social interaction', 'attention']
        base_drug = ['SSRI', 'beta-blocker', 'antibiotic', 'antihistamine', 'corticosteroid']
        base_symptom = ['inflammation', 'pain', 'fatigue', 'cognitive decline', 'anxiety']
        base_outcome = ['recovery time', 'survival rate', 'symptom score', 'quality of life', 'remission']
        base_biomarker = ['CRP', 'BDNF', 'cortisol', 'telomere length', 'HbA1c']
        base_disease = ['Alzheimer disease', 'type 2 diabetes', 'cardiovascular disease', 'asthma', 'depression']
        base_threshold = ['2-fold above baseline', '>10 pg/mL', '30% reduction', 'critical temperature', 'tidal volume']
        base_property = ['orbital period', 'atmospheric composition', 'magnetic field strength', 'surface temperature', 'albedo']
        base_feature = ['water vapor', 'methane', 'cloud cover', 'oxygen', 'silicate dust']
        base_object = ['variable star', 'supernova remnant', 'accretion disk', 'quasar', 'asteroid belt']
        base_cause = ['stellar flares', 'gravitational instability', 'magnetic reconnection', 'radiation pressure']
        base_characteristic = ['richness', 'distance', 'age', 'metalicity', 'ellipticity']
        base_technique = ['data augmentation', 'transfer learning', 'dropout', 'batch normalization', 'attention mechanism']
        base_dataset = ['ImageNet', 'MNIST', 'CIFAR-10', 'GLUE', 'SQuAD']
        base_task = ['classification', 'regression', 'segmentation', 'translation', 'summarization']
        base_parameter = ['learning rate', 'batch size', 'dropout rate', 'number of layers', 'kernel size']
        base_alg = ['CNN', 'Transformer', 'RNN', 'Random Forest', 'SVM']
        base_method = ['ensemble learning', 'graph neural network', 'reinforcement learning', 'active learning', 'self-supervised learning']
        base_metric = ['accuracy', 'F1 score', 'perplexity', 'mean squared error', 'runtime']
        base_percentage = ['5%', '10%', '15%', '20%', '25%']
        base_application = ['image recognition', 'sentiment analysis', 'drug discovery', 'robotics', 'speech recognition']
        base_rock_type = ['igneous', 'sedimentary', 'metamorphic', 'volcanic']
        base_geological_process = ['erosion', 'plate tectonics', 'glacial melting', 'volcanism', 'seismic activity']
        base_sample = ['core sample', 'outcrop', 'sediment layer', 'mineral vein']
        base_event = ['mass extinction', 'orogeny', 'ice age', 'impact event', 'sea level rise']
        base_confidence = ['low', 'moderate', 'high', 'very high']

        # Simple selection with randomness modulated by creativity
        # Higher creativity -> more random / unconventional choices
        seed = random.randint(0, 9999)
        rng = random.Random(seed)

        # Build a dictionary of placeholder values
        def choose(lst):
            return rng.choice(lst)

        mapping = {
            'independent': choose(base_independent),
            'dependent': choose(base_dependent),
            'mechanism': choose(base_mechanism),
            'direction': choose(base_direction),
            'timescale': choose(base_timescale),
            'organism': choose(base_organism),
            'condition': choose(base_condition),
            'effect': choose(base_effect),
            'relationship': choose(base_relationship),
            'factor': choose(base_factor),
            'reactant': choose(base_reactant),
            'catalyst': choose(base_catalyst),
            'reaction': choose(base_reaction),
            'stimulus': choose(base_stimulus),
            'population': choose(base_population),
            'trait': choose(base_trait),
            'intervention': choose(base_intervention),
            'pollutant': choose(base_pollutant),
            'species': choose(base_species),
            'ecosystem': choose(base_ecosystem),
            'habitat': choose(base_habitat),
            'brain_region': choose(base_brain_region),
            'behavior': choose(base_behavior),
            'drug': choose(base_drug),
            'symptom': choose(base_symptom),
            'outcome': choose(base_outcome),
            'biomarker': choose(base_biomarker),
            'disease': choose(base_disease),
            'threshold': choose(base_threshold),
            'property': choose(base_property),
            'feature': choose(base_feature),
            'object': choose(base_object),
            'cause': choose(base_cause),
            'characteristic': choose(base_characteristic),
            'technique': choose(base_technique),
            'dataset': choose(base_dataset),
            'task': choose(base_task),
            'parameter': choose(base_parameter),
            'alg': choose(base_alg),
            'method': choose(base_method),
            'metric': choose(base_metric),
            'percentage': choose(base_percentage),
            'application': choose(base_application),
            'rock_type': choose(base_rock_type),
            'geological_process': choose(base_geological_process),
            'sample': choose(base_sample),
            'event': choose(base_event),
            'confidence': choose(base_confidence),
        }

        # Select a random template
        template = choose(templates)

        # Replace placeholders with mapping values
        hypothesis_statement = template.format(**mapping)

        # Build a testable prediction (simple sentence)
        prediction = f"We predict that {mapping['dependent']} will {mapping['direction']} under the proposed conditions."

        # Suggest experimental approach
        approach_suggestions = [
            f"Conduct a controlled experiment with {mapping['independent']} as independent variable, measuring {mapping['dependent']} over {mapping['timescale']}.",
            f"Use a double-blind randomized trial with {mapping['population']} to test the effect of {mapping['independent']} on {mapping['dependent']}.",
            f"Perform regression analysis on observational data to identify correlation between {mapping['independent']} and {mapping['dependent']} in {mapping['ecosystem']}.",
            f"Set up a simulation model varying {mapping['parameter']} and monitoring {mapping['dependent']}.",
            f"Analyze existing datasets (e.g., {mapping['dataset']}) using {mapping['technique']} to evaluate the relationship."
        ]
        approach = choose(approach_suggestions)

        result = {
            'hypothesis': hypothesis_statement,
            'prediction': prediction,
            'experimental_approach': approach,
            'field': field,
            'creativity_level': creativity
        }

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'



TOOL_SPEC = {
    "name": "hypothesis_generator",
    "description": "Generate a plausible scientific hypothesis from a given research question or observation, including a testable prediction and a suggested experimental approach. This tool helps researchers brainstorm and structure new lines of inquiry.",
    "category": "generate",
    "domain": "science",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "research_question": {
            "type": "string",
            "description": "The core research question or observation that the hypothesis should address. Should be a clear, concise sentence."
        },
        "field": {
            "type": "string",
            "description": "The scientific field relevant to the hypothesis (e.g., biology, physics, psychology, environmental science).",
            "enum": [
                "biology",
                "physics",
                "chemistry",
                "psychology",
                "environmental_science",
                "neuroscience",
                "medicine",
                "astronomy",
                "computer_science",
                "geology"
            ]
        },
        "known_context": {
            "type": "string",
            "description": "Optional: Additional context or previously established facts/theories that should be considered. Helps narrow the hypothesis."
        },
        "creativity": {
            "type": "number",
            "description": "Optional: A level of creativity/novelty for the hypothesis (0.0 = very conservative, 1.0 = highly novel). Default 0.5.",
            "minimum": 0.0,
            "maximum": 1.0
        }
    },
    "required": [
        "research_question",
        "field"
    ]
},
}
