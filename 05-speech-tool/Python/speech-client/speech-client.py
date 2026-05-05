from dotenv import load_dotenv
import os

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


def main():
    try:
        os.system("cls" if os.name == "nt" else "clear")

        load_dotenv(override=True)

        foundry_endpoint = os.getenv("FOUNDRY_ENDPOINT")
        agent_name = os.getenv("AGENT_NAME")

        if not foundry_endpoint:
            raise ValueError("FOUNDRY_ENDPOINT is missing. Add it to your .env file.")

        if not agent_name:
            raise ValueError("AGENT_NAME is missing. Add it to your .env file.")

        print(f"Using endpoint: {foundry_endpoint}")
        print(f"Using agent: {agent_name}")

        project_client = AIProjectClient(
            endpoint=foundry_endpoint,
            credential=DefaultAzureCredential(),
        )

        openai_client = project_client.get_openai_client()

        # Create a conversation so the agent can maintain state
        conversation = openai_client.conversations.create()

        while True:
            prompt = input("User prompt (or 'quit'): ").strip()

            if prompt.lower() == "quit" or len(prompt) == 0:
                break

            response = openai_client.responses.create(
                conversation=conversation.id,
                input=prompt,
                extra_body={
                    "agent_reference": {
                        "name": agent_name,
                        "type": "agent_reference",
                    }
                },
            )

            print(f"{agent_name}: {response.output_text}")

    except Exception as ex:
        print(f"Error: {ex}")


if __name__ == "__main__":
    main()
