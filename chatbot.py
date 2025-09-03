import gradio as gr
from llama_index.core import VectorStoreIndex, Settings
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path
import json
import subprocess
import os
import spaces

from indexing import ServiceConfig, setup_settings, load_or_create_index
from prompts import DOCUMENT_TOPICS_ANALYSIS_PROMPT, CHATBOT_RESPONSE_PROMPT, CHATBOT_TOPIC_RESPONSE_PROMPT

def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file {config_path} not found. Using defaults.")
        return {
            "person": {"name": "Assistant", "docs_directory": "docs"},
            "chatbot": {"title": "Younger Me Chatbot", "description": "Chat with your younger self"},
            "retrieval": {"similarity_threshold": 0.7, "max_chunks": 5, "context_history_length": 3}
        }

@spaces.GPU
def get_document_topics(index: VectorStoreIndex, config: dict) -> List[dict]:
    """Analyze the indexed documents to identify key life areas/topics."""
    
    # Emoji mapping for common topics
    topic_emojis = {
        "gaming": "🎮", "technology": "💻", "tech": "💻", "coding": "💻", "programming": "💻",
        "music": "🎵", "concerts": "🎤", "songs": "🎵", "bands": "🎸",
        "career": "💼", "work": "💼", "job": "💼", "professional": "💼",
        "travel": "✈️", "adventures": "🗺️", "trips": "🧳", "places": "🌍",
        "relationships": "💝", "friends": "👥", "social": "🤝", "people": "👥",
        "school": "🎓", "education": "📚", "learning": "📖", "college": "🎓",
        "sports": "⚽", "fitness": "💪", "health": "🏃", "exercise": "💪",
        "food": "🍕", "cooking": "👨‍🍳", "eating": "🍽️", "restaurants": "🍴",
        "hobbies": "🎨", "creative": "🎨", "projects": "🛠️", "making": "🔨",
        "family": "👨‍👩‍👧‍👦", "personal": "🧠", "growth": "🌱", "thoughts": "💭",
        "experiences": "⭐", "memories": "📸", "stories": "📖", "life": "🌟"
    }
    
    try:
        # Get a sample of documents to analyze for topics
        retriever = index.as_retriever(similarity_top_k=10)
        sample_nodes = retriever.retrieve("life experiences interests work relationships music travel school")
        
        # Combine content from various documents
        sample_content = "\n\n".join([node.text[:500] for node in sample_nodes[:5]])
        
        from llama_index.core import Settings
        llm = Settings.llm
        
        prompt = DOCUMENT_TOPICS_ANALYSIS_PROMPT.format(content=sample_content)

        response = llm.complete(prompt)
        topic_words = [line.strip().lower() for line in response.text.split('\n') if line.strip() and not line.strip().startswith('#')]
        
        # Create topic objects with emojis
        topics = []
        for word in topic_words[:8]:
            # Find appropriate emoji
            emoji = "🎯"  # default
            for key, emj in topic_emojis.items():
                if key in word.lower():
                    emoji = emj
                    break
            
            topics.append({
                "word": word.capitalize(),
                "emoji": emoji
            })
        
        return topics
    except Exception as e:
        print(f"Error generating topics: {e}")
        return [
            {"word": "Gaming", "emoji": "🎮"},
            {"word": "Music", "emoji": "🎵"},
            {"word": "Career", "emoji": "💼"},
            {"word": "Travel", "emoji": "✈️"},
            {"word": "Friends", "emoji": "👥"},
            {"word": "Hobbies", "emoji": "🎨"}
        ]



