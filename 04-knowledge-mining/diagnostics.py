from dotenv import load_dotenv
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient


load_dotenv(override=True)

search_endpoint = os.getenv("SEARCH_ENDPOINT")
admin_key = os.getenv("ADMIN_KEY")
index_name = os.getenv("INDEX_NAME")

index_client = SearchIndexClient(
    endpoint=search_endpoint,
    credential=AzureKeyCredential(admin_key)
)

index = index_client.get_index(index_name)

print(f"\nFields in index: {index_name}\n")

for field in index.fields:
    print(field.name)