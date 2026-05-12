from dotenv import load_dotenv
import os
import sys
import json
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential


def main():

    # Clear the console
    os.system("cls" if os.name == "nt" else "clear")

    try:

        # Get the business card
        image_file = "biz-card-1.png"
        if len(sys.argv) > 1:
            image_file = sys.argv[1]

        # Get config settings
        load_dotenv(override=True)
        ai_svc_endpoint = os.getenv("ENDPOINT")
        ai_svc_key = os.getenv("KEY")
        analyzer = os.getenv("ANALYZER_NAME")

        # Analyze the business card
        analyze_card(image_file, analyzer, ai_svc_endpoint, ai_svc_key)

        print("\n")

    except Exception as ex:
        print(ex)


def analyze_card(image_file, analyzer, endpoint, key):

    # Use Content Understanding to analyze the image
    print(f"Analyzing {image_file}")

    # Create the Content Understanding client
    client = ContentUnderstandingClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    # Read the image data
    with open(image_file, "rb") as file:
        image_data = file.read()

    # Submit the image for analysis
    print("Submitting request...")
    poller = client.begin_analyze_binary(analyzer_id=analyzer, binary_input=image_data)

    # Wait for the analysis to complete
    result = poller.result()
    print("Analysis succeeded:\n")

    # Save JSON results to a file
    output_file = f"results_{image_file.strip(".png")}.json"
    with open(output_file, "w") as json_file:
        json.dump(dict(result), json_file, indent=4, default=str)
        print(f"Response saved in {output_file}\n")

    # Iterate through the contents and extract fields
    for content in result.contents:
        if hasattr(content, "fields") and content.fields:
            for field_name, field_data in content.fields.items():
                value = field_data.value if hasattr(field_data, "value") else None
                print(f"{field_name}: {value}")


if __name__ == "__main__":
    main()
