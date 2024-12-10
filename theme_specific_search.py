import openai
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from utility import *

def theme_search(conn,openai,user_query):
    try:
        query_info = extract_query_information(user_query,openai)
        print(f"\nExtracted query information: {json.dumps(query_info, indent=2)}")


        extracted_info=expand_query_information(query_info)
        print(f"\nExpanded query information: {json.dumps(extracted_info, indent=2)}")

        results = get_datasets_and_papers(conn, openai,extracted_info)
        print(f"\nRetrieved results:", results)
        
        recommendations = generate_theme_recommendations(user_query, openai, results)

        print("\nRecommendations:")
        print(recommendations)
        return recommendations
    except Exception as e:
        print(f"An error occurred: {e}")


    
def dynamic_cypher_query(query_info, openai, schema):
    if not schema:
        schema_str = "Schema information not available."
    else:
        schema_str = json.dumps(schema, indent=2)

    json_dict = json.dumps(query_info, indent=2)
    content = query_info.get("content", "")

    prompt = f"""
    Generate a Cypher query for Neo4j that finds related papers and associated details based on the following extracted information given in dictionary format in the variable json_dict:
    {json_dict}

    The user's original query content is:
    "{content}"


    The database schema is as follows:
    {schema_str}

    The query should:
    1. Start with a MATCH clause for Papers and related domain
    2. Use WHERE clauses to filter based on keywords and domain
    3. If domains not found in the json_dict, ensure that in the cypher query, it checks for the domain name IN $keywords
    4. Add additional OPTIONAL MATCH clauses for Conferences, Domains, Authors, and Keywords if specified in the json_dict
    5. Return the  Paper title, Paper abstract, authors, publication date, url, conclusion and related keywords

    Important guidelines:
    - Use OPTIONAL MATCH for relationships that might not exist for all papers
    - Use separate WHERE clauses for each MATCH to improve readability
    - Use coalesce() for optional filters to avoid errors when the field is not provided
    - For keyword matching, use: ANY(keyword IN json_dict["keywords"] WHERE p.title CONTAINS keyword OR p.abstract CONTAINS keyword)
    - Ensure the query is efficient and uses appropriate indexes if possible
    - Use the exact node labels, relationship types, and property names as provided in the database schema
    - If the schema information is not available, use general node labels like Dataset, Paper, Keyword, etc.

    Here's a template to start with:
    MATCH (p:Paper)-[:HAS_DOMAIN]->(dm:Domain)
    WHERE 1=1
    AND (
        toLower(dm.name) IN $domains 
        OR (($domains IS NULL OR $domains = []) AND toLower(dm.name) IN $keywords)
    )
    OPTIONAL MATCH (a:Author)-[:AUTHORED]->(p)
    OPTIONAL MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)
    OPTIONAL MATCH (p)-[:PRESENTED_AT]->(c:Conference)
    RETURN
        p.title AS Title,
        p.abstract AS Abstract,
        p.date_published AS Date_published,
        p.number_of_citations AS Citations,
        p.url AS URL,
        collect(DISTINCT a.name) AS Authors,
        collect(DISTINCT k.name) AS Keywords,
        collect(DISTINCT dm.name) AS Domains,
        collect(DISTINCT c.name) AS Conferences
    LIMIT 100


    Modify and expand this template based on the available information in json_dict.
    Do not include any explanations or additional context in the query.
    Do not include the 'CYPHER' keyword in the query and dont generate ```.
    """
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


def generate_theme_recommendations(user_query, openai, results):
    """
    Generate theme-specific research paper recommendations based on user query and retrieved results.

    Args:
        user_query (str): The original user query
        results (list): Retrieved research papers from the database

    Returns:
        str: AI-generated recommendations and insights about the research papers
    """
    prompt = f"""
    User Query: "{user_query}"

    Based on the query, here are the relevant papers found:

    {json.dumps(results, indent=2)}

    Please provide:
    1. A list of research papers relevant to the given topic
    2. Brief descriptions of what the paper is about
    3. Recommendations for potential research directions using these papers.

    Respond in a concise, well-structured format.
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # Using the same model as in generate_recommendations
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

