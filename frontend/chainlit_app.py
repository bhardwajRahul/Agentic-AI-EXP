import asyncio
import time
import uuid

import chainlit as cl

from core.voice_inference import VoiceInference
from frontend.chainlit_runtime import JarvisSessionRuntime
from utils.helper import clean_text_for_tts


RUNTIME_KEY = "jarvis_runtime"
AUDIO_BUFFER_KEY = "audio_buffer"
VOICE_AGENT_KEY = "voice_agent"
VOICE_TASK_KEY = "voice_task"
VOICE_STATE_KEY = "voice_state"
SESSION_TIMEOUT = 300


def _build_voice_actions() -> list[cl.Action]:
    return [
        cl.Action(
            name="start_voice_listening",
            payload={"state": "start"},
            label="Start Voice Listening",
        ),
        cl.Action(
            name="stop_voice_listening",
            payload={"state": "stop"},
            label="Stop Voice Listening",
        ),
        cl.Action(
            name="voice_output_on",
            payload={"state": "on"},
            label="Voice Output On",
        ),
        cl.Action(
            name="voice_output_off",
            payload={"state": "off"},
            label="Voice Output Off",
        ),
    ]


async def _send_voice_controls():
    state: dict | None = cl.user_session.get(VOICE_STATE_KEY)
    if state is None:
        state = {"listening": False, "voice_output": False}
        cl.user_session.set(VOICE_STATE_KEY, state)

    await cl.Message(
        content=(
            "Voice controls:\n"
            f"- Listening: {'ON' if state.get('listening') else 'OFF'}\n"
            f"- Voice output: {'ON' if state.get('voice_output') else 'OFF'}"
        ),
        actions=_build_voice_actions(),
    ).send()


async def _set_listening(enabled: bool):
    state: dict | None = cl.user_session.get(VOICE_STATE_KEY)
    task: asyncio.Task | None = cl.user_session.get(VOICE_TASK_KEY)

    if state is None:
        state = {"listening": False, "voice_output": False}
        cl.user_session.set(VOICE_STATE_KEY, state)

    if enabled and state.get("listening", False):
        await cl.Message(content="Voice listening is already running.").send()
        await _send_voice_controls()
        return

    state["listening"] = enabled
    if enabled and not state.get("last_interaction"):
        state["last_interaction"] = 0
    if enabled and (task is None or task.done()):
        task = asyncio.create_task(_continuous_voice_worker())
        cl.user_session.set(VOICE_TASK_KEY, task)

    await _send_voice_controls()


async def _set_voice_output(enabled: bool):
    state: dict | None = cl.user_session.get(VOICE_STATE_KEY)
    if state is None:
        state = {"listening": False, "voice_output": False}
        cl.user_session.set(VOICE_STATE_KEY, state)

    state["voice_output"] = enabled
    await _send_voice_controls()


async def _continuous_voice_worker():
    runtime: JarvisSessionRuntime | None = cl.user_session.get(RUNTIME_KEY)
    voice_agent: VoiceInference | None = cl.user_session.get(VOICE_AGENT_KEY)
    state: dict | None = cl.user_session.get(VOICE_STATE_KEY)

    if runtime is None or voice_agent is None or state is None:
        await cl.Message(content="Voice runtime is not initialized.").send()
        return

    await cl.Message(
        content="Continuous voice listening started. Use Stop Voice Listening to end."
    ).send()

    while state.get("listening", False):
        try:
            last_interaction = float(state.get("last_interaction", 0) or 0)
            time_since = time.time() - last_interaction if last_interaction else 10**9
            is_session_active = time_since < SESSION_TIMEOUT

            if not is_session_active:
                transcript = await asyncio.to_thread(voice_agent.wait_for_wake_word)
            else:
                remaining = max(1.0, SESSION_TIMEOUT - time_since)
                try:
                    transcript = await asyncio.wait_for(
                        asyncio.to_thread(voice_agent.listen), timeout=remaining
                    )
                except asyncio.TimeoutError:
                    continue

            if not state.get("listening", False):
                break

            if not transcript or not transcript.strip():
                continue

            state["last_interaction"] = time.time()
            await cl.Message(content=f"Voice transcript: {transcript.strip()}").send()
            response = await runtime.ask(query=transcript.strip(), is_voice=True)
            await cl.Message(content=response).send()

            if state.get("voice_output", False):
                speech_text = clean_text_for_tts(response)
                if speech_text:
                    await asyncio.to_thread(voice_agent.speak, speech_text)

        except Exception as exc:
            await cl.Message(content=f"Voice listener error: {exc}").send()
            await asyncio.sleep(0.5)

    await cl.Message(content="Continuous voice listening stopped.").send()


async def _handle_query(query: str, is_voice: bool = False):
    runtime: JarvisSessionRuntime | None = cl.user_session.get(RUNTIME_KEY)
    voice_agent: VoiceInference | None = cl.user_session.get(VOICE_AGENT_KEY)
    state: dict | None = cl.user_session.get(VOICE_STATE_KEY)

    if runtime is None:
        await cl.Message(
            content="Session runtime is not initialized. Please refresh and try again."
        ).send()
        return

    if not query.strip():
        await cl.Message(content="I did not detect any text in that input.").send()
        return

    response = await runtime.ask(query=query.strip(), is_voice=is_voice)
    await cl.Message(content=response).send()

    if state is not None:
        state["last_interaction"] = time.time()

    if voice_agent and state and state.get("voice_output", False):
        speech_text = clean_text_for_tts(response)
        if speech_text:
            await asyncio.to_thread(voice_agent.speak, speech_text)


