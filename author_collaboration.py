import json 
from theme_specific_search import extract_query_information, get_database_structure

def get_author_collaboration(conn, openai,user_query):
    try:
        # user_query = input("Enter your query for dataset recommendations: ")

        query_info = extract_query_information(user_query, openai)
        print(f"\nExtracted query information: {json.dumps(query_info, indent=2)}")

        results = get_datasets_and_papers(conn, openai, query_info)
        print(f"\nRetrieved results:", results)

        recommendations = generate_author_recommendations(user_query, openai, results)

        print("\nRecommendations:")
        print(recommendations)

    except Exception as e:
        print(f"An error occurred: {e}")


def dynamic_cypher_query_author_colab(query_info, openai, schema):
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
    1. Start with a MATCH clause for Authors and papers authored by them.
    2. Use WHERE clauses to filter based on available information (keywords, date range, domain)
    3. Add additional OPTIONAL MATCH clauses for Conferences, Domains, Authors, and Keywords if specified in the json_dict
    4. Return the  Author name,Paper title, Paper abstract, conference

    Important guidelines:
    - Use OPTIONAL MATCH for relationships that might not exist for all papers
    - Use separate WHERE clauses for each MATCH to improve readability
    - Use coalesce() for optional filters to avoid errors when the field is not provided
    - For keyword matching, use: ANY(keyword IN json_dict["keywords"] WHERE p.title CONTAINS keyword OR p.abstract CONTAINS keyword)
    - Ensure the query is efficient and uses appropriate indexes if possible
    - Use the exact node labels, relationship types, and property names as provided in the database schema
    - If the schema information is not available, use general node labels like Dataset, Paper, Keyword, etc.

    Here's a template to start with:
    MATCH (a:Author)-[:AUTHORED]->(p:Paper)
    WHERE 1=1
    AND ($keywords IS NULL OR $keywords = [] OR ANY(keyword IN $keywords WHERE p.title CONTAINS keyword OR p.abstract CONTAINS keyword))
    AND ($authors IS NULL OR $authors = [] OR a.name IN $authors)

    OPTIONAL MATCH (p)-[:PRESENTED_AT]->(c:Conference)
    OPTIONAL MATCH (p)-[:HAS_DOMAIN]->(dm:Domain)
    OPTIONAL MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)

    WHERE
    ($domains IS NULL OR $domains = [] OR ANY(domain IN $domains WHERE dm.name CONTAINS domain))
    AND ($conferences IS NULL OR $conferences = [] OR ANY(conference IN $conferences WHERE c.name CONTAINS conference))

    RETURN a.name AS Author, p.title AS PaperTitle, p.abstract AS Abstract, collect(DISTINCT c.name) AS Conferences
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

def get_datasets_and_papers(conn, openai, query_info):
    schema = get_database_structure(conn)
    query = dynamic_cypher_query_author_colab(query_info, openai, schema)
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


def generate_author_recommendations(user_query, openai, results):
    """
    Generate author collaboration recommendations based on user query and retrieved results.

    Args:
        user_query (str): The original user query
        results (list): Retrieved research papers and authors from the database

    Returns:
        str: AI-generated recommendations and insights about potential collaborators
    """
    prompt = f"""
    User Query: "{user_query}"

    Based on the query, here are the relevant authors and their associated work found:

    {json.dumps(results, indent=2)}

    Please provide:
    1. A list of authors who are experts or active in the given research area or topic.
    2. Brief descriptions of their work and contributions in this field.Also mention the conferences where they have published papers.
    3. Recommendations for potential collaborations with these authors and why they are suitable.
    4. Any additional authors or research networks that might be relevant but weren't found in our database.

    Respond in a concise, well-structured format.
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # Using the same model as in other recommendation methods
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


