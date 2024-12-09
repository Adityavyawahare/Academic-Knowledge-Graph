from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def connect(self):
        if not self._driver:
            try:
                self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            except ServiceUnavailable:
                print("Unable to connect to Neo4j database.")
                raise

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    def query(self, query, parameters=None):
        assert self._driver is not None, "Driver not initialized. Call connect() first."
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

# Usage
uri = "neo4j+s://b2850215.databases.neo4j.io"
user = "neo4j"
password = "fBtFxQFlU5jOLmlXSSAr76DkJxz9_vQtxjT10IyHZTE"

# Using with context manager
# with Neo4jConnection(uri, user, password) as conn:
#     result = conn.query("MATCH (n) RETURN n LIMIT 5")
#     print(result)

# Or without context manager
# conn = Neo4jConnection(uri, user, password)
# conn.connect()
# result = conn.query("MATCH (n) RETURN n LIMIT 5")
# print(result)
# conn.close()