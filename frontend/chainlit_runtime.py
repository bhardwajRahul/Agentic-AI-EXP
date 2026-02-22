import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite
import av
import numpy as np
from faster_whisper import WhisperModel
from langchain_mcp_adapters.client import MultiServerMCPClient

from config.settings import (
    CHECKPOINT_DB,
    communication_config,
    content_config,
    planning_config,
    supervisor_config,
)
from core.graph import build_graph
from utils.helper import AsyncSqliteSaver, request_counter, setup_logger
from utils.memory_manager import log_event

logger = setup_logger(__name__)


@dataclass
class AudioTranscriber:
    stt_model_path: str
    sample_rate: int = 16000
    _model: WhisperModel | None = None

    @property
    def model(self) -> WhisperModel:
        if self._model is None:
            self._model = WhisperModel(
                "base.en",
                device="cpu",
                compute_type="int8",
                download_root=self.stt_model_path,
            )
        return self._model

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""

        audio = self._decode_to_float32(audio_bytes)
        if audio.size == 0:
            return ""

        segments, _ = self.model.transcribe(
            audio,
            beam_size=3,
            temperature=0,
            language="en",
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
        )
        return " ".join(segment.text for segment in segments).strip()

    def transcribe_file(self, file_path: str | Path) -> str:
        path = Path(file_path)
        if not path.exists():
            return ""
        return self.transcribe_bytes(path.read_bytes())

    def _decode_to_float32(self, audio_bytes: bytes) -> np.ndarray:
        pcm_frames: list[np.ndarray] = []

        with av.open(io.BytesIO(audio_bytes), mode="r") as container:
            resampler = av.audio.resampler.AudioResampler(
                format="s16",
                layout="mono",
                rate=self.sample_rate,
            )

            for frame in container.decode(audio=0):
                resampled = resampler.resample(frame)
                frames = resampled if isinstance(resampled, list) else [resampled]
                for output_frame in frames:
                    if output_frame is None:
                        continue
                    pcm = output_frame.to_ndarray().astype(np.int16).flatten()
                    if pcm.size:
                        pcm_frames.append(pcm)

        if not pcm_frames:
            return np.array([], dtype=np.float32)

        merged = np.concatenate(pcm_frames)
        return merged.astype(np.float32) / 32768.0


class JarvisSessionRuntime:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self._connection: aiosqlite.Connection | None = None
        self._graph = None
        self._transcriber = AudioTranscriber(stt_model_path="./models/stt")

    @classmethod
    async def create(cls, thread_id: str) -> "JarvisSessionRuntime":
        runtime = cls(thread_id=thread_id)

        communication_client = MultiServerMCPClient(communication_config)
        planning_client = MultiServerMCPClient(planning_config)
        content_client = MultiServerMCPClient(content_config)
        supervisor_client = MultiServerMCPClient(supervisor_config)

        communication_tools = await communication_client.get_tools()
        planning_tools = await planning_client.get_tools()
        content_tools = await content_client.get_tools()
        supervisor_tools = await supervisor_client.get_tools()

        logger.info(
            "Chainlit tool bootstrap -> comm=%s planning=%s content=%s supervisor=%s",
            len(communication_tools),
            len(planning_tools),
            len(content_tools),
            len(supervisor_tools),
        )

        tool_sets = {
            "communication": communication_tools,
            "planning": planning_tools,
            "content": content_tools,
            "supervisor": supervisor_tools,
        }

        runtime._connection = await aiosqlite.connect(str(CHECKPOINT_DB))
        checkpointer = AsyncSqliteSaver(runtime._connection)
        runtime._graph = build_graph(tool_sets, checkpointer)
        return runtime

    async def ask(self, query: str, is_voice: bool = False) -> str:
        config: dict[str, Any] = {
            "configurable": {"thread_id": self.thread_id, "is_voice": is_voice}
        }

        try:
            await log_event(
                thread_id=self.thread_id,
                actor="Human_node",
                message=query,
                metadata={"source": "voice" if is_voice else "text"},
            )
        except Exception as exc:
            logger.warning("Failed to log Human_node event: %s", exc)

        request_counter.start_turn(query)
        state = await self._graph.ainvoke(
            {"messages": [{"role": "user", "content": query}]},
            config=config,
        )
        request_counter.end_turn()

        return self._extract_last_ai_message(state)

    def transcribe_audio_bytes(self, audio_bytes: bytes) -> str:
        return self._transcriber.transcribe_bytes(audio_bytes)

    def transcribe_audio_file(self, file_path: str | Path) -> str:
        return self._transcriber.transcribe_file(file_path)

    async def close(self):
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    @staticmethod
    def _extract_last_ai_message(state: dict[str, Any]) -> str:
        messages = state.get("messages", [])
        for message in reversed(messages):
            msg_type = getattr(message, "type", "")
            content = getattr(message, "content", "")
            if msg_type == "ai" and content:
                return str(content)

        if messages:
            fallback = messages[-1]
            content = getattr(fallback, "content", "")
            if content:
                return str(content)

        return "I could not generate a response for that request."
