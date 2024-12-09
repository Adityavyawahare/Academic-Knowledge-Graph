from neo4j import GraphDatabase
import json
from dotenv import load_dotenv
import os
from create_paper_node import create_paper

# Neo4j connection details
load_dotenv()
URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

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

def insert_data(papers):
    with driver.session() as session:
        # Create constraints
        create_constraints(session)

        # Insert papers
        for paper in papers:
            session.execute_write(create_paper, paper)

def insert_single_paper(paper):
    with driver.session() as session:
        session.execute_write(create_paper, paper)

# Read raw data
raw_data = open('raw_data.json',)
papers = json.load(raw_data)

# Insert the data
insert_data(papers)

# insert single paper
# insert_single_paper(papers[0])

print("Data inserted successfully!")

# Close the driver
driver.close()
