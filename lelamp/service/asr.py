import asyncio
import numpy as np
from faster_whisper import WhisperModel
from livekit import rtc

class FasterWhisperASR:
    def __init__(self, model_size: str = "base", device: str = "cpu"):
        print(f"Loading Faster-Whisper ({model_size}) on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type="int8")
        print("ASR ready.")

    async def stream_recognize(self, frame_stream: asyncio.Queue) -> str:
        """
        接收 16kHz PCM 音频帧，返回转录文本
        """
        audio_buffer = np.array([], dtype=np.float32)

        while True:
            frame = await frame_stream.get()
            if frame is None:  # 结束信号
                break

            # LiveKit 音频帧是 16-bit PCM，需转为 float32
            samples = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32) / 32768.0
            audio_buffer = np.concatenate([audio_buffer, samples])

        if len(audio_buffer) == 0:
            return ""

        # 转录（中文+英文）
        segments, _ = self.model.transcribe(
            audio_buffer,
            language=None,  # 自动检测
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False
        )
        text = "".join(seg.text for seg in segments).strip()
        print(f"ASR Result: '{text}'")
        return text


