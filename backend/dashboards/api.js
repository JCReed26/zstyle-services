// api.js

const BASE_URL = ''; // Assuming the frontend is served from the same origin as the backend

export async function createUser(userData) {
    const response = await fetch(`${BASE_URL}/user/new_user/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        },
        body: JSON.stringify(userData)
    });
    return response;
}

export async function loginUser(userData) {
    const response = await fetch(`${BASE_URL}/user/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'accept': 'application/json'
        },
        body: JSON.stringify(userData)
    });
    return response;
}
