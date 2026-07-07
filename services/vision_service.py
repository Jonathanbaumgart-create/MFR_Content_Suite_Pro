import base64
import requests


class VisionService:

    OLLAMA_URL = "http://localhost:11434/api/generate"

    MODEL = "qwen2.5vl:7b"

    ############################################################

    def analyze(self, image_path):

        with open(image_path, "rb") as image:
            encoded = base64.b64encode(image.read()).decode("utf-8")

        prompt = """
Describe this fire service image in detail.
Only describe what can actually be observed.
"""

        response = requests.post(

            self.OLLAMA_URL,

            json={
                "model": self.MODEL,
                "prompt": prompt,
                "images": [encoded],
                "stream": False
            },

            timeout=300

        )

        print("Status:", response.status_code)
        print("Response:")
        print(response.text)

        response.raise_for_status()

        return response.json()["response"]