@spaces.GPU
def chatbot(input_text, history, index: Optional[VectorStoreIndex] = None, config: dict = None):
    try:
        chatbot_input = ChatbotInput(text=input_text)
        
        # Load config with defaults
        if config is None:
            config = load_config()
        
        if index is None:
            index = load_or_create_index(docs_directory=config["person"]["docs_directory"])
            
        # Use retrieval config settings
        retrieval_config = config.get("retrieval", {})
        max_chunks = retrieval_config.get("max_chunks", 5)
        similarity_threshold = retrieval_config.get("similarity_threshold", 0.7)
        
        # Use retriever to get top chunks and filter by score
        retriever = index.as_retriever(similarity_top_k=max_chunks)
        nodes = retriever.retrieve(chatbot_input.text)

        # Filter chunks with high similarity scores
        high_score_nodes = [node for node in nodes if node.score >= similarity_threshold]
        
        # If no high-scoring nodes, use the top one anyway
        if not high_score_nodes and nodes:
            high_score_nodes = [nodes[0]]

        # Log the matched chunks
        print(f"\n=== Query: {input_text} ===")
        print(f"Found {len(nodes)} total chunks, {len(high_score_nodes)} with score >= 0.7:")
        for i, node in enumerate(high_score_nodes):
            print(f"\nChunk {i+1} (Score: {node.score:.3f}):")
            print(f"Content: {node.text[:200]}...")
            if hasattr(node.node, 'metadata') and node.node.metadata:
                print(f"Metadata: {node.node.metadata}")
        print("=" * 50)

        if not high_score_nodes:
            return "No matching content found."

        # Combine multiple high-scoring chunks as style reference
        combined_content = "\n\n---\n\n".join([node.text for node in high_score_nodes])
        
        # Use the LLM directly to process the content
        from llama_index.core import Settings
        llm = Settings.llm
        
        # Build conversation context using config
        context = ""

        # Generate the response
        prompt = CHATBOT_RESPONSE_PROMPT.format(
            context=context,
            combined_content=combined_content,
            question=chatbot_input.text
        )
        
        # Get complete response (non-streaming)
        response = llm.complete(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"



class ChatbotInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    directory_path: Optional[str] = Field(default="storage")


# Legacy function for backward compatibility - now handled by setup_settings
pass


def main():
    """Main function to launch the chatbot interface."""
    # Run startup script to ensure storage directory is properly set up
    print("Running startup script to check storage setup...")
    try:
        startup_script_path = os.path.join(os.path.dirname(__file__), "startup.sh")
        result = subprocess.run([startup_script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Startup script completed successfully")
            if result.stdout:
                print(result.stdout.strip())
        else:
            print(f"⚠️  Startup script exited with code {result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr.strip()}")
    except Exception as e:
        print(f"⚠️  Could not run startup script: {e}")
        print("Continuing without startup script...")

    # Load configuration
    config = load_config()
    
    # Load the index once at startup
    try:
        index = load_or_create_index(docs_directory=config["person"]["docs_directory"])
        print("Index loaded successfully!")
    except Exception as e:
        print(f"Error loading index: {e}")
        print("Please run 'python index_documents.py' first to create the vector database.")
        return
    
    # Create a wrapper function that uses the loaded index and config
    def chatbot_with_index(message, history):
        return chatbot(message, history, index, config)
    
    # Create custom Gradio interface
    chatbot_config = config.get("chatbot", {})
    
    # Get life topics from documents
    topics = get_document_topics(index, config)
    
    with gr.Blocks(title=chatbot_config.get("title", "AI Chatbot"), css="""
        .scroll-buttons {
            display: flex !important;
            flex-direction: row !important;
            overflow-x: auto !important;
            overflow-y: hidden !important;
            gap: 8px !important;
            padding: 8px 0 !important;
            scrollbar-width: thin !important;
            flex-wrap: nowrap !important;
            width: 100% !important;
        }
        .scroll-buttons::-webkit-scrollbar {
            height: 6px;
        }
        .scroll-buttons::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        .scroll-buttons::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        .scroll-buttons button {
            flex-shrink: 0 !important;
            flex-grow: 0 !important;
            white-space: nowrap !important;
            margin-right: 8px !important;
            min-width: 140px !important;
            max-width: 140px !important;
            height: 40px !important;
            font-size: 13px !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        .chatbot {
            min-height: 200px !important;
            max-height: none !important;
            height: auto !important;
        }
    """) as iface:
        gr.Markdown(f"# {chatbot_config.get('title', 'AI Chatbot')}")
        # gr.Markdown(chatbot_config.get("description", "Chat with AI based on indexed documents."))
        
        chatbot_ui = gr.Chatbot()
        msg = gr.Textbox(label="Message", placeholder="Type your message here...")
        
        gr.Markdown("## Topics")
        with gr.Row(elem_classes="scroll-buttons"):
            all_buttons = []
            
            # Add topic buttons
            for topic in topics:
                btn = gr.Button(f"{topic['emoji']} {topic['word']}")
                all_buttons.append(('topic', btn, topic['word']))
        
        def respond(message, history):
            history = history or []
            # Show user message immediately with loading dots
            history.append([message, "..."])
            yield history, ""
            
            # Get complete response
            response = chatbot_with_index(message, history[:-1])
            history[-1] = [message, response]
            yield history, ""
        
        def handle_topic_click(topic_word):
            return CHATBOT_TOPIC_RESPONSE_PROMPT.format(topic_word=topic_word)
        
        # Connect topic buttons
        for button_type, btn, data in all_buttons:
            btn.click(
                lambda t=data: handle_topic_click(t),
                outputs=[msg]
            ).then(
                respond, [msg, chatbot_ui], [chatbot_ui, msg]
            )
        
        msg.submit(respond, [msg, chatbot_ui], [chatbot_ui, msg])
    
    iface.launch(share=True)


if __name__ == "__main__":
    main()
