

WAKE_PHRASES = {"hey lelamp", "hi lelamp", "okay lelamp", "lelamp"}
class AudioProcessor:
    def __init__(self, agent: LeLamp, llm: QwenLLM, tts: EdgeTTS):
        self.agent = agent
        self.llm = llm
        self.tts = tts
        self.asr = FasterWhisperASR(model_size="base")  # 可换 small/base.int8

    async def run(self, room: rtc.Room):
        # Find first user audio track
        subscriber = None
        for participant in room.participants.values():
            if participant.identity == "host":  # 或根据你的房间设置调整
                for track_pub in participant.tracks.values():
                    if track_pub.kind == rtc.TrackKind.KIND_AUDIO:
                        subscriber = track_pub
                        break
            if subscriber:
                break

        if not subscriber:
            print("No host audio found!")
            return

        track = await room.subscribe(subscriber.track_sid)
        if not isinstance(track, rtc.AudioTrack):
            return

        frame_queue = asyncio.Queue()
        conversation_history = [{"role": "system", "content": self.agent.instructions}]

        async def audio_frame_loop():
            async for frame in rtc.AudioStream(track):
                await frame_queue.put(frame)
            await frame_queue.put(None)

        asyncio.create_task(audio_frame_loop())

        while True:
            frames = []
            try:
                # 等待第一帧
                first = await frame_queue.get()
                if first is None:
                    break
                frames.append(first)

                # 继续收 1.5 秒或直到静音
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

                # ASR（简化：传整个 buffer）
                audio_buffer = bytearray()
                for f in frames:
                    audio_buffer.extend(f.data)

                # 模拟转文本（实际应传给 FasterWhisper）
                # 这里我们直接用一个临时队列模拟 stream_recognize
                temp_q = asyncio.Queue()
                for f in frames:
                    await temp_q.put(f)
                await temp_q.put(None)
                user_text = await self.asr.stream_recognize(temp_q)

                if not user_text or len(user_text.strip()) < 2:
                    # 听不清 → 主动请求重复
                    confused = "Sorry, say that once more?"
                    raw_resp = f"{confused} @@play_recording('scanning')@@ @@set_rgb_solid(100, 100, 255)@@"
                    speech = extract_and_execute_actions(self.agent, raw_resp)
                    await self.tts.synthesize_and_play(speech)
                    continue

                print(f"👤 User: {user_text}")
                conversation_history.append({"role": "user", "content": user_text})

                # LLM
                raw_response = await self.llm.chat(conversation_history)
                speech_text = extract_and_execute_actions(self.agent, raw_response)
                print(f"🤖 LeLamp: {speech_text}")

                conversation_history.append({"role": "assistant", "content": raw_response})
                await self.tts.synthesize_and_play(speech_text)

            except Exception as e:
                print(f"⚠️ Audio loop error: {e}")
                continue
