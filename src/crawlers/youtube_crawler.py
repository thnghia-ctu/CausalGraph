import yt_dlp
from faster_whisper import WhisperModel
import os
import re
import uuid
import unicodedata
from .base_crawler import BaseCrawler


class YouTubeCrawler(BaseCrawler):
    source_type = "youtube"
    _model = None

    def __init__(self, url):
        super().__init__(url)

        if YouTubeCrawler._model is None:
            YouTubeCrawler._model = WhisperModel("medium")

        self.model = YouTubeCrawler._model

    def fetch(self):
        filename = f"temp_{uuid.uuid4().hex}.%(ext)s"

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': filename,
            'quiet': True,
            'noplaylist': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=True)
            audio_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"

        return audio_path

    def parse(self, audio_path):
        try:
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=5
            )

            text = "\n".join(
                seg.text.strip()
                for seg in segments
                if seg.text.strip()
            )

            return text

        except Exception as e:
            print(f"Transcription error: {e}")
            raise

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def postprocess(self, text):
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def save(self, text, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Source: {self.url}\n\n")
            f.write(text)
