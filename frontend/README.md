Purpose is to have static forms to fill out to add data/users to the database

Paths:
    login -> create_account -> login 

    login -> user_profile

    user_profile -> chat -> user_profile

    user_profile -> voice -> user_profile 

Connections: 
    create_account: Calls /user/new_user/

    login: Calls /user/login

    chat: connects chat websocket on page open

    voice: connects voice websocket on toggle button

    chat_voice: connects websocket and toggles between chat and voice via button

Functions: 
    api.js: 
        