import os
import json
from neo4j_connection import Neo4jConnection
from openai_connection import initialize_openai
from dataset_recommendation import get_dataset_recommendations
from theme_specific_search import generate_theme_recommendations
from author_collaboration import get_author_collaboration

def initialize_services():
    # Initialize Neo4j connection
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        raise ValueError("Neo4j environment variables are not set properly.")

    neo4j_conn = Neo4jConnection(neo4j_uri, neo4j_user, neo4j_password)
    neo4j_conn.connect()

    # Initialize OpenAI
    openai_client = initialize_openai()

    return neo4j_conn, openai_client

# Define the tools
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_dataset_recommendations",
            "description": "Get dataset recommendations for information extraction tasks",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User's query about dataset recommendations"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_theme_recommendations",
            "description": "Get influential papers for a specific domain",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User's query about influential papers in a domain"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_author_collaboration",
            "description": "Find potential authors for collaboration",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User's query about finding authors for collaboration"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def chatbot(neo4j_conn, openai_client):
    messages = [
        {"role": "system", "content": "You are a helpful assistant for researchers in the field of Natural Language Processing and Information Extraction. You can provide dataset recommendations, suggest influential papers, and help find potential collaborators."}
    ]

    while True:
        user_input = input("User: ")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Assistant: Goodbye! Have a great day.")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message)

            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    try:
                        if function_name == "get_dataset_recommendations":
                            result = get_dataset_recommendations(neo4j_conn, openai_client, function_args['query'])
                        elif function_name == "generate_theme_recommendations":
                            result = generate_theme_recommendations(function_args['query'], openai_client, neo4j_conn)
                        elif function_name == "get_author_collaboration":
                            result = get_author_collaboration(neo4j_conn, openai_client, function_args['query'])
                        else:
                            result = "Function not found."
                    except Exception as e:
                        result = f"An error occurred while executing {function_name}: {str(e)}"

                    messages.append(
                        {"role": "tool", "tool_call_id": tool_call.id, "name": function_name, "content": result}
                    )

                # Get a new response from the model
                response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=messages
                )
                assistant_message = response.choices[0].message
                messages.append(assistant_message)

            print("Assistant:", assistant_message.content)

        except Exception as e:
            print(f"An error occurred: {str(e)}")

def main():
    neo4j_conn, openai_client = initialize_services()

    try:
        chatbot(neo4j_conn, openai_client)
    finally:
        # Ensure Neo4j connection is closed
        neo4j_conn.close()

if __name__ == "__main__":
    main()