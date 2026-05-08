import os
import json
import base64

# Add references
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI


def main():

    # Clear the console
    os.system("cls" if os.name == "nt" else "clear")

    try:
        # Get configuration settings
        load_dotenv(override=True)
        endpoint = os.getenv("ENDPOINT")
        model_deployment = os.getenv("MODEL_DEPLOYMENT")

        if not endpoint:
            raise ValueError("ENDPOINT is missing from your .env file.")

        if not model_deployment:
            raise ValueError("MODEL_DEPLOYMENT is missing from your .env file.")

        # Initialize the client
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True,
            ),
            "https://cognitiveservices.azure.com/.default",
        )

        client = OpenAI(
            base_url=endpoint,
            # Pass the provider itself so the SDK can refresh the auth token when needed.
            # This is the auth token provider, not the image generation usage tokens.
            api_key=token_provider,
        )

        img_no = 0

        # Loop until the user types 'quit'
        while True:
            input_text = input("Enter the prompt (or type 'quit' to exit): ")

            if input_text.lower() == "quit":
                break

            if len(input_text) == 0:
                print("Please enter a prompt.")
                continue

            # Generate an image
            img = client.images.generate(
                model=model_deployment,
                prompt=input_text,
                size="1024x1024",
                n=1,
            )

            # Log model token usage for this image request/response
            log_image_token_usage(img)

            json_response = json.loads(img.model_dump_json())
            image_data = json_response["data"][0].get("b64_json")

            if not image_data:
                raise ValueError("No base64 image data was returned.")

            image_data_in_bytes = base64.b64decode(image_data)

            # Save the image
            img_no += 1
            file_name = f"image_{img_no}.png"
            save_image(image_data_in_bytes, file_name)

    except Exception as ex:
        print(f"Error: {ex}")


def log_image_token_usage(image_response):
    response_dict = image_response.model_dump(exclude_none=True)
    usage = response_dict.get("usage")

    print("\nImage generation token usage:")

    if usage is None:
        print("  Usage metadata was not returned by the service.")
        print("  This is normal for some Azure OpenAI / Foundry image responses.")
        print()
        return

    print(f"  Request/input tokens:   {usage.get('input_tokens')}")
    print(f"  Response/output tokens: {usage.get('output_tokens')}")
    print(f"  Total tokens:           {usage.get('total_tokens')}")

    input_details = usage.get("input_tokens_details") or {}
    output_details = usage.get("output_tokens_details") or {}

    if input_details:
        print("  Input token details:")
        print(f"    Text input tokens:  {input_details.get('text_tokens')}")
        print(f"    Image input tokens: {input_details.get('image_tokens')}")

    if output_details:
        print("  Output token details:")
        print(f"    Text output tokens:  {output_details.get('text_tokens')}")
        print(f"    Image output tokens: {output_details.get('image_tokens')}")

    print()


def save_image(image_data, file_name):
    # Set the directory for the stored image
    image_dir = os.path.join(os.getcwd(), "images")

    # If the directory doesn't exist, create it
    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    # Initialize the image path
    image_path = os.path.join(image_dir, file_name)

    # Save the generated image
    with open(image_path, "wb") as image_file:
        image_file.write(image_data)

    print(f"Image saved as {image_path}")


if __name__ == "__main__":
    main()
