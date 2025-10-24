# ZStyle Web and Backend Services 
> Note: zstyle-mobile-app is the repository for the mobile app that corresponds with this program  
> Note: terraform is setup to work on MacOS and Linux
> No web frontend yet -- use test endpoint in agents

## QuickStart

1. Setup env variables

  - Rename the `.env.example` file to `.env` and update the values with your own  

  ```bash
  cp .env.example .env
  ```

2. Start docker daemon and run command below

  ```bash
  docker-compose up --build
  ```

  or

  MacOS/Linux:
  ```bash
  ./run_clean.sh
  ```

  Windows:
  ```powershell
  ./run_clean.ps1
  ```

## agents
The zstyle system core. The main agent from the server on main is zstyle. currently with two agent tools for gcal and gmail due to these becoming 
custom agents

### What is ZStyle?

ZStyle is a lifestyle management app. Life throws service after service, app after app, yet remembering all of them what goes where etc. ZStyle helps to manage this by integrating as many regular daily use life as possible 
ex. 
    slack 
    gmail
    google calendar 
    ticktick 
    alarms
    whatsapp
    discord
    reminders 
    etc.

While ZStyle can interact with these regular tools the app takes it a step further by creating an easily customizable dashboard on your phone to bring all the information of your life to 1 place. 

ZStyle uses these integrations and AI Agent interactablility to set goals while ZStyle acts as an AI personal assistant to cleanup messy todo lists, unorganized calenders, schedule the day

To make the lifestyle platform more powerful other AI agents are introduced
ex. 
    fitness coach - Strava, Gym Chain Apps, Custom trackers
    nutritionist - Recipe Books, Meal trackers, calorie trackers
    student assistant - Canvas, etc.

These agents when purchased alongside ZStyle work together directly through A2A protocol.
Agents will also be given the ability to communicate with other relavent agents.
This will allow ZStyle to help these other agents create customized plans for each user
For example: the fitness coach could recommend starting to eat more calories a day, the fitness coach would be able to call the nutritionist and have the nutritionist start creating meal ideas that follow the fitness coach recommendations to reach health goals.

Each goal is tracked by the agent just through interacting with the App, Widgets, and (Coming Soon) Text or Call
This allows current goals to be viewable and help people not overload their goals and days 

Put together tracking daily life never became easier 

ZStyle while an ochestrating personal assistant by function is a lifecoach(style) manager it ensures integrations of personal time for scrolling, reading, or for me this. It also encourages and focuses on trying to help the user enjoy time without technology, now that ZStyle can handle everything it encorages thigns like going on walk while listening to a podcast, disconnecting on days when you really dont need to do work.

ZStyle looks to create a world of looking up from devices and experience life