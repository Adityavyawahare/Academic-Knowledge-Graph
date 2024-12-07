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
    FOREACH (author_name IN CASE WHEN $authors IS NOT NULL THEN $authors ELSE [] END |
        MERGE (a:Author {name: author_name})
        MERGE (a)-[:AUTHORED]->(p)
    )
    WITH p
    FOREACH (dataset_name IN CASE WHEN $datasets IS NOT NULL THEN $datasets ELSE [] END |
        MERGE (d:Dataset {name: dataset_name})
        MERGE (p)-[:USES_DATASET]->(d)
    )
    WITH p
    FOREACH (domain_name IN CASE WHEN $domains IS NOT NULL THEN $domains ELSE [] END |
        MERGE (do:Domain {name: domain_name})
        MERGE (p)-[:HAS_DOMAIN]->(do)
    )
    WITH p
    FOREACH (keyword_name IN CASE WHEN $keywords IS NOT NULL THEN $keywords ELSE [] END |
        MERGE (k:Keyword {name: keyword_name})
        MERGE (p)-[:HAS_KEYWORD]->(k)
    )
    WITH p
    MERGE (c:Conference {name: $conference})
    MERGE (p)-[:PRESENTED_AT]->(c)
    WITH p
    FOREACH (_ IN CASE WHEN $github_repo IS NOT NULL THEN [1] ELSE [] END |
        MERGE (r:GitHubRepo {link: $github_repo})
        MERGE (p)-[:HAS_GITHUB_REPO]->(r)
    )
    WITH p
    FOREACH (citation IN CASE WHEN $citations IS NOT NULL THEN $citations ELSE [] END |
        MERGE (cited_paper:Paper {id: citation.id})
        ON CREATE SET cited_paper.title = citation.title,
                    cited_paper.url = citation.url
        MERGE (p)-[:CITES]->(cited_paper)
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
           github_repo=paper_data.get('github_repo', None),
           citations=paper_data.get('citations', []))
