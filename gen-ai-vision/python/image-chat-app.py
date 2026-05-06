import os
import base64
from pathlib import Path
from dotenv import load_dotenv

from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider


def main():
    # Clear the console
    os.system("cls" if os.name == "nt" else "clear")

    orange = "https://microsoftlearning.github.io/mslearn-ai-vision/Labfiles/gen-ai-vision/orange.jpeg"
    selected_image = orange
    selected_fruit_name = "orange"

    # Load dragon fruit image from local file
    image_path = Path("mystery-fruit.jpeg")
    image_format = "jpeg"

    if not image_path.exists():
        raise FileNotFoundError(
            "Could not find mystery-fruit.jpeg. Make sure it is in the same folder "
            "where you run this script."
        )

    with open(image_path, "rb") as image_file:
        image_data = base64.b64encode(image_file.read()).decode("utf-8")

    dragon_fruit = f"data:image/{image_format};base64,{image_data}"

    try:
        # Get configuration settings
        load_dotenv(override=True)
        openai_endpoint = os.getenv("ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        if not openai_endpoint:
            raise ValueError("Missing ENDPOINT in your .env file.")

        if not model_deployment:
            raise ValueError("Missing MODEL_DEPLOYMENT in your .env file.")

        # Create an OpenAI client using Microsoft Entra ID
        credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            credential,
            "https://ai.azure.com/.default"
        )

        client = OpenAI(
            base_url=openai_endpoint,
            api_key=token_provider
        )

        # Initialize system message
        system_message = """
        You are an AI assistant in a grocery store that sells fruit.
        You provide detailed answers to questions about produce.
        """

        # Loop until the user types 'quit'
        while True:
            print(f"\nThe selected fruit is {selected_fruit_name}.")
            print("Type /select to choose a fruit image, or ask a question.")
            print("Type quit to exit.")

            prompt = input("Your prompt: ").strip()

            if prompt.lower() == "quit":
                break

            elif prompt == "":
                print("Please enter a question.\n")
                continue

            elif prompt.lower() == "/select":
                choice = input("Choose 1 for orange, 2 for dragon fruit: ").strip()

                if choice == "1":
                    selected_image = orange
                    selected_fruit_name = "orange"
                    print("Orange selected.")

                elif choice == "2":
                    selected_image = dragon_fruit
                    selected_fruit_name = "dragon fruit"
                    print("Dragon fruit selected.")

                else:
                    print("Invalid selection. Please choose 1 or 2.")

                continue

            else:
                print("Getting a response ...\n")

                response = client.responses.create(
                    model=model_deployment,
                    input=[
                        {
                            "role": "developer",
                            "content": system_message
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": prompt
                                },
                                {
                                    "type": "input_image",
                                    "image_url": selected_image
                                }
                            ]
                        }
                    ]
                )

                print(response.output_text)

    except Exception as ex:
        print(f"Error: {ex}")


if __name__ == "__main__":
    main()