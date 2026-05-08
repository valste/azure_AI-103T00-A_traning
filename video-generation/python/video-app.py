import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import base64
import mimetypes
from pathlib import Path

import get_costs as gc

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

load_dotenv(override=True)

endpoint = os.getenv("OPENAI_BASE_URL")
model_deployment = os.getenv("MODEL_DEPLOYMENT")

if not endpoint:
    raise ValueError("OPENAI_BASE_URL is missing from your .env file.")

if not model_deployment:
    raise ValueError("MODEL_DEPLOYMENT is missing from your .env file.")


# ------------------------------------------------------------
# Azure OpenAI authentication
# ------------------------------------------------------------

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default",
)

client = OpenAI(
    base_url=endpoint,
    api_key=token_provider,
)


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------


def get_input_with_default(message, default_value):
    """
    Prompt the user for input.
    Pressing Enter returns the default value.
    """

    value = input(f"{message} [{default_value}]: ").strip()

    if value == "":
        return default_value

    return value


def log_video_job(video, label, planned_size=None, planned_seconds=None):
    """
    Logs available metadata for a Sora video task.

    Cost is tracked by:
    - model
    - resolution
    - billable video seconds
    - number of submitted jobs
    """

    video_dict = video.model_dump(exclude_none=True)

    size = video_dict.get("size") or planned_size
    seconds = video_dict.get("seconds") or planned_seconds

    print(f"\n=== Video job info: {label} ===")
    print(f"  Video ID:                {video_dict.get('id')}")
    print(f"  Model:                   {video_dict.get('model') or model_deployment}")
    print(f"  Status:                  {video_dict.get('status')}")
    print(f"  Progress:                {video_dict.get('progress')}")
    print(f"  Size:                    {size}")
    print(f"  Billable video seconds:  {gc.parse_seconds(seconds)}")
    print()


def plan_and_log_cost(operation, size, seconds):
    """
    Uses get_costs.py as-is to estimate and log planned cost.
    """

    estimated_cost = gc.log_planned_video_cost(
        operation=operation,
        model=model_deployment,
        size=size,
        seconds=seconds,
        price_per_second=gc.sora_price_per_second,
    )

    return estimated_cost


def poll_video_status(video_id):
    """
    Poll the video status every 20 seconds until it completes, fails, or is cancelled.
    """

    video = client.videos.retrieve(video_id)

    while video.status not in ["completed", "failed", "cancelled"]:
        print(f"Status: {video.status}. Waiting 20 seconds...")
        time.sleep(20)
        video = client.videos.retrieve(video_id)

    if video.status == "completed":
        print("Video successfully completed!")
    else:
        print(f"Video creation ended with status: {video.status}")

    return video


def download_video(video_id, output_filename="output.mp4"):
    """
    Download the completed video to a local MP4 file.
    """

    print(f"Downloading video {video_id}...")

    content = client.videos.download_content(
        video_id,
        variant="video",
    )

    content.write_to_file(output_filename)

    print(f"Saved video to {output_filename}")


# ------------------------------------------------------------
# Scenario 1: Text-to-video
# ------------------------------------------------------------


def run_text_to_video_scenario():
    """
    Generate a video from a text prompt.
    """

    print("\n=== Scenario 1: Text-to-video ===")
    print(
        "Apply the default values by keying enter or enter your own and press Enter\n"
    )

    prompt = get_input_with_default(
        "Enter text prompt",
        "A peaceful mountain lake at sunrise with mist rising from the water",
    )

    size = get_input_with_default(
        "Enter video size",
        "1280x1280",
    )

    seconds = get_input_with_default(
        "Enter video duration in seconds",
        "4",
    )

    output_filename = get_input_with_default(
        "Enter output filename",
        "from_text_to_video.mp4",
    )

    operation = "text-to-video"

    estimated_cost = plan_and_log_cost(
        operation=operation,
        size=size,
        seconds=seconds,
    )

    video = client.videos.create(
        model=model_deployment,
        prompt=prompt,
        size=size,
        seconds=seconds,
    )

    gc.record_estimated_cost(operation, estimated_cost)

    print(f"Video creation started. ID: {video.id}")
    print(f"Initial status: {video.status}")

    log_video_job(
        video,
        label="Initial text-to-video request",
        planned_size=size,
        planned_seconds=seconds,
    )

    video = poll_video_status(video.id)

    log_video_job(
        video,
        label="Completed text-to-video request",
        planned_size=size,
        planned_seconds=seconds,
    )

    if video.status == "completed":
        download_video(video.id, output_filename)
    else:
        print("Text-to-video generation did not complete, so it was not downloaded.")

    return video


# ------------------------------------------------------------
# Scenario 2: Remix video
# ------------------------------------------------------------


