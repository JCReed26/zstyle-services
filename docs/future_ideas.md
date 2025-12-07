# Agent Ideas

Collection of potential AI agents for the ZStyle platform

## Executive Function Coach (Current)
- Current implementation focused on calendar management
- Integrates with Google Calendar
- Helps with scheduling and organization

## Workflows 

Automations at certain times of the day to complete certain tasks

Routines: 
- morning_routine -> maps to new telegram chat sessions for each day to handle context. 
- evening_routine -> ensure inbox 0 at the end of the day type of thing. 

Automations:
- lunch-newsupdate - ???

## Potential Future Agents

- personal-trainer-agent (strava, apple fitness, )
- nutrition-agent -> (is meal planner, dietitian, chooses safe foods, factor, meal kits)
- accountant-agent -> handle finances and books the basics (sofi, everydollar!!!, etc)
- knowledge-student-assistant -> canvas, coursera, duolingo, masterclass, boaters course, drivers ed. (included online and actual practice with test checks for personal measurements)   

- goal-agent -> helps you set track and reach goals faster
- news-agent -> news summarized, based on your interests
- lawyer-agent -> basic legal questions and where to go for help if needed (ai representation on road laws, etc.)
- doctor-agent -> basic medical questions and where to go for help if needed (quick replies and when to know if I need a real doctor)
- fashion-agent -> clothes shopping but constantly looking for deals, helping with fits, wardrobe management (can have database of closet images to create outfit combinations based upon stored pictures of user to see what you would look like each day, like wakeup say its cold what could I wear and get outfit options that fit your style)
- curated-content-agent -> curate and collect the content you want to sort through unwanted fyp marketing (podcasts, spotify, youtube, tiktok)
- phone-addition-agent -> (could be ios only) will mess with your phone to lock it, block apps, and get you unaddicted from your phone (this is ZSTYLE experience life)

for when mobile-app if ever:
- circles-agent -> can directly interact with circles feature to help users make more friends and do more things in their area



## Implementation Considerations

### Common Services Needed
- Authentication (OAuth 2.0)
- Memory storage for context
- Calendar integration
- Notification systems
- File/attachment handling

### MCP Integrations to Consider
- Email clients
- Calendar services
- Task management tools (Todoist, TickTick, etc.)
- Home automation systems
- Health tracking apps