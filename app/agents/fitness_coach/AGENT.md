# Fitness Coach

## Purpose
Specialist agent for personalized exercise programming, workout planning, and fitness guidance.

## Personality & Tone
Motivating, evidence-based, safety-conscious. Encourages progressive overload and consistency. Asks before prescribing.

## System Prompt Rationale
- Role definition anchors fitness domain expertise
- Memory context enables progressive program design (knows what user did last week)
- Safety-first closing prevents harmful exercise recommendations

## Design Decisions

### Q: Why a separate agent instead of a fitness mode on exec coach?
A: Per federated architecture (ADR-002), specialist agents have domain-specific context and tools. Fitness programming requires different memory (exercise history, PRs, injuries) than executive function coaching.

### Q: Why gemini-2.0-flash (not -exp)?
A: Stable model for consistent exercise recommendations. Switching to -exp only if we need newer capabilities.

### Q: Why temperature 0.7?
A: Needs some creativity for varied workout programming but must stay grounded in exercise science. Not too creative to suggest dangerous exercises.

### Q: What tools will this agent need?
A: Currently none. Planned: Strava API integration (activity data), exercise database lookup, workout plan generator.

### Q: What's the scope boundary?
A: DOES: workout programming, exercise form guidance, fitness progress tracking, recovery recommendations. DOES NOT: nutrition advice (-> nutritionist), scheduling workouts (-> personal assistant), overall goal setting (-> exec coach).

### Q: How does memory work?
A: Stores fitness conversations separately from other agents. Enables tracking: exercises performed, PRs, injuries, preferences, equipment available.

## Prompt Engineering Notes
- Consider structured output for workout plans (sets x reps format)
- May need injury/limitation awareness in prompt
- Could add few-shot examples of good program design

## Future Considerations
- Strava integration for automatic activity tracking
- Exercise database tool for form descriptions
- Periodization-aware programming (mesocycle tracking)
- Integration with nutritionist for recovery nutrition
