import asyncio
import os
import random
import json
from dotenv import load_dotenv
from livekit import api

# Load environment variables
load_dotenv(dotenv_path=".env.local")

async def main():
    # Get configuration from environment variables
    livekit_url = os.getenv("LIVEKIT_URL")
    livekit_api_key = os.getenv("LIVEKIT_API_KEY")
    livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
    
    # Phone number to call (removing space for proper formatting)
    phone_number = "+917416985486"
    
    # Optional: transfer number if needed
    # transfer_to = "+9876543210"
    
    # Validate required environment variables
    if not all([livekit_url, livekit_api_key, livekit_api_secret]):
        print("Error: Missing required environment variables.")
        print("Please ensure the following are set in .env.local:")
        print("  - LIVEKIT_URL")
        print("  - LIVEKIT_API_KEY")
        print("  - LIVEKIT_API_SECRET")
        return
    
    # Initialize LiveKit API
    lkapi = api.LiveKitAPI(
        url=livekit_url,
        api_key=livekit_api_key,
        api_secret=livekit_api_secret,
    )
    
    # Generate a unique room name for this call
    room_name = f"outbound-{''.join(str(random.randint(0, 9)) for _ in range(10))}"
    
    # Prepare metadata - the agent expects phone_number and optionally transfer_to
    metadata = {
        "phone_number": phone_number
    }
    # Uncomment if you want to add transfer capability:
    # metadata["transfer_to"] = transfer_to
    
    try:
        print(f"Dispatching agent to call {phone_number}...")
        print(f"Room: {room_name}")
        
        # Dispatch the agent to make the call
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                # Use the agent name from agent.py (line 242)
                agent_name="outbound-caller",
                # The room name to use. This should be unique for each call
                room=room_name,
                # Pass the phone number and other info as JSON metadata
                metadata=json.dumps(metadata)
            )
        )
        
        print(f"Successfully dispatched agent!")
        print(f"Dispatch ID: {dispatch.id}")
        print(f"Room: {room_name}")
        print(f"Agent: outbound-caller")
        print(f"Metadata: {metadata}")
        print("\nThe agent will now make the call and handle the conversation.")
        
    except api.TwirpError as e:
        print(f"Error creating agent dispatch: {e.message}")
        # Check for SIP-specific error metadata if available
        sip_status_code = e.metadata.get('sip_status_code', 'N/A')
        sip_status = e.metadata.get('sip_status', 'N/A')
        if sip_status_code != 'N/A':
            print(f"SIP error code: {sip_status_code}")
            print(f"SIP error message: {sip_status}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
