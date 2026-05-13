from dotenv import load_dotenv
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def main():
    # Clear the console
    os.system("cls" if os.name == "nt" else "clear")

    try:
        # Get config settings
        load_dotenv(override=True)

        search_endpoint = os.getenv("SEARCH_ENDPOINT")
        query_key = os.getenv("QUERY_KEY")
        index = os.getenv("INDEX_NAME")

        # Get a search client
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index,
            credential=AzureKeyCredential(query_key)
        )

        # Loop until the user types 'quit'
        while True:
            query_text = input("Enter a query (or type 'quit' to exit): ")

            if query_text.lower() == "quit":
                break

            if len(query_text.strip()) == 0:
                print("Please enter a query.")
                continue

            # Clear the console
            os.system("cls" if os.name == "nt" else "clear")

            # Search the index
            found_documents = search_client.search(
                search_text=query_text,
                select=["title", "id", "locations", "persons", "keyPhrases"],
                order_by=["search.score() desc"], #order by relevance score instead
                #order_by=["metadata_storage_name"], #doesn't exist asd index field
                include_total_count=True
            )

            # Parse the results
            print(f"\nSearch returned {found_documents.get_count()} documents:")

            for document in found_documents:
                document_title = document.get("title") or document.get("id") or "<unknown document>"

                print(f"\nDocument: {document_title}")

                print(" - Locations:")
                for location in document.get("locations", []):
                    print(f"   - {location}")

                print(" - People:")
                for person in document.get("persons", []):
                    print(f"   - {person}")

                print(" - Key phrases:")
                for phrase in document.get("keyPhrases", []):
                    print(f"   - {phrase}")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()