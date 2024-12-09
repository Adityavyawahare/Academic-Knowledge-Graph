import json
from pdfTojson import extract_paper_content_from_url

def summarize_papers(conn, openai, query):
    query_content = extract_paper_info(conn, openai, query)
    paper_nodes = get_paper_info(conn, openai, query_content)
    summaries = '''Here is the requested summary:'''
    for p in paper_nodes:
        paper_data = p.data()
        doc = extract_paper_content_from_url(paper_data['p']['url'], paper_data['p']['title'])
        json_doc= json.dumps(doc, indent=4)
        summary = generate_summary(query_content, openai, json_doc, paper_data['p']['title'])
        summaries += f"\nPaper: {paper_data['p']['title']}\n{summary}\n"

    return summaries

def get_citation_reasoning(conn, openai, query):
    query_content = extract_paper_info(conn, openai, query)
    no_of_titles_extracted = len(query_content['paper_titles'].split(","))
    paper_nodes = get_paper_info(conn, openai, query_content)

    if len(paper_nodes) != no_of_titles_extracted:
        print("Insufficient information on given papers")
        return
    
    context = '''Here is the information about the papers:'''
    for p in paper_nodes:
        paper_data = p.data()
        doc = extract_paper_content_from_url(paper_data['p']['url'], paper_data['p']['title'])
        json_doc = json.dumps(doc, indent=4)
        context += f"\n{json_doc}\n"
    
    prompt = f"""
    Given structured data containing information of the research papers.
    Answer this query: {query}
    Data:
    {context}

    Important guidelines:
    1. If no reason is found for citation then please specify no reason found.
    2. Give separate reasoning for each pair of citing and cited paper.
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def extract_paper_info(conn, openai, query):
    prompt = f"""
        Extract titles of mentioned research papers from the given query:
        "{query}"
        Give the result in comma separated format.
        If a research paper is not mentioned then return null.
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()

        query_content = {
            "content": query,
            "paper_titles": content
        }
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return query_content

def generate_cypher_query(conn, openai, query_info, schema):
    if not schema:
        schema_str = "Schema information not available."
    else:
        schema_str = json.dumps(schema, indent=2)
    content = query_info.get("content", "")
    paper_titles = query_info.get("paper_titles")
    prompt = f"""
    Generate a Cypher query for Neo4j that finds papers using title information.
    titles: {paper_titles}

    The user's original query content is:
    "{content}"



    The database schema is as follows:
    {schema_str}

    The query should:
    1. Start with a MATCH clause for Papers.
    2. Use WHERE clauses to filter based on titles
    4. Return the paper node

    Important guidelines:
    - Put quotes around titles when listing them in the WHERE clause.
    - Ensure the query is efficient and uses appropriate indexes if possible
    - Use the exact node labels, relationship types, and property names as provided in the database schema
    - If the schema information is not available, use general node labels like Dataset, Paper, Keyword, etc.

    Here's a template to start with:

    MATCH (p:Paper)
    WHERE p.title IN [
        $paper_title1,
        $paper_title2,
        ...,
        $paper_titlen
    ]
    RETURN p
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




def get_paper_info(conn, openai, query_content):
    # return paper url
    schema = get_database_structure(conn)
    cypher_query = generate_cypher_query(conn, openai, query_content, schema)
    results = conn.query(cypher_query)
    return results


def generate_summary(query, openai, json_doc, paper_tile):
    prompt = f"""
    Summarize the given json data containing information about the research paper : {paper_tile}
    Json data:
    {json_doc}

    Please provide the summary divided into 3 parts:
    1. Summarize the motivation of the paper.
    2. Summarize the main idea of the paper.
    3. Summarize the conclusion and results.

    Each section should atleast be 250 words if possible.
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
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
