import os
import traceback
from pathlib import Path
from playsound3 import playsound
from dotenv import load_dotenv

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def main():
    try:
        os.system("cls" if os.name == "nt" else "clear")

        # Load .env from the same folder as this script
        load_dotenv(override=True)

        azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_deployment = os.getenv("STT_MODEL_NAME")

        if not azure_openai_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT is missing or empty in .env")

        if not model_deployment:
            raise ValueError("STT_MODEL_NAME is missing or empty in .env")

        file_path = Path(__file__).parent / "speech.wav"

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        print(f"Endpoint: {azure_openai_endpoint}")
        print(f"Deployment: {model_deployment}")
        print(f"Audio file: {file_path}")

        playsound(str(file_path))

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default"
        )

        client = AzureOpenAI(
            azure_endpoint=azure_openai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="2024-12-01-preview",
        )

        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model=model_deployment,
                file=audio_file,
                response_format="text"
            )

        print("\nTranscription:")
        print(transcription)

    except Exception:
        traceback.print_exc()


if __name__ == "__main__":
    main()