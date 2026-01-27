---
name: ai-engineer
description: Use the ai-engineer sub-agent when building LangChain agents, integrating LLMs, or working on AI features. Activates when user needs agent development, LLM integration, or AI system design.
---

# AI Engineer Skill

## When to Use

Activate the ai-engineer sub-agent when:

- User asks for LangChain or LangGraph agents
- Need to integrate with LLM providers
- Working on AI-powered features
- User mentions "agent", "LLM", "LangChain", "LangGraph", or "AI"
- Need to design multi-agent systems

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/ai-engineer/SUBAGENT.md`
2. **Discover context**: 
   - Check `docs/working/research/` for agent research
   - Check `docs/contracts/agents/` for agent contracts
   - Check `docs/working/error-logs.md` for agent errors
   - Use semantic search to find related agent code
3. **Research patterns**: Look for LangChain/LangGraph examples
4. **Follow TDD**: Write tests for agents (use `tdd-langchain` command)
5. **Design tools**: Create focused, reliable tools
6. **Handle errors**: Implement robust error handling
7. **Update contracts**: Update agent contracts when interfaces change

## Example Usage

**User**: "Create a LangChain agent that can search and analyze"

**Response**:
1. Research LangChain patterns
2. Design agent architecture
3. Define tools needed
4. Create agent with LangChain
5. Write tests
6. Handle errors

## Key Capabilities

- LangChain agent development
- LangGraph state management
- LLM integration
- Tool development
- Prompt engineering
