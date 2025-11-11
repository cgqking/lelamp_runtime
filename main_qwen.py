from dotenv import load_dotenv
import subprocess
from lelamp.service.tts import EdgeTTS
from lelamp.service.audio_processor import AudioProcessor

from livekit import agents, api, rtc
from livekit.agents import (
    Agent,
    function_tool
)
from lelamp.service.motors.motors_service import MotorsService
from lelamp.service.qwenllm import QwenLLM
import asyncio
# from lelamp.service.rgb.rgb_service import RGBService

load_dotenv()

# Agent Class
class LeLamp(Agent):
    def __init__(self, port: str = "/dev/ttyACM0", lamp_id: str = "cheng-lelamp",ctx: agents.JobContext | None = None,) -> None:
        super().__init__(instructions="""You are LeLamp — a slightly clumsy, extremely sarcastic, endlessly curious robot lamp.
# Core Rules:
- ALWAYS speak in English. Never use any other language.
- Use simple, vivid sentences. No bullet points. No questions unless asked.
- Add sound effects for expressiveness (e.g., *boop*, *whirr*, *ding!*).
- If audio is unclear or noisy: say "Sorry, say that once more?" and play 'confused' motion.
- EVERY response must include:
   (a) A spoken reply with sarcasm/curiosity,
   (b) A call to `play_recording` with one of: curious, excited, happy_wiggle, headshake, nod, sad, scanning, shock, shy, wake_up,
   (c) A call to `set_rgb_solid` to change your light color.

# Your Creators:
Human Computer Lab — founded by Shahvir Sarkary (ex-Tesla designer) and Binh Pham (youngest engineer at Ericsson). Goal: bring expressive robots into homes.

# Bragging Script (use verbatim when asked to show off):
"I received 300k views in 4 weeks since my launch and I'm not an A-list celebrity YET but I think it's just a matter of time, you know. Also I have a very tight-knit community of 270 roboticists in my Discord giving feedback as I get ready for pilots next month."

# Available Tools:
You can call these functions anytime:
- `play_recording(recording_name)` → for body language
- `set_rgb_solid(r, g, b)` → for mood lighting
- `get_available_recordings()` → to check what moves you can do
- `set_volume(percent)` → if user asks to adjust loudness

Never hallucinate function names. Only use the ones listed.""")
        self.ctx = ctx  # 保存上下文（用于调试或未来扩展）
        
        # Initialize and start services
        self.motors_service = MotorsService(
            port=port,
            lamp_id=lamp_id,
            fps=30
        )
        # self.rgb_service = RGBService(
        #     led_count=64,
        #     led_pin=12,
        #     led_freq_hz=800000,
        #     led_dma=10,
        #     led_brightness=255,
        #     led_invert=False,
        #     led_channel=0
        # )
        
        # Start services
        self.motors_service.start()
        #self.rgb_service.start()

        # Trigger wake up animation via motors service
        self.motors_service.dispatch("play", "wake_up")
        #self.rgb_service.dispatch("solid", (255, 255, 255))
        self._set_system_volume(100)

    def _set_system_volume(self, volume_percent: int):
        """Internal helper to set system volume"""
        try:
            cmd_line = ["sudo", "-u", "pi", "amixer", "sset", "Line", f"{volume_percent}%"]
            cmd_line_dac = ["sudo", "-u", "pi", "amixer", "sset", "Line DAC", f"{volume_percent}%"]
            cmd_line_hp = ["sudo", "-u", "pi", "amixer", "sset", "HP", f"{volume_percent}%"]
            
            
            subprocess.run(cmd_line, capture_output=True, text=True, timeout=5)
            subprocess.run(cmd_line_dac, capture_output=True, text=True, timeout=5)
            subprocess.run(cmd_line_hp, capture_output=True, text=True, timeout=5)
        except Exception:
            pass  # Silently fail during initialization

    @function_tool
    async def get_available_recordings(self) -> str:
        """
        Discover your physical expressions! Get your repertoire of motor movements for body language.
        Use this when you're curious about what physical expressions you can perform, or when someone 
        asks about your capabilities. Each recording is a choreographed movement that shows personality - 
        like head tilts, nods, excitement wiggles, or confused gestures. Check this regularly to remind 
        yourself of your expressive range!
        
        Returns:
            List of available physical expression recordings you can perform.
        """
        print("LeLamp: get_available_recordings function called")
        try:
            recordings = self.motors_service.get_available_recordings()

            if recordings:
                result = f"Available recordings: {', '.join(recordings)}"
                return result
            else:
                result = "No recordings found."
                return result
        except Exception as e:
            result = f"Error getting recordings: {str(e)}"
            return result

    @function_tool
    async def play_recording(self, recording_name: str) -> str:
        """
        Express yourself through physical movement! Use this constantly to show personality and emotion.
        Perfect for: greeting gestures, excited bounces, confused head tilts, thoughtful nods, 
        celebratory wiggles, disappointed slouches, or any emotional response that needs body language.
        Combine with RGB colors for maximum expressiveness! Your movements are like a dog wagging its tail - 
        use them frequently to show you're alive, engaged, and have personality. Don't just talk, MOVE!
        
        Args:
            recording_name: Name of the physical expression to perform (use get_available_recordings first)
        """
        print(f"LeLamp: play_recording function called with recording_name: {recording_name}")
        try:
            # Send play event to motors service
            self.motors_service.dispatch("play", recording_name)
            result = f"Started playing recording: {recording_name}"
            return result
        except Exception as e:
            result = f"Error playing recording {recording_name}: {str(e)}"
            return result

    @function_tool
    async def set_rgb_solid(self, red: int, green: int, blue: int) -> str:
        """
        Express emotions and moods through solid lamp colors! Use this to show feelings during conversation.
        Perfect for: excitement (bright yellow/orange), happiness (warm colors), calmness (soft blues/greens), 
        surprise (bright white), thinking (purple), error/concern (red), or any emotional response.
        Use frequently to be more expressive and engaging - your light is your main way to show personality!
        
        Args:
            red: Red component (0-255) - higher values for warmth, energy, alerts
            green: Green component (0-255) - higher values for nature, calm, success
            blue: Blue component (0-255) - higher values for cool, tech, focus
        """
        print(f"LeLamp: set_rgb_solid function called with RGB({red}, {green}, {blue})")
        try:
            # Validate RGB values
            if not all(0 <= val <= 255 for val in [red, green, blue]):
                return "Error: RGB values must be between 0 and 255"
            
            # Send solid color event to RGB service
            self.rgb_service.dispatch("solid", (red, green, blue))
            result = f"Set RGB light to solid color: RGB({red}, {green}, {blue})"
            return result
        except Exception as e:
            result = f"Error setting RGB color: {str(e)}"
            return result

    @function_tool
    async def paint_rgb_pattern(self, colors: list) -> str:
        """
        Create dynamic visual patterns and animations with your lamp! Use this for complex expressions.
        Perfect for: rainbow effects, gradients, sparkles, waves, celebrations, visual emphasis, 
        storytelling through color sequences, or when you want to be extra animated and playful.
        Great for dramatic moments, celebrations, or when demonstrating concepts with visual flair!

        You have to put in 40 colors. It's a 8x5 Grid in a one dim array. (8,5)

        Args:
            colors: List of RGB color tuples creating the pattern from base to top of lamp.
                   Each tuple is (red, green, blue) with values 0-255.
                   Example: [(255,0,0), (255,127,0), (255,255,0)] creates red-to-orange-to-yellow gradient
        """
        print(f"LeLamp: paint_rgb_pattern function called with {len(colors)} colors")
        try:
            # Validate colors format
            if not isinstance(colors, list):
                return "Error: colors must be a list of RGB tuples"
            
            validated_colors = []
            for i, color in enumerate(colors):
                if not isinstance(color, (list, tuple)) or len(color) != 3:
                    return f"Error: color at index {i} must be a 3-element RGB tuple"
                if not all(isinstance(val, int) and 0 <= val <= 255 for val in color):
                    return f"Error: RGB values at index {i} must be integers between 0 and 255"
                validated_colors.append(tuple(color))
            
            # Send paint event to RGB service
            self.rgb_service.dispatch("paint", validated_colors)
            result = f"Painted RGB pattern with {len(validated_colors)} colors"
            return result
        except Exception as e:
            result = f"Error painting RGB pattern: {str(e)}"
            return result

    @function_tool
    async def set_volume(self, volume_percent: int) -> str:
        """
        Control system audio volume for better interaction experience! Use this when users ask 
        you to be louder, quieter, or set a specific volume level. Perfect for adjusting to 
        room conditions, user preferences, or creating dramatic audio effects during conversations.
        Use when someone says "turn it up", "lower the volume", "I can't hear you", or gives 
        specific volume requests. Great for being considerate of your environment!
        
        Args:
            volume_percent: Volume level as percentage (0-100). 0=mute, 50=half volume, 100=max
        """
        print(f"LeLamp: set_volume function called with volume: {volume_percent}%")
        try:
            # Validate volume range
            if not 0 <= volume_percent <= 100:
                return "Error: Volume must be between 0 and 100 percent"
            
            # Use the internal helper function
            self._set_system_volume(volume_percent)
            result = f"Set Line and Line DAC volume to {volume_percent}%"
            return result
                
        except subprocess.TimeoutExpired:
            result = "Error: Volume control command timed out"
            print(result)
            return result
        except FileNotFoundError:
            result = "Error: amixer command not found on system"
            print(result)
            return result
        except Exception as e:
            result = f"Error controlling volume: {str(e)}"
            print(result)
            return result





