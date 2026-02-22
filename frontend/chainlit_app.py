import uuid

import chainlit as cl

from frontend.chainlit_runtime import JarvisSessionRuntime


RUNTIME_KEY = "jarvis_runtime"
AUDIO_BUFFER_KEY = "audio_buffer"


async def _handle_query(query: str, is_voice: bool = False):
    runtime: JarvisSessionRuntime | None = cl.user_session.get(RUNTIME_KEY)
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


@cl.on_chat_start
async def on_chat_start():
    thread_id = f"chainlit_{uuid.uuid4().hex}"
    runtime = await JarvisSessionRuntime.create(thread_id=thread_id)
    cl.user_session.set(RUNTIME_KEY, runtime)
    cl.user_session.set(AUDIO_BUFFER_KEY, bytearray())

    await cl.Message(
        content=(
            "JARVIS Chainlit frontend is ready.\n"
            "- Type a message to chat\n"
            "- Use your browser microphone if audio streaming is enabled\n"
            "- Or type `/voice` to upload an audio clip for transcription"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    content = (message.content or "").strip()

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
    runtime: JarvisSessionRuntime | None = cl.user_session.get(RUNTIME_KEY)
    if runtime:
        await runtime.close()
