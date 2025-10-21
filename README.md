# ZStyle Web and Backend Services 
> Note: zstyle-mobile-app is the repository for the mobile app that corresponds with this program 
> as you will see currently as of writing this there is nothing in the web frontend

# QuickStart

Run the stack (proxy + same-origin WS)

Prerequisites
    Docker and Docker Compose installed
    Ports 80 (and optionally 443) available on your machine
    The UI listens on port 2000 inside the web_frontend container; the agents WS listens on 4312 inside the agents container.
    First-time setup
    Ensure Nginx config is at nginx/conf.d/default.conf (path is important).
    If you previously created ngnix/, rename to nginx/.

Start
> docker compose up --build
Open http://localhost in your browser.

How it routes
UI: Nginx proxies / to web_frontend:2000.
WebSocket: Nginx proxies /ws to agents:4312.

Frontend WS URL
    The frontend should use a same-origin WS URL: wss://<host>/ws (HTTPS) or ws://<host>/ws (HTTP).
    In dev at http://localhost, that resolves to ws://localhost/ws.
    If you set NEXT_PUBLIC_WS_URL, it will override and connect directly to that URL (e.g., ws://localhost:4312).

React Native
    Use the same endpoint as browsers when reachable: ws(s)://<your-machine-IP-or-domain>/ws.

Local dev tips:
    iOS Simulator: ws://localhost/ws
    Android Emulator: ws://10.0.2.2/ws
    Physical devices on same Wi‑Fi: ws://<your-laptop-LAN-IP>/ws
    Off-LAN or mobile networks: deploy with TLS and use wss://<your-domain>/ws.


Production
Add TLS to Nginx (443) and update your DNS to point your domain to the host running the proxy.
Browsers and RN should connect to wss://yourdomain.com/ws.

Troubleshooting
Nginx starts but 502 on /ws: ensure agents is up and listening on 0.0.0.0:4312 inside the container.
UI loads but assets 404: confirm web_frontend actually serves on port 2000 and isn’t using a different port.
CORS / mixed-content errors: on HTTPS, ensure the WS URL uses wss://; prefer same-origin (/ws) to avoid CORS.
Windows firewall: allow inbound on port 80 when testing from devices on the LAN.

# What is ZStyle?

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

ZStyle looks to transform people
