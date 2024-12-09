import os
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_models import ChatOpenAI
from langchain_community.utilities import GoogleSerperAPIWrapper


import json
from neo4j_connection import Neo4jConnection
from openai_connection import initialize_openai
from dataset_recommendation import get_dataset_recommendations
from theme_specific_search import theme_search
from author_collaboration import get_author_collaboration
from summarize_papers import summarize_papers, get_citation_reasoning
from dotenv import load_dotenv

load_dotenv(override=True)

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

def setup_tools(neo4j_conn, openai_client):
    # Check if SERPER_API_KEY is set
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        raise ValueError("SERPER_API_KEY environment variable is not set")
    
    search = GoogleSerperAPIWrapper(serper_api_key=serper_api_key)

    dataset_tool = StructuredTool.from_function(
        name="get_dataset_recommendations",
        func=lambda query: get_dataset_recommendations(neo4j_conn, openai_client, query),
        description="Get dataset recommendations for information extraction tasks"
    )
    theme_tool = StructuredTool.from_function(
        name="generate_theme_recommendations",
        func=lambda query: theme_search(neo4j_conn, openai_client, query),
        description="Get influential papers for a specific domain"
    )
    author_tool = StructuredTool.from_function(
        name="get_author_collaboration",
        func=lambda query: get_author_collaboration(neo4j_conn, openai_client, query),
        description="Find potential authors for collaboration"
    )
    summarization_tool = StructuredTool.from_function(
        name="summarize_papers",
        func=lambda query: summarize_papers(neo4j_conn, openai_client, query),
        description="Fetch summaries of mentioned papers"
    )
    citation_reasoning_tool = StructuredTool.from_function(
        name="citation_reasoning",
        func=lambda query: get_citation_reasoning(neo4j_conn, openai_client, query),
        description="Give reasoning for citation between given papers."
    )
    web_search_tool = StructuredTool.from_function(
        name="web_search",
        func=search.run,
        description="Search the web for current information. Use this as a last resort."
    )

    return [dataset_tool, theme_tool, author_tool, summarization_tool, citation_reasoning_tool, web_search_tool]


def setup_agent(tools):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    main_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant for researchers in the field of Natural Language Processing and Information Extraction. "
                   "You can provide dataset recommendations, suggest influential papers, help find potential collaborators and summarize research papers."
                   "When answering queries or completing tasks:\n"
                   "1. Use the appropriate tool based on the user's request.\n"
                   "2. For dataset recommendations, use the get_dataset_recommendations tool.\n"
                   "3. For finding influential papers in a domain, use the generate_theme_recommendations tool.\n"
                   "4. To find potential collaborators, use the get_author_collaboration tool.\n"
                   "5. For research paper summarization requests, use the summarize_papers tool\n"
                   "6. For citation reasoning, use the citation_reasoning tool\n"
                   "7. Use web search as a last resort to fill any remaining gaps in information.\n"
                   "8. Clearly indicate which sources you've used in your response.\n"
                   "Remember to provide comprehensive and accurate responses by combining information when necessary."),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(llm, tools, main_prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)



def chatbot(agent_executor):
    while True:
        user_input = input("User: ")
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Assistant: Goodbye! Have a great day.")
            break

        try:
            response = agent_executor.invoke({"input": user_input})
            print("Assistant:", response['output'])
        except Exception as e:
            print(f"An error occurred: {str(e)}")

def main():
    neo4j_conn, openai_client = initialize_services()
    tools = setup_tools(neo4j_conn, openai_client)
    agent_executor = setup_agent(tools)

    try:
        chatbot(agent_executor)
    finally:
        # Close Neo4j connection
        neo4j_conn.close()

if __name__ == "__main__":
    main()