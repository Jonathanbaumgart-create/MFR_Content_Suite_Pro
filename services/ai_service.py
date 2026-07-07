import base64
import json
import requests


class AIService:

    OLLAMA_URL = "http://localhost:11434/api/generate"

    ############################################################

    def analyze_image(self, image_path):

        with open(image_path, "rb") as image:

            encoded = base64.b64encode(
                image.read()
            ).decode("utf-8")

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

                "model": "qwen2.5vl:7b",

                "prompt": prompt,

                "images": [

                    encoded

                ],

                "stream": False

            },

            timeout=300

        )

        response.raise_for_status()

        text = response.json()["response"]

        try:

            return json.loads(text)

        except Exception:

            return {

                "description": text,

                "scene_type": "",

                "activity": "",

                "people_count": 0,

                "apparatus": [],

                "equipment": [],

                "keywords": [],

                "community_score": 50,

                "recruitment_score": 50,

                "education_score": 50,

                "technical_score": 50,

                "overall_score": 50,

                "model": "qwen2.5vl:7b"

            }