# Plan: Phase 4 - Nutritionist Agent

**Status**: ⏳ Pending
**Created**: 2026-01-26
**Version**: v1

## Objective
Add the second **Specialist Agent**. This confirms the scalability of the architecture (adding new "products" without rewriting the core).

## Tasks

### 1. Nutritionist Agent Service
- [ ] **Agent Setup**
  - **Owner**: ai-engineer
  - Create `app/agents/nutrition/`.
  - Define `NutritionState` (Dietary preferences, Macros).
- [ ] **Data Source**
  - **Owner**: backend-engineer
  - Integrate Food Database API (MyFitnessPal/USDA).

### 2. Integration & Flows
- [ ] **Meal Planning Flow**
  - **Owner**: ai-engineer
  - **Nutritionist**: Generates Weekly Meal Plan.
  - **A2A**: Requests "Add Ingredients to Shopping List" via Exec Coach.
- [ ] **Fitness Synergy**
  - **Owner**: systems-architect
  - **Fitness Coach**: Reports "High Calorie Burn".
  - **Exec Coach**: Forwards info to Nutritionist.
  - **Nutritionist**: Adjusts meal plan (adds carbs).

## Success Criteria
- [ ] Nutritionist successfully receives "Activity Level" updates from the system (via Exec Coach).
- [ ] Nutritionist successfully populates the user's "Shopping List" (in TickTick) via the Exec Coach -> PA pipeline.

## Risks
- **Risk**: Context conflict (Fitness says "Eat less", Nutrition says "Eat more").
- **Mitigation**: Exec Function Coach as the final arbiter/resolver of conflicting advice.