@cl.on_chat_start
async def on_chat_start():
    thread_id = f"chainlit_{uuid.uuid4().hex}"
    runtime = await JarvisSessionRuntime.create(thread_id=thread_id)
    voice_agent = VoiceInference()

    cl.user_session.set(RUNTIME_KEY, runtime)
    cl.user_session.set(VOICE_AGENT_KEY, voice_agent)
    cl.user_session.set(VOICE_TASK_KEY, None)
    cl.user_session.set(
        VOICE_STATE_KEY,
        {"listening": False, "voice_output": False, "last_interaction": 0},
    )
    cl.user_session.set(AUDIO_BUFFER_KEY, bytearray())

    await cl.Message(
        content=(
            "JARVIS Chainlit frontend is ready.\n"
            "- Type a message to chat\n"
            "- Use Start/Stop Voice Listening buttons for continuous local mic mode\n"
            "- Use Voice Output On/Off to control spoken responses\n"
            "- Optional: type `/voice` to upload an audio clip for transcription"
        )
    ).send()
    await _send_voice_controls()


@cl.on_message
async def on_message(message: cl.Message):
    content = (message.content or "").strip()

    if content.lower() in {"/controls", "/voice_controls"}:
        await _send_voice_controls()
        return

    if content.lower() == "/start_voice":
        await _set_listening(True)
        return

    if content.lower() == "/stop_voice":
        await _set_listening(False)
        return

    if content.lower() == "/voice_output_on":
        await _set_voice_output(True)
        return

    if content.lower() == "/voice_output_off":
        await _set_voice_output(False)
        return

    if content.lower() == "/voice":
        files = await cl.AskFileMessage(
            content="Upload an audio file (wav/mp3/m4a/webm) and I will transcribe it.",
            accept=["audio/*"],
            max_size_mb=25,
            timeout=180,
        ).send()

        if not files:
            await cl.Message(content="No file was uploaded.").send()
            return

        runtime: JarvisSessionRuntime | None = cl.user_session.get(RUNTIME_KEY)
        if runtime is None:
            await cl.Message(content="Runtime not initialized.").send()
            return

        transcript = runtime.transcribe_audio_file(files[0].path)
        if not transcript:
            await cl.Message(
                content="I couldn't transcribe that file. Please try a clearer recording."
            ).send()
            return

        await cl.Message(content=f"Voice transcript: {transcript}").send()
        await _handle_query(transcript, is_voice=True)
        return

    await _handle_query(content, is_voice=False)


@cl.action_callback("start_voice_listening")
async def start_voice_listening(_action: cl.Action):
    await _set_listening(True)


@cl.action_callback("stop_voice_listening")
async def stop_voice_listening(_action: cl.Action):
    await _set_listening(False)


@cl.action_callback("voice_output_on")
async def voice_output_on(_action: cl.Action):
    await _set_voice_output(True)


@cl.action_callback("voice_output_off")
async def voice_output_off(_action: cl.Action):
    await _set_voice_output(False)


if hasattr(cl, "on_audio_chunk"):

    @cl.on_audio_chunk
    async def on_audio_chunk(chunk):
        audio_buffer: bytearray | None = cl.user_session.get(AUDIO_BUFFER_KEY)
        if audio_buffer is None:
            audio_buffer = bytearray()
            cl.user_session.set(AUDIO_BUFFER_KEY, audio_buffer)

        data = getattr(chunk, "data", None)
        if data:
            audio_buffer.extend(data)


if hasattr(cl, "on_audio_end"):

    @cl.on_audio_end
    async def on_audio_end(*_args, **_kwargs):
        audio_buffer: bytearray | None = cl.user_session.get(AUDIO_BUFFER_KEY)
        if not audio_buffer:
            return

        runtime: JarvisSessionRuntime | None = cl.user_session.get(RUNTIME_KEY)
        if runtime is None:
            await cl.Message(content="Runtime not initialized.").send()
            return

        transcript = runtime.transcribe_audio_bytes(bytes(audio_buffer))
        cl.user_session.set(AUDIO_BUFFER_KEY, bytearray())

        if not transcript:
            await cl.Message(content="No speech detected. Please try again.").send()
            return

        await cl.Message(content=f"Voice transcript: {transcript}").send()
        await _handle_query(transcript, is_voice=True)


@cl.on_chat_end
async def on_chat_end():
    state: dict | None = cl.user_session.get(VOICE_STATE_KEY)
    task: asyncio.Task | None = cl.user_session.get(VOICE_TASK_KEY)
    runtime: JarvisSessionRuntime | None = cl.user_session.get(RUNTIME_KEY)

    if state:
        state["listening"] = False

    if task and not task.done():
        task.cancel()

    if runtime:
        await runtime.close()
