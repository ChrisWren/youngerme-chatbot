"""
Indexing functionality for creating and managing vector databases.
This module contains all the code needed to index documents and set up the LlamaIndex environment.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings, StorageContext, load_index_from_storage
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding


class ServiceConfig(BaseModel):
    num_outputs: int = Field(default=512, ge=1, le=4096)
    max_chunk_overlap: int = Field(default=20, ge=0)
    chunk_size_limit: int = Field(default=600, ge=1)
    max_input_size: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    model_name: str = Field(default="gpt-3.5-turbo")

    @field_validator('max_input_size')
    @classmethod
    def validate_max_input_size(cls, v, info):
        values = info.data
        if 'chunk_size_limit' in values and v < values['chunk_size_limit']:
            raise ValueError('max_input_size must be greater than chunk_size_limit')
        return v


def setup_settings(config: Optional[ServiceConfig] = None) -> None:
    """Configure LlamaIndex global settings."""
    if config is None:
        config = ServiceConfig()
    
    # Set up LLM
    Settings.llm = OpenAI(
        temperature=config.temperature,
        model=config.model_name,
        max_tokens=config.num_outputs
    )
    
    # Set up embedding model
    Settings.embed_model = OpenAIEmbedding()
    
    # Set chunk size
    Settings.chunk_size = config.chunk_size_limit
    Settings.chunk_overlap = config.max_chunk_overlap


def analyze_documents_for_config(documents: List, llm) -> dict:
    """Analyze documents to generate config updates including name, description, and questions."""
    # Sample documents to analyze
    sample_docs = documents[:5] if len(documents) >= 5 else documents
    sample_content = "\n\n".join([doc.text[:800] for doc in sample_docs])
    
    prompt = f"""Analyze this personal writing/document content and extract information about the person:

Content:
{sample_content}

Based on this content, provide:
1. The person's name (if mentioned, otherwise use "Assistant")
2. A brief description of who they are (2-3 sentences)
3. A good title for a chatbot representing them
4. 5 specific questions someone might ask this person based on the content

Format your response as JSON:
{{
  "name": "Person's Name",
  "description": "Brief description of the person",
  "title": "Chatbot Title",
  "questions": [
    "Question 1",
    "Question 2", 
    "Question 3",
    "Question 4",
    "Question 5"
  ]
}}"""

    try:
        response = llm.complete(prompt)
        # Try to parse JSON response
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "name": "Assistant",
                "description": "AI chatbot based on provided documents and communication style",
                "title": "Personal AI Assistant",
                "questions": ["Tell me about yourself", "What are your interests?", "How do you think?"]
            }
    except Exception as e:
        print(f"Error analyzing documents: {e}")
        return {
            "name": "Assistant", 
            "description": "AI chatbot based on provided documents and communication style",
            "title": "Personal AI Assistant",
            "questions": ["Tell me about yourself", "What are your interests?", "How do you think?"]
        }


def construct_index(directory_path: str, config: Optional[ServiceConfig] = None) -> VectorStoreIndex:
    """Construct a vector index from documents in the specified directory."""
    try:
        documents = SimpleDirectoryReader(directory_path).load_data()
        setup_settings(config)
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist()
        return index
    except Exception as e:
        print(f"Error constructing index: {str(e)}")
        raise


def load_or_create_index(storage_directory: str = "./storage", docs_directory: str = "docs") -> VectorStoreIndex:
    """Load index from storage or create new one if not found."""
    storage_path = Path(storage_directory)
    
    if storage_path.exists():
        try:
            print(f"Loading existing index from {storage_directory}")
            storage_context = StorageContext.from_defaults(persist_dir=storage_directory)
            return load_index_from_storage(storage_context)
        except Exception as e:
            print(f"Failed to load index: {e}. Creating new index...")
    
    # Fallback to creating new index
    print(f"Creating new index from documents in {docs_directory}...")
    return construct_index(docs_directory)


def setup_initial_files(docs_directory: str, storage_directory: str = "./storage") -> None:
    """Set up initial config, docs, and storage from sample files if they don't exist."""
    docs_path = Path(docs_directory)
    storage_path = Path(storage_directory)
    config_path = Path("config.json")
    
    sample_config_path = Path("sample/config/config.json")
    sample_docs_path = Path("sample/docs")
    sample_storage_path = Path("sample/storage")
    
    # Copy sample config if config.json doesn't exist
    if not config_path.exists() and sample_config_path.exists():
        print(f"Copying sample config to config.json...")
        shutil.copy2(sample_config_path, config_path)
        print("Created config.json from sample")
    
    # Copy sample docs if docs directory doesn't exist
    if not docs_path.exists() and sample_docs_path.exists():
        print(f"Copying sample docs to {docs_directory}...")
        shutil.copytree(sample_docs_path, docs_path)
        print(f"Created {docs_directory} directory from sample")
    
    # Copy sample storage if storage directory doesn't exist
    if not storage_path.exists() and sample_storage_path.exists():
        print(f"Copying sample storage to {storage_directory}...")
        shutil.copytree(sample_storage_path, storage_path)
        print(f"Created {storage_directory} directory from sample")


