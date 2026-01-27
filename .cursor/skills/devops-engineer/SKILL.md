---
name: devops-engineer
description: Use the devops-engineer sub-agent when setting up CI/CD pipelines, infrastructure, monitoring, or deployment automation. Activates when user needs DevOps, CI/CD, infrastructure, or deployment work.
---

# DevOps Engineer Skill

## When to Use

Activate the devops-engineer sub-agent when:

- User asks for CI/CD setup or pipelines
- Need infrastructure configuration
- Working on deployment automation
- User mentions "CI/CD", "DevOps", "deployment", "infrastructure", or "monitoring"
- Need to set up logging or metrics

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/devops-engineer/SUBAGENT.md`
2. **Discover context**: 
   - Check `docs/working/plans/` for deployment plans
   - Check `docs/architecture/decisions/` for infrastructure decisions
   - Check `docs/working/error-logs.md` for deployment issues
3. **Design pipeline**: Plan CI/CD stages
4. **Automate**: Automate testing, building, deployment
5. **Monitor**: Set up logging and metrics
6. **Document**: Document deployment processes
7. **Update ADRs**: Document infrastructure decisions in ADRs

## Example Usage

**User**: "Set up CI/CD pipeline"

**Response**:
1. Analyze deployment requirements
2. Create pipeline configuration
3. Set up test stages
4. Configure build and deploy stages
5. Add monitoring
6. Document process

## Key Capabilities

- CI/CD pipeline setup
- Infrastructure as code
- Monitoring and alerting
- Deployment automation
- Reliability engineering
