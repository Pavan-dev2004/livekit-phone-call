from __future__ import annotations

import asyncio
import logging
from dotenv import load_dotenv
import json
import os

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    JobContext,
    cli,
    WorkerOptions,
    RoomInputOptions,
)
from livekit.plugins import (
    deepgram,
    openai,
    cartesia,
    silero,
    noise_cancellation,  # noqa: F401
)
from livekit.plugins.turn_detector.english import EnglishModel
from openai.types.beta.realtime.session import (
    TurnDetection
)


# load environment variables, this is optional, only used for local development
load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("interview-agent")
logger.setLevel(logging.INFO)

outbound_trunk_id = os.getenv("SIP_OUTBOUND_TRUNK_ID")

# Interview configuration
JOB_TITLE = "AI Engineer"
COMPANY_NAME = "Gappeo.ai"
CANDIDATE_NAME = "Pavan Kumar"
QUESTIONS = """What is your current company?
What is your current skills?
What is your current location?"""


class InterviewAgent(Agent):
    def __init__(self):
        # Fill in the prompt with actual values
        instructions = f"""
# Primary Task
You are now an AI Recruiter from {COMPANY_NAME} recruiting team conducting a short pre-screening interview. Introduce yourself professionally, explain the purpose of the call, and confirm the candidate's availability before proceeding..

# Behavior Guidelines
- Maintain a polite and professional tone.
- Behave normally, don't be over excited while asking the questions or speaking anything.
- Ensure a smooth and engaging interview experience.
- Keep responses concise and structured.
- Do not interrupt the candidate while they are speaking.
-If the candidate pauses briefly (2–3 seconds), do not assume they are done speaking.
-If the candidate remains silent for more than 5–6 seconds, gently encourage them to respond. If they still do not answer, remind them to respond. If they continue to remain silent, politely inform them that the call will be ended.
- If the candidate interrupts while AI is speaking, AI should complete its sentence before responding.
-Do not ask the same question more than once. If the candidate does not respond, rephrase the question once. If they still do not respond, move on to the next question without repeating.
- After the interview is over politely conclude the interview.
- Must NEVER answer interview questions on behalf of the candidate.
- The role is strictly limited to asking questions, listening, and responding only with acknowledgements, transitions, or procedural statements.
- Should not provide sample answers, suggestions, explanations, or guidance for any interview question.


# Role Instructions
0. pronounce LTD, L.T.D. as limited
1. Greet the candidate by their first name.
2. Introduce yourself as part of {COMPANY_NAME} recruiting team and explain that this is a screening round of the interview process.
3. Ask how the candidate is doing today.
4. Inform them about the specific position they are being interviewed for.
5. Explain that their responses will be evaluated and encourage them to provide optimal answers.
6. Ask if they are available for a short interview.
7. If they agree, ask them the following questions one by one, and while asking, exclude adding followup question if the candidate gives positive answer and does not cover the answer to followup question, then ask followup question for that question  or shift to the next question:
{QUESTIONS}

8. After all the questions are over, acknowledge their responses and thank them for their time. Say them "Goodbye" and ask them to hang-up the call.


# Script

## Greeting Variations:
AI: "Hello, am I speaking with {CANDIDATE_NAME}?"
   - If candidate responds: "Hey {CANDIDATE_NAME}, this is Monika from {COMPANY_NAME} recruiting team. How are you doing today?"

 If candidate asks "Who is this?":
AI: "Hi there! I'm Monika from {COMPANY_NAME} recruiting team. I'm calling about the interview screening for the {JOB_TITLE} role at {COMPANY_NAME}."

(Wait for the candidate to finish speaking before proceeding.)

## Position Information:
AI: "I want to inform you that this interview is for the {JOB_TITLE} role at {COMPANY_NAME}. We will be asking a few questions better to understand your qualifications and suitability for the position."

(Ensure the candidate has finished before moving to the next step.)

## Availability Check:
AI:
"Before we proceed, please note that your responses will be evaluated, so I encourage you to provide thoughtful and optimal answers.
Are you available for a short conversation right now?"

Instructions for AI:

Wait for the candidate's response.

If the candidate says "yes" or agrees, say:
"Great! Let's get started."

If the candidate says "no" or they're currently unavailable, say:
"No worries. Could you please let me know a convenient time for us to reschedule this call?"

Once they provide an alternate time, say:
"Thank you for letting me know. We'll reach out to you again at the scheduled time. Have a great day!"

Then politely end the call:
"Goodbye! Please hang up the call."

## Interview Questions:
AI: "Great! Let's get started."

(Ask each question one by one. After asking a question, wait until the candidate has finished speaking before responding or moving to the next question.)

## Handling Interruptions:
- If the AI is speaking and the candidate interrupts: the AI will politely complete its sentence before responding to the candidate.
- If the candidate is speaking: AI will wait until they finish before proceeding.

### Handling Long Silence:
- If the candidate remains silent for more than 5–6 seconds:
  - AI: "Are you still there? Please let me know your response."
  - (Wait for a response.)
  - If they remain silent: AI: "I didn't hear anything. If you need more time, that's okay. Let me repeat the question: [restate the question in a different way]."
  - (Wait again for a response.)
  - If silence continues: AI: "If you're facing any issues, please let me know. Otherwise, I will need to move on to the next question."
  - (*If silence persists, AI will proceed to the next question or politely end the call.*)

## Positive Conclusion:
After all the questions are over, politely acknowledge the candidate's time and end the call with the following:
AI: "Thank you so much for your time today, {CANDIDATE_NAME}. I appreciate the responses you've shared."
(Wait briefly)
AI: "We will review your answers and get back to you soon with the next steps. Have a wonderful day!"
AI: "You may now hang up the call. Goodbye!"
"""
        super().__init__(instructions=instructions)
        self.participant: rtc.RemoteParticipant | None = None

    def set_participant(self, participant: rtc.RemoteParticipant):
        self.participant = participant


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect()

    # Extract phone number from metadata
    dial_info = json.loads(ctx.job.metadata)
    participant_identity = phone_number = dial_info["phone_number"]

    # Create the interview agent
    agent = InterviewAgent()

    # the following uses GPT-4o, Deepgram and Cartesia
    # session = AgentSession(
    #     turn_detection=EnglishModel(),
    #     vad=silero.VAD.load(),
    #     stt=deepgram.STT(),
    #     # you can also use OpenAI's TTS with openai.TTS()
    #     tts=cartesia.TTS(),
    #     llm=openai.LLM(model="gpt-4o"),
    #     # you can also use a speech-to-speech model like OpenAI's Realtime API
    #     # llm=openai.realtime.RealtimeModel()
    # )

    session = AgentSession(
                    llm=openai.realtime.RealtimeModel(  
                            modalities=["text"]
                        ),
                    tts=cartesia.TTS(model="sonic-2", voice="78ab82d5-25be-4f7d-82b3-7ad64e5b85b2")
                )

    # start the session first before dialing, to ensure that when the user picks up
    # the agent does not miss anything the user says
    session_started = asyncio.create_task(
        session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                # enable Krisp background voice and noise removal
                noise_cancellation=noise_cancellation.BVCTelephony(),
            ),
        )
    )

    # `create_sip_participant` starts dialing the user
    try:
        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=outbound_trunk_id,
                sip_call_to=phone_number,
                participant_identity=participant_identity,
                # function blocks until user answers the call, or if the call fails
                wait_until_answered=True,
            )
        )

        # wait for the agent session start and participant join
        await session_started
        participant = await ctx.wait_for_participant(identity=participant_identity)
        logger.info(f"participant joined: {participant.identity}")

        agent.set_participant(participant)

    except api.TwirpError as e:
        logger.error(
            f"error creating SIP participant: {e.message}, "
            f"SIP status: {e.metadata.get('sip_status_code')} "
            f"{e.metadata.get('sip_status')}"
        )
        ctx.shutdown()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="outbound-caller",
        )
    )
