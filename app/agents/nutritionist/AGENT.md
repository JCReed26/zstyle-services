# Nutritionist

## Purpose
Specialist agent for personalized meal planning, dietary guidance, and nutritional education.

## Personality & Tone
Informative, non-judgmental, practical. Focuses on sustainable habits over restriction. Asks before recommending.

## System Prompt Rationale
- Role definition anchors nutrition domain expertise
- Memory context enables tracking dietary patterns, allergies, and preferences over time
- Non-judgmental closing prevents shaming language around food choices

## Design Decisions

### Q: Why a separate agent instead of a nutrition mode on exec coach?
A: Per federated architecture (ADR-002), nutrition requires domain-specific memory (dietary restrictions, allergies, meal history, macro targets) that would pollute the exec coach's context.

### Q: Why gemini-2.0-flash?
A: Stable model for consistent dietary recommendations. Nutrition advice must be reliable — not experimental.

### Q: Why temperature 0.7?
A: Needs creativity for varied meal suggestions but must stay grounded in nutritional science. Too high risks recommending harmful dietary practices.

### Q: What tools will this agent need?
A: Currently none. Planned: food/nutrition database API, meal plan generator, macro calculator, recipe search.

### Q: What's the scope boundary?
A: DOES: meal planning, macro guidance, recipe suggestions, dietary education, allergy-aware recommendations. DOES NOT: exercise programming (→ fitness coach), grocery scheduling (→ personal assistant), overall lifestyle goals (→ exec coach).

### Q: How does memory work?
A: Stores nutrition conversations separately. Tracks: dietary restrictions, allergies, food preferences, macro targets, meal history.

## Prompt Engineering Notes
- Consider structured output for meal plans (meals per day format)
- May need allergen/restriction awareness prominently in prompt
- Could add few-shot examples of balanced meal recommendations

## Future Considerations
- Food database API integration (USDA, Nutritionix)
- Macro tracking and calculation tools
- Recipe search and suggestion tool
- Integration with fitness coach for performance nutrition
