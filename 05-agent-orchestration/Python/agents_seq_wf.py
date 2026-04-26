"""
The code in the exsercise is obsolete. 
requiremnets.txt should be updated to agent-framework==0.2.0 and the code should be updated to use FoundryChatClient instead of AzureAIAgentClient, and SequentialBuilder instead of OrchestrationBuilder.
"""


# Add references
import os
import asyncio
from typing import cast
from dotenv import load_dotenv

from azure.identity import AzureCliCredential
from agent_framework import Agent, Message
from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import SequentialBuilder

load_dotenv(override=True)


async def main():
    project_endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model_deployment = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]

    summarizer_instructions = """
    Summarize the customer's feedback in one short sentence. Keep it neutral and concise.
    """

    classifier_instructions = """
    Classify the feedback as one of the following: Positive, Negative, or Feature request.
    """

    action_instructions = """
    Based on the summary and classification, suggest the next action in one short sentence.
    """

    # Modern replacement for AzureAIAgentClient
    chat_client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model_deployment,
        credential=AzureCliCredential(),
    )

    summarizer = Agent(
        client=chat_client,
        name="summarizer",
        instructions=summarizer_instructions,
    )

    classifier = Agent(
        client=chat_client,
        name="classifier",
        instructions=classifier_instructions,
    )

    action = Agent(
        client=chat_client,
        name="action",
        instructions=action_instructions,
    )

    feedback = """
    I use the dashboard every day to monitor metrics, and it works well overall. 
    But when I'm working late at night, the bright screen is really harsh on my eyes. 
    If you added a dark mode option, it would make the experience much more comfortable.
    """

    workflow = SequentialBuilder(
        participants=[summarizer, classifier, action]
    ).build()

    outputs: list[list[Message]] = []

    async for event in workflow.run(
        f"Customer feedback: {feedback}",
        stream=True,
    ):
        if event.type == "output":
            outputs.append(cast(list[Message], event.data))

    if outputs:
        for i, msg in enumerate(outputs[-1], start=1):
            name = msg.author_name or (
                "assistant" if msg.role == "assistant" else "user"
            )
            print(f"{'-' * 60}\n{i:02d} [{name}]\n{msg.text}")


if __name__ == "__main__":
    asyncio.run(main())