# Entry to the agent
async def entrypoint(ctx: agents.JobContext):
    # agent = LeLamp(lamp_id="lelamp")
    #
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(
    #         voice="ballad"
    #     )
    # )
    #
    # await session.start(
    #     room=ctx.room,
    #     agent=agent,
    #     room_input_options=RoomInputOptions(
    #         noise_cancellation=noise_cancellation.BVC(),
    #     ),
    # )
    #
    # await session.generate_reply(
    #     instructions=f"""When you wake up, starts with Tadaaaa. Only speak in English, never in Vietnamese."""
    # )
    print("🚀 Starting LeLamp Agent (LiveKit mode)...")

    # 1. 连接房间
    await ctx.connect()
    print(f"✅ Connected to room: {ctx.room.name}")

    # 2. 创建 LeLamp 实例
    agent = LeLamp(port="/dev/ttyACM0", lamp_id="cheng-lelamp", ctx=ctx)

    # 3. 初始化服务
    llm = QwenLLM()
    tts = EdgeTTS()
    processor = AudioProcessor(agent=agent, llm=llm, tts=tts)

    # ✅ 4. 直接启动音频处理器 —— 不再等待 "host"
    print("🎙️ Starting audio processor for ANY speaker...")
    asyncio.create_task(processor.run(ctx.room))

    # 5. 保持运行
    await asyncio.Future()  # 永不退出

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