def index_documents(
    docs_directory: str,
    storage_directory: str = "./storage",
    service_config: Optional[ServiceConfig] = None,
    force_reindex: bool = False,
    generate_questions: bool = True
) -> VectorStoreIndex:
    """
    Index documents from a directory and persist to storage.
    
    Args:
        docs_directory: Directory containing documents to index
        storage_directory: Directory to store the vector index
        service_config: Configuration for the service context
        force_reindex: Force re-indexing even if storage exists
        generate_questions: Whether to generate sample questions and update config
    
    Returns:
        VectorStoreIndex: The created or loaded index
    """
    # Set up initial files from samples if needed
    setup_initial_files(docs_directory, storage_directory)
    
    docs_path = Path(docs_directory)
    storage_path = Path(storage_directory)
    
    # Check if documents directory exists
    if not docs_path.exists():
        raise FileNotFoundError(f"Documents directory not found: {docs_directory}")
    
    # Check if we should load existing index
    if storage_path.exists() and not force_reindex:
        print(f"Loading existing index from {storage_directory}")
        try:
            storage_context = StorageContext.from_defaults(persist_dir=storage_directory)
            index = load_index_from_storage(storage_context)
            return index
        except Exception as e:
            print(f"Failed to load existing index: {e}")
            print("Creating new index...")
    
    # Create storage directory if it doesn't exist
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Load documents
    print(f"Loading documents from {docs_directory}")
    documents = SimpleDirectoryReader(docs_directory).load_data()
    print(f"Loaded {len(documents)} documents")
    
    # Set up global settings
    setup_settings(service_config)
    
    # Create index
    print("Creating vector index...")
    index = VectorStoreIndex.from_documents(documents)
    
    # Generate config updates if requested
    if generate_questions:
        print("Analyzing documents to update configuration...")
        analysis = analyze_documents_for_config(documents, Settings.llm)
        
        # Update config.json with analyzed information
        config_path = Path("config.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Update person info
                config["person"]["name"] = analysis["name"]
                config["person"]["description"] = analysis["description"]
                
                # Update chatbot info
                config["chatbot"]["title"] = analysis["title"]
                config["chatbot"]["examples"] = analysis["questions"]
                
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"Updated config.json:")
                print(f"  Name: {analysis['name']}")
                print(f"  Title: {analysis['title']}")
                print(f"  Description: {analysis['description']}")
                print(f"  Generated {len(analysis['questions'])} questions:")
                for i, q in enumerate(analysis['questions'], 1):
                    print(f"    {i}. {q}")
            except Exception as e:
                print(f"Error updating config.json: {e}")
        else:
            # Create new config.json file
            print("Creating new config.json file...")
            default_config = {
                "person": {
                    "name": analysis["name"],
                    "description": analysis["description"],
                    "docs_directory": docs_directory
                },
                "chatbot": {
                    "title": analysis["title"],
                    "description": analysis["description"],
                    "examples": analysis["questions"]
                },
                "retrieval": {
                    "similarity_threshold": 0.7,
                    "max_chunks": 5,
                    "context_history_length": 3
                }
            }
            
            try:
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                
                print(f"Created config.json:")
                print(f"  Name: {analysis['name']}")
                print(f"  Title: {analysis['title']}")
                print(f"  Description: {analysis['description']}")
                print(f"  Generated {len(analysis['questions'])} questions:")
                for i, q in enumerate(analysis['questions'], 1):
                    print(f"    {i}. {q}")
            except Exception as e:
                print(f"Error creating config.json: {e}")

    # Persist index
    print(f"Persisting index to {storage_directory}")
    index.storage_context.persist(persist_dir=storage_directory)
    
    print("Indexing completed successfully!")
    return index