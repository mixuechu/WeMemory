#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试 Gemini 2.5 响应"""
import os
import json
from dotenv import load_dotenv
load_dotenv()

from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel

PROJECT_ID = os.getenv("VITE_GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("VITE_GOOGLE_CLOUD_LOCATION")
credentials_json = os.getenv("VITE_GOOGLE_APPLICATION_CREDENTIALS_JSON")

creds_dict = json.loads(credentials_json)
credentials = service_account.Credentials.from_service_account_info(creds_dict)

vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)

test_prompt = "Say hello in 10 words"

model = GenerativeModel("gemini-2.5-flash")

response = model.generate_content(
    test_prompt,
    generation_config={"max_output_tokens": 2000}
)

print("Response 对象属性:")
print(f"  - dir(response): {[x for x in dir(response) if not x.startswith('_')]}")
print()

print("Response.text:")
print(f"  {response.text}")
print()

print("Response.candidates:")
for i, candidate in enumerate(response.candidates):
    print(f"  Candidate {i}:")
    print(f"    finish_reason: {candidate.finish_reason}")
    print(f"    content: {candidate.content}")
    print(f"    content.parts: {candidate.content.parts}")
    if candidate.content.parts:
        for j, part in enumerate(candidate.content.parts):
            print(f"      Part {j}: {part.text if hasattr(part, 'text') else part}")
print()

if hasattr(response, 'usage_metadata'):
    print("Usage metadata:")
    print(f"  {response.usage_metadata}")
