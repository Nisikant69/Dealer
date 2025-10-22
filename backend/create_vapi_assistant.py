import requests
import os
import json
# --- CONFIGURATION ---
# This script relies on the config.py to load the .env file.
# You must run this script from the `backend` directory.
from app.core.config import settings

VAPI_API_KEY = settings.VAPI_API_KEY

# You must have ngrok running and provide the public URL here
# Example: "https://<your-id>.ngrok-free.app"
NGROK_BASE_URL = "https://ee59cca48b7c.ngrok-free.ngrok-free.app" # <-- IMPORTANT: REPLACE THIS

# --- MODIFICATION ---
# Your ElevenLabs Voice ID (the NAME of the voice, e.g., "Rachel").
# Find this in your ElevenLabs Voice Lab. IT IS NOT YOUR API KEY.
ELEVENLABS_VOICE_ID = "TTY70JqFvDxeExufZ1za" # <-- IMPORTANT: REPLACE THIS
# --- END MODIFICATION ---


# --- VALIDATION ---
if not VAPI_API_KEY or "your_vapi_api_key" in VAPI_API_KEY:
    print("FATAL ERROR: VAPI_API_KEY is not set in your backend/.env file. The script cannot proceed.")
    exit()
if "your-ngrok-id" in NGROK_BASE_URL:
    print("FATAL ERROR: You must replace the placeholder NGROK_BASE_URL with your actual running ngrok URL.")
    exit()
if "your_actual_voice_id_name" in ELEVENLABS_VOICE_ID:
    print("FATAL ERROR: You must provide a valid ElevenLabs Voice ID (e.g., 'Rachel').")
    exit()

# --- SCRIPT LOGIC ---

WEBHOOK_URL = f"{NGROK_BASE_URL}/api/v1/voice/webhook"

create_assistant_payload = {
    "name": "Dealership Local LLM Assistant",
    "server": {
        "url": WEBHOOK_URL,
        "timeoutSeconds": 30
    },
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-2",
        "language": "en-IN"
    },
    # --- MODIFICATION ---
    # The provider name is '11labs', not 'elevenlabs'.
    "voice": {
        "provider": "11labs",
        "voiceId": ELEVENLABS_VOICE_ID
    },
    # --- END MODIFICATION ---
    "model": {
        "provider": "openai",
        "model": "gpt-4" # Placeholder for Vapi's logging
    },
    "firstMessage": "Hello, thank you for calling Luxury Auto Group. How may I assist you today?"
}

print("--- PAYLOAD TO BE SENT ---")
print(json.dumps(create_assistant_payload, indent=2))
print("--------------------------\n")

try:
    response = requests.post(
        "https://api.vapi.ai/assistant",
        headers={
            "Authorization": f"Bearer {VAPI_API_KEY}",
            "Content-Type": "application/json"
        },
        json=create_assistant_payload
    )

    response.raise_for_status()

    assistant_data = response.json()
    assistant_id = assistant_data.get("id")

    print(f"✅ Assistant created successfully.")
    print(f"   - Assistant Name: {assistant_data.get('name')}")
    print(f"   - Assistant ID: {assistant_id}")
    print("\nIMPORTANT: Update your backend/.env file with this new VAPI_ASSISTANT_ID.")

except requests.exceptions.HTTPError as e:
    print(f"❌ HTTP ERROR: {e.response.status_code}")
    print(f"   - VAPI'S DETAILED ERROR: {e.response.text}")
    print("\n   - CHECKPOINT: The error above from Vapi will tell you which field is wrong. Check your NGROK_BASE_URL and ELEVENLABS_VOICE_ID values.")
except requests.exceptions.RequestException as e:
    print(f"❌ CONNECTION ERROR: {e}")
    print("\n   - CHECKPOINT: Is your internet connection working?")