def run_remix_video_scenario():
    """
    Remix an existing video.
    """

    print("\n=== Scenario 2: Remix video ===")

    original_video_id = input("Enter the video ID to remix: ").strip()

    if not original_video_id:
        print("No video ID provided. Remix cancelled.")
        return None

    prompt = get_input_with_default(
        "Enter remix prompt",
        "Shift the color palette to warm sunset tones with golden light",
    )

    size = get_input_with_default(
        "Enter estimated video size for cost tracking",
        "1280x720",
    )

    seconds = get_input_with_default(
        "Enter estimated video duration in seconds for cost tracking",
        "4",
    )

    output_filename = get_input_with_default(
        "Enter output filename",
        "remixed_video.mp4",
    )

    operation = "video remix"

    estimated_cost = plan_and_log_cost(
        operation=operation,
        size=size,
        seconds=seconds,
    )

    video = client.videos.remix(
        video_id=original_video_id,
        prompt=prompt,
    )

    gc.record_estimated_cost(operation, estimated_cost)

    print(f"Remix started. New video ID: {video.id}")
    print(f"Initial status: {video.status}")

    log_video_job(
        video,
        label="Initial remix request",
        planned_size=size,
        planned_seconds=seconds,
    )

    video = poll_video_status(video.id)

    log_video_job(
        video,
        label="Completed remix request",
        planned_size=size,
        planned_seconds=seconds,
    )

    if video.status == "completed":
        download_video(video.id, output_filename)
    else:
        print("Remixed video was not completed, so it was not downloaded.")

    return video


# ------------------------------------------------------------
# Scenario 3: Image-to-video
# ------------------------------------------------------------


def run_image_to_video_scenario():
    """
    Generate a video using a reference image.
    """

    print("\n=== Scenario 3: Image-to-video ===")

    image_path = get_input_with_default(
        "Enter reference image path",
        "reference_720x1280.png",
    )

    print(f"Checking for reference image at: {image_path}")

    if not os.path.exists(image_path):
        print(f"Reference image not found: {image_path}")
        return None

    prompt = get_input_with_default(
        "Enter image-to-video prompt",
        """A 4-second cinematic macro video using the reference image as the starting frame: 
        a glossy black apple sits centered on a soft gray studio background in gentle falling rain. 
        The oval opening in the apple subtly moves as a cute, friendly worm slowly crawls out. 
        The worm has soft beige skin, a rounded face, tiny expressive eyes, 
        and a warm charming personality — not scary, not gross.

        0–1s: The apple remains still, rain streaks down, subtle reflections on the glossy black skin.
        1–2.5s: The worm gently pushes forward from inside the oval hole, wiggling naturally and looking curious.
        2.5–4s: The worm fully emerges halfway out of the apple, turns toward the camera, pauses, and gives a 
        friendly smile directly to the viewer.

        Style: whimsical but realistic, premium studio lighting, shallow depth of field, 
        detailed rain droplets, smooth natural motion, clean cinematic composition. Keep the apple shape, 
        black glossy surface, green leaf, gray background, and existing opening consistent with the reference image. 
        Avoid horror, gore, exaggerated slime, deformation, extra insects, or cartoonish overacting.""",
    )

    size = get_input_with_default(
        "Enter video size",
        "720x1280",
    )

    seconds = get_input_with_default(
        "Enter video duration in seconds",
        "4",
    )

    output_filename = get_input_with_default(
        "Enter output filename",
        "happy_worm.mp4",
    )

    operation = "image-to-video"

    estimated_cost = plan_and_log_cost(
        operation=operation,
        size=size,
        seconds=seconds,
    )

    video = client.videos.create(
        model=model_deployment,
        prompt=prompt,
        size=size,
        seconds=seconds,
        input_reference=Path(image_path),
    )

    gc.record_estimated_cost(operation, estimated_cost)

    print(f"Video creation started. ID: {video.id}")
    print(f"Initial status: {video.status}")

    log_video_job(
        video,
        label="Initial image-to-video request",
        planned_size=size,
        planned_seconds=seconds,
    )

    video = poll_video_status(video.id)

    log_video_job(
        video,
        label="Completed image-to-video request",
        planned_size=size,
        planned_seconds=seconds,
    )

    if video.status == "completed":
        download_video(video.id, output_filename)
    else:
        print("Image-based video was not completed, so it was not downloaded.")

    return video


# ------------------------------------------------------------
# Main application
# ------------------------------------------------------------


def main():
    os.system("cls" if os.name == "nt" else "clear")

    print("=== Video Generation Application ===\n")
    print(f"Endpoint: {endpoint}")
    print(f"Model deployment: {model_deployment}")

    print("\n=== Cost tracking configuration ===")
    print(f"Cost currency: {gc.cost_currency}")
    print(
        f"Configured price per second: "
        f"{gc.format_money(gc.sora_price_per_second, gc.cost_currency)}"
    )
    print(f"Price source: {gc.price_source}")

    if gc.max_total_estimated_cost > 0:
        print(
            f"Budget limit: "
            f"{gc.format_money(gc.max_total_estimated_cost, gc.cost_currency)}"
        )
        print(f"Budget source: {gc.budget_source}")
    else:
        print("Budget limit: disabled")

    print("\nSelect a video generation scenario and press Enter:")
    print("1) Text-to-video")
    print("2) Remix video")
    print("3) Image-to-video")
    print("q) Quit")

    choice = input("\nYour choice: ").strip().lower()

    try:
        if choice == "1":
            run_text_to_video_scenario()

        elif choice == "2":
            run_remix_video_scenario()

        elif choice == "3":
            run_image_to_video_scenario()

        elif choice in ["q", "quit", "exit"]:
            print("Exiting application.")
            return

        else:
            print(f"Invalid selection: {choice}")
            print("Please choose 1, 2, 3, or q.")
            return

        print("\n=== Video generation complete ===")

        print(
            f"Final cumulative estimated cost: "
            f"{gc.format_money(gc.estimated_total_cost, gc.cost_currency)}"
        )

    except Exception as ex:
        print(f"\nError: {ex}")


if __name__ == "__main__":
    main()
