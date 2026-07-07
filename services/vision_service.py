import base64
from abc import ABC, abstractmethod

import requests


class VisionProvider(ABC):

    @abstractmethod
    def analyze(self, image_path: str) -> str:
        pass


class OllamaVisionProvider(VisionProvider):

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "qwen2.5vl:7b"

    def analyze(self, image_path: str) -> str:

        with open(image_path, "rb") as image:
            encoded = base64.b64encode(image.read()).decode("utf-8")

        prompt = """
You are the AI assistant for Morden Fire & Rescue.

Analyze this image.

Return ONLY valid JSON.

Do not wrap the JSON in markdown.

Return this exact structure:

{
  "description":"",
  "scene_type":"",
  "activity":"",
  "people_count":0,
  "apparatus":[],
  "equipment":[],
  "keywords":[],
  "community_score":0,
  "recruitment_score":0,
  "education_score":0,
  "technical_score":0,
  "overall_score":0,
  "facebook_caption":"",
  "instagram_caption":"",
  "model":"qwen2.5vl:7b"
}

Rules:

- Be factual.
- Do not invent information.
- Estimate scores from 0-100.
- Apparatus, equipment and keywords MUST be arrays.
- Return JSON only.
"""

        response = requests.post(
            self.OLLAMA_URL,
            json={
                "model": self.MODEL,
                "prompt": prompt,
                "images": [encoded],
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["response"]


class MockVisionProvider(VisionProvider):

    def analyze(self, image_path: str) -> str:
        return """
{
  "description":"Mock analysis completed for the selected image.",
  "scene_type":"training",
  "activity":"fire service media review",
  "people_count":0,
  "apparatus":[],
  "equipment":[],
  "keywords":["mock","analysis"],
  "community_score":50,
  "recruitment_score":50,
  "education_score":50,
  "technical_score":50,
  "overall_score":50,
  "facebook_caption":"",
  "instagram_caption":"",
  "model":"mock"
}
"""


class VisionService:

    def __init__(self, provider: VisionProvider | None = None):
        self._provider = provider or OllamaVisionProvider()

    def set_provider(self, provider: VisionProvider):
        self._provider = provider

    def analyze(self, image_path: str) -> str:
        return self._provider.analyze(image_path)
