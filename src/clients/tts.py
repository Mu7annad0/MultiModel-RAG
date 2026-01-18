from pathlib import Path
from openai import AsyncOpenAI


class TTSClient:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.voices_dir = Path(__file__).parent.parent.parent / "voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)
        self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)

    async def generate(self, text: str, response_index: int):
        speach_file_path = self.voices_dir / f"speech_response_{response_index}.mp3"
        async with self.client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            instructions=(
                "Speak in a warm, cheerful, and friendly tone. "
                "Sound natural and human, not robotic. "
                "Use gentle pauses between sentences and key ideas. "
                "Keep the energy positive and welcoming, with soft emphasis "
                "on important words."
            ),
        ) as response:
            await response.stream_to_file(speach_file_path)
        return speach_file_path
