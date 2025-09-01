#!/usr/bin/env python3
"""
Document indexing script for creating a persistent vector database.
Run this script to index documents before starting the chatbot.
"""

import os
import sys

from indexing import index_documents

def main():
    """Main entry point for the indexing script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Index documents for the chatbot")
    parser.add_argument(
        "--docs", 
        default="docs", 
        help="Directory containing documents to index (default: docs)"
    )
    parser.add_argument(
        "--storage", 
        default="./storage", 
        help="Directory to store the vector index (default: ./storage)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force re-indexing even if storage exists"
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (can also use OPENAI_API_KEY environment variable)"
    )
    parser.add_argument(
        "--no-questions",
        action="store_true",
        help="Skip generating sample questions"
    )
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
    elif not os.environ.get("OPENAI_API_KEY"):
        print("Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Check if docs directory exists
    docs_path = os.path.join(os.getcwd(), args.docs)
    if not os.path.exists(docs_path):
        print(f"Documents directory '{args.docs}' not found.")
        print("Using sample data instead...")

        # Import the setup function from indexing module
        from indexing import setup_initial_files

        # Set up sample files
        setup_initial_files(args.docs, args.storage)

        # Check if sample storage was copied
        storage_path = os.path.join(os.getcwd(), args.storage)
        if os.path.exists(storage_path):
            print("\nSample data and pre-indexed storage loaded successfully!")
            print(f"Storage location: {os.path.abspath(args.storage)}")
            print("Ready to start chatbot with sample data.")
        else:
            print("Warning: Sample storage not found. You may need to run indexing.")
        return

    try:
        index = index_documents(
            docs_directory=args.docs,
            storage_directory=args.storage,
            force_reindex=args.force,
            generate_questions=not args.no_questions
        )
        print(f"\nIndex created successfully!")
        print(f"Documents indexed: {len(index.docstore.docs)} documents")
        print(f"Storage location: {os.path.abspath(args.storage)}")

    except Exception as e:
        print(f"Error during indexing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()