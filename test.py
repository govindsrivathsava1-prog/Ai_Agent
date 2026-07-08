import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key = os.environ["GEMINI_API_KEY"])



# response = client.models.embed_content(
#     model = "text-embedding-004",
#     contents = "Hello World"
# )

# print(response)

for model in client.models.list():
    print(model)
                      