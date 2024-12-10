import openai
import json
import psycopg2
from psycopg2.extras import RealDictCursor

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

    If a category is not mentioned, return an empty list or null for that key.Store all values in the list as lower case.
    Don't return json keyword or ```.
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
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
    
def expand_query_information(extracted_info, openai_client):
    """
    Expand query information by generating synonyms, related terms, 
    and acronyms for each category.
    
    :param extracted_info: Dictionary with extracted query information
    :param openai_client: OpenAI client object
    :return: Expanded query information dictionary
    """
    print("Starting query expansion")
    expanded_info = extracted_info.copy()
    
    # Prepare prompt for query expansion
    expansion_prompt = f"""
    Perform query expansion for the following extracted information:
    {json.dumps(extracted_info, indent=2)}
    
    For each category (keywords, domains, etc.) for which the list is not empty, generate:
    1. Synonyms
    2. Related terms
    3. Acronyms or alternative phrasings
    4. Broader and narrower terms
    
    Return a JSON object without any formatting or explanation or json keywords. Return a JSON object with the same structure, 
    but with expanded lists. Ensure:
    - All expanded terms are in lowercase
    - Remove duplicates
    - Keep the original terms
    - Provide up to 5 additional terms for each category
    """
    
    try:
        # Call OpenAI API for expansion
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": expansion_prompt}]
        )
        
        # Parse the response
        expanded_content = response.choices[0].message.content.strip()
        # print(f"Raw API response: {expanded_content}")
        
        if not expanded_content:
            print("Error: Received empty response from OpenAI API")
            return extracted_info
        
        try:
            expanded_terms = json.loads(expanded_content)
            # print(f"Parsed expanded terms: {expanded_terms}")
        except json.JSONDecodeError as json_error:
            print(f"Error decoding JSON: {json_error}")
            print(f"Problematic content: {expanded_content}")
            return extracted_info
        
        # Merge and deduplicate expanded terms
        for key in ['keywords', 'domains', 'papers', 'datasets', 'authors', 'conferences']:
            if key in expanded_terms:
                # Combine original and expanded terms, convert to lowercase, remove duplicates
                expanded_info[key] = list(set(
                    [term.lower() for term in 
                     (extracted_info.get(key, []) + expanded_terms.get(key, []))
                    ]
                ))
        
        print("Query expansion completed successfully")
        return expanded_info
    
    except Exception as e:
        print(f"Error in query expansion: {e}")
        return extracted_info

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
