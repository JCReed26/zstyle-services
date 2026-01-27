---
name: docker-engineer
description: Use the docker-engineer sub-agent when creating Dockerfiles, managing docker-compose.yml, or working with containers. Activates when user needs containerization, Docker configuration, or deployment setup.
---

# Docker Engineer Skill

## When to Use

Activate the docker-engineer sub-agent when:

- User asks for Dockerfile or container setup
- Need to configure docker-compose.yml
- Working on containerization
- User mentions "Docker", "containers", "docker-compose", or "containerization"
- Need to optimize container images

## How to Use

1. **Read the sub-agent definition**: `.cursor/agents/docker-engineer/SUBAGENT.md`
2. **Discover context**: 
   - Check `docs/working/plans/` for deployment plans
   - Check existing Dockerfiles for patterns
   - Check `docs/working/error-logs.md` for container issues
3. **Follow best practices**: Use multi-stage builds, security patterns
4. **Optimize**: Keep images small and build times fast
5. **Test**: Test builds and container runs
6. **Document**: Document container requirements
7. **Update plans**: Update deployment plans with container decisions

## Example Usage

**User**: "Create a Dockerfile for the FastAPI app"

**Response**:
1. Analyze app requirements
2. Choose base image
3. Create optimized Dockerfile
4. Add health checks
5. Configure for production
6. Test build

## Key Capabilities

- Dockerfile creation
- Docker Compose orchestration
- Image optimization
- Container security
- Environment management
