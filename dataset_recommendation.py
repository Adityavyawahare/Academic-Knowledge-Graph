import openai
import json
from dotenv import load_dotenv
import os
from utility import *
load_dotenv()

def get_dataset_recommendations(conn,openai,user_query):
    """
    Returns a string containing dataset recommendations based on a given query.
    """
    try:
        query_info = extract_query_information(user_query,openai)
        print(f"\nExtracted query information: {json.dumps(query_info, indent=2)}")

        results = get_datasets_and_papers(conn,openai, query_info)
        print(f"\nRetrieved results:", results)

        recommendations = generate_recommendations(user_query, openai,query_info, results)
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
    Generate a Cypher query for Neo4j that finds datasets and related papers based on the following extracted information given in dictionary format in the variable json_dict:
    {json_dict}

    The user's original query content is:
    "{content}"



    The database schema is as follows:
    {schema_str}

    The query should:
    1. Start with a MATCH clause for Papers and related Datasets
    2. Use WHERE clauses to filter based on available information (keywords, date range, min citations)
    3. Add additional OPTIONAL MATCH clauses for Conferences, Domains, Authors, and Keywords if specified in the json_dict
    4. Return the Dataset name, Paper title, Paper abstract, authors, publication date, number of citations, and related keywords

    Important guidelines:
    - Use OPTIONAL MATCH for relationships that might not exist for all papers
    - Use separate WHERE clauses for each MATCH to improve readability
    - Use coalesce() for optional filters to avoid errors when the field is not provided
    - For keyword matching, use: ANY(keyword IN json_dict["keywords"] WHERE p.title CONTAINS keyword OR p.abstract CONTAINS keyword)
    - Ensure the query is efficient and uses appropriate indexes if possible
    - Use the exact node labels, relationship types, and property names as provided in the database schema
    - If the schema information is not available, use general node labels like Dataset, Paper, Keyword, etc.

    Here's a template to start with:

    MATCH (p:Paper)-[:USES_DATASET]->(d:Dataset)
    WHERE 1=1
    AND ($keywords IS NULL OR $keywords = [] OR ANY(keyword IN $keywords WHERE p.title CONTAINS keyword OR p.abstract CONTAINS keyword))
    AND ($date_range_start IS NULL OR p.date_published >= $date_range_start)
    AND ($date_range_end IS NULL OR p.date_published <= $date_range_end)
    AND ($min_citations IS NULL OR p.number_of_citations >= $min_citations)

    OPTIONAL MATCH (p)-[:AUTHORED]->(a:Author)
    OPTIONAL MATCH (p)-[:PRESENTED_AT]->(c:Conference)
    OPTIONAL MATCH (p)-[:HAS_DOMAIN]->(dm:Domain)
    OPTIONAL MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)

    WHERE
    ($authors IS NULL OR $authors = [] OR a.name IN $authors)
    AND ($conferences IS NULL OR $conferences = [] OR c.name IN $conferences)
    AND ($domains IS NULL OR $domains = [] OR dm.name IN $domains)

    RETURN d.name AS Dataset, p.title AS Paper, p.abstract AS Abstract,
           collect(DISTINCT a.name) AS Authors, p.date_published AS Date_published,
           p.number_of_citations AS Citations, collect(DISTINCT k.name) AS Keywords
    ORDER BY p.date_published DESC
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


def generate_recommendations(user_query, openai, query_info, results):
    prompt = f"""
    User Query: "{user_query}"

    Based on the query and extracted information, here are the relevant datasets and papers found:

    {json.dumps(results, indent=2)}

    Please provide:
    1. A summary of the most relevant datasets and why they are suitable for the given topics or research areas.
    2. Brief descriptions of how these datasets have been used in the related papers.
    3. Recommendations for potential research directions or applications using these datasets.
    4. Any additional datasets or research areas that might be relevant but weren't found in our database.

    Respond in a concise, well-structured format, focusing on providing useful recommendations for dataset usage in research.
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


def get_datasets_and_papers(conn, openai, query_info):
    schema = get_database_structure(conn)
    query = dynamic_cypher_query(query_info,openai,schema)
    print(f"Generated Cypher query:\n{query}")

    # Prepare parameters with default values
    parameters = {
        "papers": query_info.get("papers", []),
        "keywords": query_info.get("keywords", []),
        "authors": query_info.get("authors", []),
        "conferences": query_info.get("conferences", []),
        "domains": query_info.get("domains", []),
        "date_range_start": None,
        "date_range_end": None,
        "min_citations": query_info.get("min_citations")
    }

    # Safely get date range values
    date_range = query_info.get("date_range", {})
    if isinstance(date_range, dict):
        parameters["date_range_start"] = date_range.get("start")
        parameters["date_range_end"] = date_range.get("end")

    # Convert None to empty lists for list parameters
    for key in ["keywords", "authors", "conferences", "domains"]:
        if parameters[key] is None:
            parameters[key] = []

    results = conn.query(query, parameters=parameters)
    print(f"Retrieved {len(results)} results")
    return results