"""
Phone Number Authentication Endpoints

Handles phone number-based authentication using Supabase Auth.
Works seamlessly with Telegram (phone numbers are available from Telegram users).
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional

from services.auth_service import auth_service

router = APIRouter()


class PhoneAuthInitiateRequest(BaseModel):
    """Request model for initiating phone authentication."""
    phone_number: str = Field(..., description="Phone number in E.164 format (e.g., +1234567890)")


class PhoneAuthVerifyRequest(BaseModel):
    """Request model for verifying OTP."""
    phone_number: str = Field(..., description="Phone number in E.164 format")
    token: str = Field(..., description="OTP token received via SMS")


@router.post("/auth/phone/initiate")
async def initiate_phone_auth(request: PhoneAuthInitiateRequest):
    """
    Initiate phone number authentication by sending OTP.
    
    This endpoint sends an OTP to the provided phone number via Supabase Auth.
    The user will receive an SMS with a verification code.
    
    Args:
        request: PhoneAuthInitiateRequest with phone_number
    
    Returns:
        Success message and phone number (masked)
    
    Raises:
        HTTPException: If Supabase is not configured or OTP sending fails
    """
    try:
        result = await auth_service.initiate_phone_auth(request.phone_number)
        return {
            "success": True,
            "message": "OTP sent successfully. Please check your SMS.",
            "phone_masked": f"{request.phone_number[:5]}****"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {str(e)}")


@router.post("/auth/phone/verify")
async def verify_phone_auth(request: PhoneAuthVerifyRequest):
    """
    Verify OTP token and create user session.
    
    This endpoint verifies the OTP token and creates/updates the user account.
    Returns access tokens for API authentication.
    
    Args:
        request: PhoneAuthVerifyRequest with phone_number and token
    
    Returns:
        Access token, refresh token, and user information
    
    Raises:
        HTTPException: If verification fails
    """
    try:
        result = await auth_service.verify_phone_auth(
            request.phone_number,
            request.token
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OTP verification failed: {str(e)}")


@router.get("/auth/phone/webapp")
async def phone_auth_webapp():
    """
    Web app interface for phone authentication (for Telegram WebView).
    
    Returns an HTML page that can be opened in Telegram's WebView
    for phone number authentication.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phone Authentication</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
                padding: 20px;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            .container {
                width: 100%;
                max-width: 400px;
            }
            h1 {
                font-size: 24px;
                margin-bottom: 20px;
                text-align: center;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-size: 14px;
                color: var(--tg-theme-hint-color, #999999);
            }
            input {
                width: 100%;
                padding: 12px;
                border: 1px solid var(--tg-theme-hint-color, #e0e0e0);
                border-radius: 8px;
                font-size: 16px;
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
            }
            button {
                width: 100%;
                padding: 12px;
                background: var(--tg-theme-button-color, #0088cc);
                color: var(--tg-theme-button-text-color, #ffffff);
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
            }
            button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .message {
                margin-top: 16px;
                padding: 12px;
                border-radius: 8px;
                font-size: 14px;
                text-align: center;
            }
            .message.success {
                background: #d4edda;
                color: #155724;
            }
            .message.error {
                background: #f8d7da;
                color: #721c24;
            }
            .message.info {
                background: #d1ecf1;
                color: #0c5460;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Phone Authentication</h1>
            <div id="initiate-form">
                <div class="form-group">
                    <label for="phone">Phone Number</label>
                    <input 
                        type="tel" 
                        id="phone" 
                        placeholder="+1234567890" 
                        required
                        pattern="^\\+[1-9]\\d{1,14}$"
                    />
                </div>
                <button onclick="initiateAuth()">Send OTP</button>
            </div>
            <div id="verify-form" style="display: none;">
                <div class="form-group">
                    <label for="token">Enter OTP</label>
                    <input 
                        type="text" 
                        id="token" 
                        placeholder="123456" 
                        required
                        maxlength="6"
                    />
                </div>
                <button onclick="verifyAuth()">Verify</button>
            </div>
            <div id="message"></div>
        </div>
        <script>
            let currentPhone = '';
            
            if (window.Telegram && window.Telegram.WebApp) {
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
                
                // Try to get phone number from Telegram user
                const tgUser = window.Telegram.WebApp.initDataUnsafe?.user;
                if (tgUser && tgUser.phone_number) {
                    document.getElementById('phone').value = tgUser.phone_number;
                }
            }
            
            async function initiateAuth() {
                const phone = document.getElementById('phone').value;
                if (!phone) {
                    showMessage('Please enter your phone number', 'error');
                    return;
                }
                
                currentPhone = phone;
                const button = event.target;
                button.disabled = true;
                button.textContent = 'Sending...';
                
                try {
                    const response = await fetch('/auth/phone/initiate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({phone_number: phone})
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showMessage('OTP sent! Check your SMS.', 'success');
                        document.getElementById('initiate-form').style.display = 'none';
                        document.getElementById('verify-form').style.display = 'block';
                    } else {
                        showMessage(data.detail || 'Failed to send OTP', 'error');
                        button.disabled = false;
                        button.textContent = 'Send OTP';
                    }
                } catch (error) {
                    showMessage('Network error. Please try again.', 'error');
                    button.disabled = false;
                    button.textContent = 'Send OTP';
                }
            }
            
            async function verifyAuth() {
                const token = document.getElementById('token').value;
                if (!token) {
                    showMessage('Please enter the OTP', 'error');
                    return;
                }
                
                const button = event.target;
                button.disabled = true;
                button.textContent = 'Verifying...';
                
                try {
                    const response = await fetch('/auth/phone/verify', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            phone_number: currentPhone,
                            token: token
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showMessage('Authentication successful!', 'success');
                        setTimeout(() => {
                            if (window.Telegram && window.Telegram.WebApp) {
                                window.Telegram.WebApp.close();
                            } else {
                                window.close();
                            }
                        }, 2000);
                    } else {
                        showMessage(data.detail || 'Invalid OTP', 'error');
                        button.disabled = false;
                        button.textContent = 'Verify';
                    }
                } catch (error) {
                    showMessage('Network error. Please try again.', 'error');
                    button.disabled = false;
                    button.textContent = 'Verify';
                }
            }
            
            function showMessage(text, type) {
                const messageDiv = document.getElementById('message');
                messageDiv.textContent = text;
                messageDiv.className = 'message ' + type;
                messageDiv.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
