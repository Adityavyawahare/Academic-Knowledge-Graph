from neo4j import GraphDatabase
from llmsherpa.readers import LayoutPDFReader
import json

credentials = open('credentials.json',)
creds = json.load(credentials)
URI = creds["NEO4J_URI"]
USERNAME = creds["NEO4J_USERNAME"]
PASSWORD = creds["NEO4J_PASSWORD"]
llmsherpa_api_url = "https://readers.llmsherpa.com/api/document/developer/parseDocument?renderFormat=all"
pdf_reader = LayoutPDFReader(llmsherpa_api_url)

# Connect to Neo4j
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

records, summary, keys = driver.execute_query(
    "MATCH (p:Paper {title: 'Large Language Models Can Self-Improve'}) RETURN p",
    database_="neo4j",
)

# Loop through results and do something with them
pdf_url = records[0].data()['p']['url']  # obtain record as dict
doc = pdf_reader.read_pdf(pdf_url)
# print(doc)

