from pathlib import Path
from openai import OpenAI


class TTSClient:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.speach_file_path = Path(__file__).parent.parent.parent / "voices" / "speach.mp3" 
        self.speach_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.client = OpenAI(api_key=self.settings.OPENAI_API_KEY)

    def generate(self, text: str):
        with self.client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            instructions=(
                "Speak in a warm, cheerful, and friendly tone. "
                "Sound natural and human, not robotic. "
                "Maintain a relaxed, moderate pace—do not rush. "
                "Use gentle pauses between sentences and key ideas. "
                "Keep the energy positive and welcoming, with soft emphasis "
                "on important words."
            ),
        ) as response:
            response.stream_to_file(self.speach_file_path)
        return self.speach_file_path
