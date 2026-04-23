import os
from dotenv import load_dotenv

# Add references
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


load_dotenv(override=True)
endpoint = os.environ["PROJECT_ENDPOINT"]

# Connect to the AI Project client
with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
    project_client.get_openai_client() as openai_client,
):

    # Specify the workflow
    workflow = {"name": "ContosoPay-Customer-Support-Triage"}

    # Create a conversation and run the workflow
    conversation = openai_client.conversations.create()
    print(f"Created conversation (id: {conversation.id})")

    stream = openai_client.responses.create(
        conversation=conversation.id,
        extra_body={
            "agent_reference": {"name": workflow["name"], "type": "agent_reference"}
        },
        input="Start",
        stream=True,  # !!!!! streaming on
    )

    # Process events from the workflow run
    for event in stream:
        if event.type == "response.completed":
            print("\nResponse completed:")
            response = openai_client.responses.retrieve(event.response.id)
            print(f"{response.output_text}")

    # Clean up resources
    openai_client.conversations.delete(conversation_id=conversation.id)
    print("\nConversation deleted")

    """run->Output
    
        $ python workflow.py
        Created conversation (id: conv_e79b6062a2caa262009nfHQXAvT8rXJ0N97WjBcH8jki9pT4nQ)

        Response completed:
        {"customer_issue":"The API returns a 403 error when creating invoices, but the API key hasn't changed.","category":"Technical","confidence":0.95}{"customer_issue":"Is there a way to export all invoices as a CSV?","category":"General","confidence":0.9}{"customer_issue":"Is there a way to export all invoices as a CSV?","category":"General","confidence":0.9}{"customer_issue":"I was charged twice for the same invoice last Friday and my customer is also seeing two receipts. Can someone fix this?","category":"Billing","confidence":0.98}{"customer_issue":"I was charged twice for the same invoice last Friday and my customer is also seeing two receipts. Can someone fix this?","category":"Billing","confidence":0.98}{"customer_issue":"I was charged twice for the same invoice last Friday and my customer is also seeing two receipts. Can someone fix this?","category":"Billing","confidence":0.99}{"customer_issue":"I was charged twice for the same invoice last Friday and my customer is also seeing two receipts. Can someone fix this?","category":"Billing","confidence":0.99}Escalate billing issue to human support team.

        Conversation deleted
    """
