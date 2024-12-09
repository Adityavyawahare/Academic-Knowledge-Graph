import openai
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def theme_search(conn,openai,user_query):
    try:
        query_info = extract_query_information(user_query,openai)
        print(f"\nExtracted query information: {json.dumps(query_info, indent=2)}")

        results = get_datasets_and_papers(conn, openai,query_info)
        print(f"\nRetrieved results:", results)

        recommendations = generate_theme_recommendations(user_query, openai, results)

        print("\nRecommendations:")
        print(recommendations)
        return recommendations
    except Exception as e:
        print(f"An error occurred: {e}")
    
def extract_query_information(query, openai):
    prompt = f"""
    Extract the following information from the given query:
    "{query}"

    Return a JSON object with the following keys:
    - "content": the original query text
    - "keywords": list of relevant keywords or topics
    - "papers": list of any specific papers mentioned
    - "datasets": list of any specific datasets mentioned
    - "domains": list of any specific domains or research areas mentioned
    - "authors": list of any specific authors mentioned
    - "conferences": list of any specific conferences mentioned
    - "date_range": object with "start" and "end" dates if a date range is specified
    - "min_citations": minimum number of citations if specified

    If a category is not mentioned, return an empty list or null for that key.
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        if not content:
            raise ValueError("Empty response from OpenAI API")

        extracted_info = json.loads(content)

        # Ensure all required keys are present
        required_keys = ["content", "keywords", "papers", "datasets", "domains", "authors", "conferences", "date_range", "min_citations"]
        for key in required_keys:
            if key not in extracted_info:
                extracted_info[key] = [] if key not in ["content", "date_range", "min_citations"] else None

        return extracted_info

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        print(f"Received content: {content}")
        # Return a default structure if JSON parsing fails
        return {
            "content": query,
            "keywords": [],
            "papers": [],
            "datasets": [],
            "domains": [],
            "authors": [],
            "conferences": [],
            "date_range": None,
            "min_citations": None
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        # Return a default structure if any other error occurs
        return {
            "content": query,
            "keywords": [],
            "papers": [],
            "datasets": [],
            "domains": [],
            "authors": [],
            "conferences": [],
            "date_range": None,
            "min_citations": None
        }

def dynamic_cypher_query_domain_specific(query_info, openai, schema):
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
    1. Start with a MATCH clause for Papers and related details such as title, abstract, authors, publication date, conclusion, paper url and related keywords
    2. Use WHERE clauses to filter based on available information (keywords, date range, domain)
    3. Add additional OPTIONAL MATCH clauses for Conferences, Domains, Authors, and Keywords if specified in the json_dict
    4. Return the  Paper title, Paper abstract, authors, publication date, url, conclusion and related keywords

    Important guidelines:
    - Use OPTIONAL MATCH for relationships that might not exist for all papers
    - Use separate WHERE clauses for each MATCH to improve readability
    - Use coalesce() for optional filters to avoid errors when the field is not provided
    - For keyword matching, use: ANY(keyword IN json_dict["keywords"] WHERE p.title CONTAINS keyword OR p.abstract CONTAINS keyword)
    - Ensure the query is efficient and uses appropriate indexes if possible
    - Use the exact node labels, relationship types, and property names as provided in the database schema
    - If the schema information is not available, use general node labels like Dataset, Paper, Keyword, etc.

    Here's a template to start with:

    MATCH (p:Paper)-[:HAS_DOMAIN]->(d:Domain)
    WHERE 1=1
    AND domain IN $domains
    OPTIONAL MATCH (p)-[:AUTHORED]->(a:Author)
    OPTIONAL MATCH (p)-[:PRESENTED_AT]->(c:Conference)
    OPTIONAL MATCH (p)-[:HAS_KEYWORD]->(k:Keyword)
    RETURN
      p.title AS PaperTitle,
      p.abstract AS Abstract,
      p.date_published AS PublicationDate,
      collect(DISTINCT d.name) AS Domains,
      collect(DISTINCT ds.name) AS Datasets,
      collect(DISTINCT a.name) AS Authors,
      collect(DISTINCT c.name) AS Conferences,
      collect(DISTINCT k.name) AS Keywords,
      p.url AS URLs,
      p.number_of_citations AS Citations
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
    query = dynamic_cypher_query_domain_specific(query_info,openai,schema)
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

def get_database_structure(conn):
    schema_query = """
    CALL apoc.meta.schema()
    """
    try:
        schema = conn.query(schema_query)
        return schema[0] if schema else None
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return None