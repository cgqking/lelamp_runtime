# tts.py
import edge_tts
import asyncio
import tempfile
import subprocess
import os

class EdgeTTS:
    def __init__(self, voice: str = "en-US-AvaNeural"):  # 支持 en/zh
        self.voice = voice

    async def synthesize_and_play(self, text: str):
        if not text.strip():
            return

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        try:
            # 生成 16kHz WAV
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(tmp_path)

            # 转为 16kHz 单声道（确保兼容 aplay）
            converted = tmp_path.replace(".wav", "_16k.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", tmp_path,
                "-ar", "16000", "-ac", "1", "-f", "wav", converted
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 播放（阻塞直到结束）
            subprocess.run(["aplay", "-q", converted], check=True)

        finally:
            for path in [tmp_path, converted]:
                if os.path.exists(path):
                    os.remove(path)