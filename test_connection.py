from neo4j import GraphDatabase

# URI examples: "neo4j://localhost", "neo4j+s://xxx.databases.neo4j.io"
URI = "neo4j+s://b2850215.databases.neo4j.io"
AUTH = ("neo4j", "fBtFxQFlU5jOLmlXSSAr76DkJxz9_vQtxjT10IyHZTE")

with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()

    records, summary, keys = driver.execute_query(
        "MATCH (p:Person {name: 'Tom Hanks'}) RETURN p",
        database_="neo4j",
    )

    # Loop through results and do something with them
    for person in records:
        print(person)

    # Summary information
    print("The query `{query}` returned {records_count} records in {time} ms.".format(
        query=summary.query, records_count=len(records),
        time=summary.result_available_after,
    ))