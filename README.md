---
title: Younger Me Chatbot
emoji: 🤖
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: "5.44.1"
app_file: chatbot.py
pinned: false
license: apache-2.0
hardware: zero-gpu
---

# Younger Me Chatbot

A gradio chatbot that allows you to chat with your younger self based on your previous writings and memories.

<img width="512" height="512" alt="younger_me_chatbot" src="https://github.com/user-attachments/assets/b36e69e2-bf10-4f2e-8bdc-eb65185020bf" />

## Usage

1. Clone the repository
2. Install the dependencies via `pip install -r requirements.txt`
3. Add text files to the `docs` directory.
 - See the `example_sources` directory for examples of how to extract text from various sources from your past self.
4. Run the `index_documents.py` script to index the documents
4. Run the `chatbot.py` script to start the chatbot

## Requirements
This app uses ZeroGPU for free GPU access through Hugging Face Spaces. No API keys required!

The app uses:
- **Mistral-7B-Instruct-v0.1** for text generation (7B parameters)
- **sentence-transformers/all-MiniLM-L6-v2** for document embeddings
- ZeroGPU hardware allocation through Hugging Face Spaces

## Contributing

1. Fork the repository
2. Create a new branch
3. Make your changes and commit them
4. Push your changes to your fork

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference