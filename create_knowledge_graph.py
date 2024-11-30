from neo4j import GraphDatabase
import json

# Neo4j connection details
URI = "neo4j+s://b2850215.databases.neo4j.io"
USERNAME = "neo4j"
PASSWORD = "insert password here"

# Connect to Neo4j
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def create_constraints(session):
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.id IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Conference) REQUIRE c.name IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (do:Domain) REQUIRE do.name IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (k:Keyword) REQUIRE k.name IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (r:GitHubRepo) REQUIRE r.link IS UNIQUE")

def create_paper(tx, paper_data):
    query = """
    MERGE (p:Paper {id: $paper_id})
    SET p.title = $title,
        p.date_published = $date_published,
        p.abstract = $abstract,
        p.conclusion = $conclusion,
        p.number_of_citations = $number_of_citations,
        p.url = $url
    WITH p
    UNWIND $authors AS author_name
        MERGE (a:Author {name: author_name})
        MERGE (a)-[:AUTHORED]->(p)
    WITH p
    UNWIND $datasets AS dataset_name
        MERGE (d:Dataset {name: dataset_name})
        MERGE (p)-[:USES_DATASET]->(d)
    WITH p
    UNWIND $domains AS domain_name
        MERGE (do:Domain {name: domain_name})
        MERGE (p)-[:HAS_DOMAIN]->(do)
    WITH p
    UNWIND $keywords AS keyword_name
        MERGE (k:Keyword {name: keyword_name})
        MERGE (p)-[:HAS_KEYWORD]->(k)
    WITH p
    MERGE (c:Conference {name: $conference})
    MERGE (p)-[:PRESENTED_AT]->(c)
    WITH p
    FOREACH (_ IN CASE WHEN $github_repo IS NOT NULL THEN [1] ELSE [] END |
        MERGE (r:GitHubRepo {link: $github_repo})
        MERGE (p)-[:HAS_GITHUB_REPO]->(r)
    )
    RETURN p
    """
    tx.run(query,
           paper_id=paper_data['id'],
           title=paper_data['title'],
           date_published=paper_data['date_published'],
           abstract=paper_data['abstract'],
           conclusion=paper_data.get('conclusion', ''),
           number_of_citations=paper_data['number_of_citations'],
           url=paper_data['url'],
           authors=paper_data['authors'],
           datasets=paper_data['datasets'],
           domains=paper_data['domains'],
           keywords=paper_data['keywords'],
           conference=paper_data['conference'],
           github_repo=paper_data.get('github_repo', None))

def insert_data(papers):
    with driver.session() as session:
        # Create constraints
        create_constraints(session)

        # Insert papers
        for paper in papers:
            session.execute_write(create_paper, paper)

# Read raw data
raw_data = open('raw_data.json',)
papers = json.load(raw_data)

# Insert the data
insert_data(papers)

print("Data inserted successfully!")

# Close the driver
driver.close()
