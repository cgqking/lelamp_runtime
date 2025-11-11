# lelamp/service/audio_processor.py

import asyncio
import re
import random
from livekit import rtc

from lelamp.service.asr import FasterWhisperASR

WAKE_PHRASES = {"hey lelamp", "hi lelamp", "okay lelamp", "lelamp"}
VALID_RECORDINGS = {
    "curious", "excited", "happy_wiggle", "headshake", "nod",
    "sad", "scanning", "shock", "shy", "wake_up"
}
DEFAULT_MOTIONS = ["nod", "curious", "happy_wiggle"]
ACTION_PATTERN = re.compile(r"@@(\w+)\(([^)]+)\)@@")


class AudioProcessor:
    def __init__(self, agent, llm, tts):
        self.agent = agent
        self.llm = llm
        self.tts = tts
        self.asr = FasterWhisperASR(model_size="base")
        self._active_streams = {}  # track_sid -> task

    async def run(self, room: rtc.Room):
        print("🎙️ AudioProcessor started — listening to any speaker")

        conversation_history = [{"role": "system", "content": self.agent.instructions}]

        # 监听新发布的音频轨道
        @room.on("track_published")
        def on_track_published(pub: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if pub.kind == rtc.TrackKind.KIND_AUDIO:
                print(f"🎧 New audio track from {participant.identity}")
                # 异步启动处理（避免阻塞事件回调）
                asyncio.create_task(self._handle_audio_track(room, pub, participant, conversation_history))

        # 处理已经存在的音频轨道（房间连接时可能已有用户）
        for participant in room.remote_participants.values():
            for pub in participant.tracks.values():
                if pub.kind == rtc.TrackKind.KIND_AUDIO and pub.track:
                    print(f"🎧 Existing audio track from {participant.identity}")
                    asyncio.create_task(self._handle_audio_track(room, pub, participant, conversation_history))

        # 保持运行
        try:
            await asyncio.Future()  # 永不退出
        except asyncio.CancelledError:
            print("🛑 AudioProcessor cancelled.")
        finally:
            # 取消所有流任务
            for task in self._active_streams.values():
                task.cancel()

    async def _handle_audio_track(
        self,
        room: rtc.Room,
        pub: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
        conversation_history: list,
    ):
        track_sid = pub.sid
        if track_sid in self._active_streams:
            return  # 已在处理

        try:
            track = await room.subscribe(pub.track_sid)
            if not isinstance(track, rtc.AudioTrack):
                return
        except Exception as e:
            print(f"❌ Failed to subscribe to audio track {track_sid}: {e}")
            return

        task = asyncio.create_task(
            self._process_audio_stream(track, participant.identity, conversation_history)
        )
        self._active_streams[track_sid] = task
        try:
            await task
        except Exception as e:
            print(f"⚠️ Audio stream error for {participant.identity}: {e}")
        finally:
            self._active_streams.pop(track_sid, None)

    async def _process_audio_stream(
        self,
        track: rtc.AudioTrack,
        identity: str,
        conversation_history: list,
    ):
        frame_queue = asyncio.Queue()
        stream_reader = asyncio.create_task(self._audio_stream_reader(track, frame_queue))

        try:
            while True:
                first_frame = await frame_queue.get()
                if first_frame is None:
                    break
                frames = [first_frame]

                # 收集后续帧（模拟 VAD）
                while True:
                    try:
                        frame = await asyncio.wait_for(frame_queue.get(), timeout=1.5)
                        if frame is None:
                            break
                        frames.append(frame)
                    except asyncio.TimeoutError:
                        break

                if not frames:
                    continue

                # ASR
                temp_q = asyncio.Queue()
                for f in frames:
                    await temp_q.put(f)
                await temp_q.put(None)

                user_text = await self.asr.stream_recognize(temp_q)
                user_text = user_text.strip() if user_text else ""

                if not user_text or len(user_text) < 2:
                    continue  # 忽略无效语音

                print(f"👤 [{identity}] said: '{user_text}'")

                # # 唤醒词检查（必须包含）
                # if not any(phrase in user_text.lower() for phrase in WAKE_PHRASES):
                #     print("💤 Ignoring: no wake word detected.")
                #     continue

                # LLM + 动作执行
                conversation_history.append({"role": "user", "content": user_text})
                try:
                    raw_response = await self.llm.chat(conversation_history)
                except Exception as e:
                    print(f"⚠️ LLM error: {e}")
                    raw_response = "Oops! Try again? @@play_recording('shock')@@"

                speech_text = self._execute_actions(raw_response)
                conversation_history.append({"role": "assistant", "content": raw_response})

                print(f"🤖 LeLamp replies: '{speech_text}'")
                await self.tts.synthesize_and_play(speech_text)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"💥 Error in audio processing for {identity}: {e}")
        finally:
            stream_reader.cancel()

    async def _audio_stream_reader(self, track: rtc.AudioTrack, queue: asyncio.Queue):
        try:
            async for event in rtc.AudioStream(track):
                await queue.put(event.frame)
        except Exception as e:
            print(f"⚠️ Audio stream reader error: {e}")
        finally:
            await queue.put(None)

    def _execute_actions(self, full_response: str) -> str:
        calls = ACTION_PATTERN.findall(full_response)
        speech = ACTION_PATTERN.sub("", full_response).strip()
        has_play = False

        for func_name, args_str in calls:
            try:
                if args_str.startswith(('"', "'")):
                    arg_val = args_str.strip('"\'')
                    args = (arg_val,)
                else:
                    args = tuple(int(x.strip()) for x in args_str.split(",") if x.strip())

                if func_name == "play_recording":
                    rec_name = args[0]
                    if rec_name in VALID_RECORDINGS:
                        asyncio.create_task(
                            self.agent.motors_service.dispatch("play", rec_name)
                        )
                        has_play = True
                        print(f"🎬 Playing recording: {rec_name}")
                    else:
                        print(f"⚠️ Invalid recording: {rec_name}")

                elif func_name == "set_rgb_solid" and len(args) == 3:
                    r, g, b = args
                    if all(0 <= x <= 255 for x in (r, g, b)):
                        if hasattr(self.agent, 'rgb_service'):
                            asyncio.create_task(
                                self.agent.rgb_service.dispatch("solid", (r, g, b))
                            )
                            print(f"💡 Setting RGB: ({r}, {g}, {b})")
                        else:
                            print("💡 Ignoring light command: RGB service not active.")
                    else:
                        print(f"⚠️ Invalid RGB values: {args}")

            except Exception as e:
                print(f"❌ Error executing {func_name}({args_str}): {e}")

        if not has_play:
            motion = random.choice(DEFAULT_MOTIONS)
            asyncio.create_task(self.agent.motors_service.dispatch("play", motion))
            print(f"🤖 Auto-playing motion: {motion}")

        return speech if speech else "..."