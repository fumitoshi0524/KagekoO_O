"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    """Generate a personalized list of actionable, eco-friendly habits for a user."""
    import json
    import random
    try:
        data = json.loads(payload)
        lifestyle = data.get('lifestyle_category')
        routine = data.get('daily_routine')
        goal = data.get('environmental_goal')
        count = data.get('habit_count', 5)
        if not lifestyle or not routine or not goal:
            return json.dumps({'error': 'Missing required parameters: lifestyle_category, daily_routine, environmental_goal'}, ensure_ascii=False)
        # Habit templates by lifestyle and goal
        habit_templates = {
            'urban_apartment': {
                'reduce_carbon_footprint': ['Use public transit or bike for commutes under 5 km', 'Switch to a renewable energy provider for electricity', 'Unplug electronics when not in use to avoid phantom energy', 'Choose second-hand or refurbished electronics', 'Participate in a local car-sharing program'],
                'minimize_waste': ['Start a countertop compost bin for food scraps', 'Refuse single-use plastics when ordering takeout', 'Use reusable grocery bags and produce bags', 'Buy in bulk using your own containers', 'Repair clothes instead of discarding them'],
                'conserve_water': ['Install low-flow showerheads and faucet aerators', 'Collect cold water while waiting for hot to water plants', 'Fix leaky taps immediately', 'Take shorter showers (5 minutes timer)', 'Use a broom instead of a hose to clean balconies'],
                'save_energy': ['Use LED bulbs throughout the apartment', 'Set thermostat to 18°C in winter and 25°C in summer', 'Air-dry laundry instead of using a dryer', 'Use a smart power strip for entertainment systems', 'Cook with lids on pots to reduce heat loss'],
                'sustainable_food': ['Plan meals weekly to reduce food waste', 'Buy seasonal and local produce from farmers markets', 'Reduce meat consumption to 3 times per week', 'Start a windowsill herb garden', 'Freeze leftovers for future meals'],
                'general_eco_friendly': ['Join a community garden or balcony planting', 'Use a menstrual cup or reusable pads', 'Switch to bar soap and shampoo bars', 'Walk or bike for errands under 2 km', 'Adopt one new green habit each month']
            },
            'suburban_house': {
                'reduce_carbon_footprint': ['Install solar panels on the roof', 'Replace lawn with native drought-resistant plants', 'Carpool with neighbors for school or work runs', 'Use an electric or push lawnmower', 'Install a rain barrel for garden watering'],
                'minimize_waste': ['Set up a three-bin compost system (greens, browns, soil)', 'Repurpose glass jars for storage', 'Host a neighborhood swap meet for unused items', 'Use cloth napkins and towels instead of paper', 'Make household cleaners from vinegar and baking soda'],
                'conserve_water': ['Install a greywater system for garden irrigation', 'Mulch garden beds to retain moisture', 'Water plants early morning or late evening to reduce evaporation', 'Fix dripping outdoor taps', 'Use a drip irrigation system for vegetable beds'],
                'save_energy': ['Add attic insulation to reduce heating/cooling needs', 'Install a programmable thermostat', 'Replace old windows with double-glazing', 'Use ceiling fans instead of air conditioning when possible', 'Insulate water heater pipes'],
                'sustainable_food': ['Grow a vegetable garden with seasonal crops', 'Preserve excess harvest by canning or freezing', 'Raise backyard chickens for eggs', 'Cook from scratch using garden produce', 'Compost kitchen scraps to enrich garden soil'],
                'general_eco_friendly': ['Create a wildlife habitat in the yard', 'Use non-toxic pest control methods', 'Install a clothesline for outdoor drying', 'Choose pet products made from recycled materials', 'Participate in local environmental clean-up days']
            },
            'rural_home': {
                'reduce_carbon_footprint': ['Use a wood-burning stove from sustainably harvested wood', 'Drive fuel-efficient or electric vehicle for long distances', 'Generate electricity with small wind turbine', 'Use animal traction for small farm tasks', 'Preserve natural forest areas on property'],
                'minimize_waste': ['Practice rotational grazing to improve soil', 'Make your own hay bale gardening', 'Use natural fibers for crafts', 'Repurpose machinery parts for furniture', 'Implement a zero-waste homesteading system'],
                'conserve_water': ['Harvest rainwater from roof runoff', 'Use swales and keyline design for water retention', 'Install a pond for wildlife and irrigation', 'Use greywater for fruit trees', 'Mulch around trees to reduce water loss'],
                'save_energy': ['Build with passive solar design principles', 'Use geothermal heat pump for heating', 'Insulate barns and outbuildings', 'Install high-efficiency wood pellet boiler', 'Use solar-powered outdoor lighting'],
                'sustainable_food': ['Practice permaculture food forest design', 'Raise heritage breed livestock for genetic diversity', 'Save seeds from open-pollinated plants', 'Ferment vegetables for long-term storage', 'Tap maple trees for syrup'],
                'general_eco_friendly': ['Maintain hedgerows for biodiversity', 'Use natural predators for pest control', 'Build with local sustainable materials', 'Host farm-to-table events for community', 'Manage forest for carbon sequestration']
            },
            'office_worker': {
                'reduce_carbon_footprint': ['Telecommute one day per week if feasible', 'Take public transit or bike to work', 'Bring a reusable lunch container', 'Use stairs instead of elevators', 'Offset work-related travel emissions'],
                'minimize_waste': ['Go paperless and use digital notes', 'Bring a reusable coffee cup to the office', 'Use refillable pens and recycled paper', 'Set up a office recycling station', 'Print double-sided and in grayscale'],
                'conserve_water': ['Bring a reusable water bottle', 'Report leaky faucets in office bathrooms', 'Encourage office to install water-efficient fixtures', 'Use a drip coffee maker instead of single-serve pods', 'Take shorter breaks to reduce water use'],
                'save_energy': ['Turn off computer monitor when away', 'Use natural light instead of desk lamps', 'Unplug chargers when not in use', 'Set computer to sleep after 10 minutes', 'Use a laptop instead of desktop for lower energy'],
                'sustainable_food': ['Pack lunch with leftovers from dinner', 'Choose vegetarian options in cafeteria', 'Bring own cutlery and napkin', 'Buy coffee from fair-trade and organic sources', 'Snack on fruits and nuts instead of packaged goods'],
                'general_eco_friendly': ['Join office green team', 'Suggest green office policies', 'Use green search engine Ecosia', 'Start a office plant initiative', 'Celebrate Earth Day with team activities']
            },
            'student_dormitory': {
                'reduce_carbon_footprint': ['Walk or cycle to campus', 'Share textbooks with classmates', 'Use digital textbooks and notes', 'Participate in campus car-sharing', 'Vote for sustainable campus initiatives'],
                'minimize_waste': ['Use a reusable water bottle and coffee mug', 'Avoid individually packaged snacks', 'Recycle plastic bottles and paper', 'Use cloth bags for laundry', 'Start a dorm recycling competition'],
                'conserve_water': ['Take shorter showers (5 minutes)', 'Turn off tap while brushing teeth', 'Report leaking faucets to maintenance', 'Use bucket to collect shower water for flushing', 'Wash clothes only when full load'],
                'save_energy': ['Unplug electronics when not in use', 'Use LED desk lamp', 'Turn off lights when leaving room', 'Minimize use of space heater', 'Use power strip to turn off multiple devices'],
                'sustainable_food': ['Cook simple meals in bulk', 'Buy in bulk from co-op grocery', 'Use own containers for takeout', 'Reduce food waste by sharing with roommates', 'Choose plant-based meals occasionally'],
                'general_eco_friendly': ['Join environmental student club', 'Organize campus clean-up events', 'Start a dorm garden on windowsill', 'Rent or borrow instead of buying new', 'Educate friends about eco-habits']
            },
            'frequent_traveler': {
                'reduce_carbon_footprint': ['Choose direct flights to reduce fuel burn', 'Offset flight emissions via certified programs', 'Travel by train or bus for short distances', 'Pack light to reduce plane weight', 'Stay in eco-certified accommodations'],
                'minimize_waste': ['Carry a reusable water bottle with filter', 'Bring collapsible utensils and straw', 'Refuse mini toiletries and use own solid bars', 'Use e-tickets rather than printed', 'Pack a reusable shopping bag'],
                'conserve_water': ['Reuse towels in hotels', 'Take short showers even when traveling', 'Turn off tap while brushing in hotel', 'Choose accommodations with water-saving measures', 'Avoid laundry service until needed'],
                'save_energy': ['Unplug chargers and electronics in hotel', 'Turn off lights and AC when leaving room', 'Use natural ventilation instead of AC if possible', 'Choose hotels with energy certification', 'Stay in hostels or shared economy to reduce energy per person'],
                'sustainable_food': ['Eat at local restaurants serving regional dishes', 'Avoid imported packaged snacks', 'Choose plant-based street food', 'Bring own snack bag to avoid airport junk', 'Visit local markets for fresh produce'],
                'general_eco_friendly': ['Travel with a reusable coffee cup', 'Support local eco-tourism operators', 'Leave no trace when exploring nature', 'Choose souvenirs from local artisans', 'Learn about local environmental issues']
            }
        }
        # Generate habits
        templates = habit_templates.get(lifestyle, habit_templates['urban_apartment']).get(goal, habit_templates['urban_apartment']['general_eco_friendly'])
        # Shuffle and pick 'count' items (or all if count > len)
        random.shuffle(templates)
        selected = templates[:min(count, len(templates))]
        # Build result with estimated impact (simple heuristic based on goal)
        impact_map = {
            'reduce_carbon_footprint': 'High carbon reduction',
            'minimize_waste': 'Moderate waste reduction',
            'conserve_water': 'High water savings',
            'save_energy': 'High energy savings',
            'sustainable_food': 'Moderate dietary impact',
            'general_eco_friendly': 'Varied positive impact'
        }
        habits = [{'habit': h, 'estimated_impact': impact_map[goal]} for h in selected]
        result = {
            'habits': habits,
            'total_suggestions': len(habits),
            'lifestyle': lifestyle,
            'goal': goal,
            'summary': f'Generated {len(habits)} personalized eco-habits for {lifestyle.replace("_", " ")} focusing on {goal.replace("_", " ")}.'
        }
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "sustainable_habit_generator",
    "description": "Generate a personalized list of actionable, eco-friendly habits for a user based on their lifestyle category, daily routine, and environmental goals, returning a structured set of habit suggestions with estimated impact.",
    "category": "generate",
    "domain": "environment",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "lifestyle_category": {
            "type": "string",
            "description": "The user's primary living or working context to tailor habits appropriately",
            "enum": [
                "urban_apartment",
                "suburban_house",
                "rural_home",
                "office_worker",
                "student_dormitory",
                "frequent_traveler"
            ]
        },
        "daily_routine": {
            "type": "string",
            "description": "A brief description of the user's typical day (free text, max 200 characters) to refine habit relevance"
        },
        "environmental_goal": {
            "type": "string",
            "description": "The main environmental focus area the user wants to improve",
            "enum": [
                "reduce_carbon_footprint",
                "minimize_waste",
                "conserve_water",
                "save_energy",
                "sustainable_food",
                "general_eco_friendly"
            ]
        },
        "habit_count": {
            "type": "integer",
            "description": "Optional: number of habit suggestions to generate (between 1 and 10, default 5)",
            "minimum": 1,
            "maximum": 10,
            "default": 5
        }
    },
    "required": [
        "lifestyle_category",
        "daily_routine",
        "environmental_goal"
    ]
},
}
