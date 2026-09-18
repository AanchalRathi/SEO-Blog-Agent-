def get_docs_path(company_name: str) -> str:
    safe_name = company_name.lower().replace(" ", "_")[:40]
    return f"brand_docs/{safe_name}/"