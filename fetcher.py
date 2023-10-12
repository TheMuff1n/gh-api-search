from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from os import environ, path, makedirs
import json
import datetime

bearer_token = environ.get("API_KEY")
headers = {
    "Authorization": f"bearer {bearer_token}"
}

transport = RequestsHTTPTransport(
    url="https://api.github.com/graphql", headers=headers, use_json=True)
client = Client(transport=transport, fetch_schema_from_transport=True)

gql_query = gql("""
query Search($query:String!, $first:Int! $cursor:String) {
    search(
        query: $query
        type: REPOSITORY
        first: $first
        after: $cursor
    ) {
        repositoryCount
        edges {
            node {
                ... on Repository {
                    nameWithOwner
                    url
                    homepageUrl
                    primaryLanguage {
                        name
                    }
                    forks {
                        totalCount
                    }
                    stargazers {
                        totalCount
                    }
                    description
                    readme_master: object(expression: "master:README.md") {
                        ... on Blob {
                            text
                        }
                    }
                    readme_main: object(expression: "main:README.md") {
                        ... on Blob {
                            text
                        }
                    }
                    defaultBranchRef {
                        target {
                            ... on Commit {
                                tree {
                                    entries {
                                        name
                                        type
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        pageInfo {
            endCursor
            hasNextPage
        }
    }
    rateLimit {
        limit
        cost
        remaining
        resetAt
    }
}
""")


def fetch_page(query, pageSize=100, cursor=None):
    params = {
        "query": query,
        "first": pageSize,
        "cursor": cursor
    }
    return client.execute(gql_query, variable_values=params)


def fetch_all_pages(query, pageSize=100):
    # print(f"query '{query}' fetching first page")
    i = 1
    page = fetch_page(query=query, pageSize=pageSize)
    search = page["search"]
    repositories = search["edges"]
    while search["pageInfo"]["hasNextPage"]:
        # print(f"query '{query}' fetching page {i}")
        page = fetch_page(query=query, pageSize=pageSize,
                          cursor=search["pageInfo"]["endCursor"])
        search = page["search"]
        repositories.extend(search["edges"])
        i += 1
    return repositories


def format_content_element(element):
    return {
        "name": element["name"],
        "type": "file" if element["type"] == "blob" else "folder"
    }


def format_repo(node):
    repo = node["node"]
    readme_master = repo["readme_master"]
    readme_main = repo["readme_main"]
    readme = readme_main if readme_main is not None else readme_master if readme_master is not None else None
    readme = readme["text"] if readme is not None else ""
    new_repo = {
        "full_name": repo["nameWithOwner"],
        "url": repo["url"],
        "homepage": repo["homepageUrl"] if repo["homepageUrl"] is not None else "",
        "programming_language": repo["primaryLanguage"]["name"] if repo["primaryLanguage"] is not None else "",
        "forks": repo["forks"]["totalCount"],
        "stars": repo["stargazers"]["totalCount"],
        "description": repo["description"] if repo["description"] is not None else "",
        "contents": list(map(format_content_element, repo["defaultBranchRef"]["target"]["tree"]["entries"])),
        "readme": readme
    }
    return new_repo


fields = {
    "mathematics": ["Applied Math", "Combinatorics", "Number Theory", "Financial Math",
                    "Geometry", "Probability", "Representation Theory", "Symplectic Geometry", "Topology"],
    "chemistry": ["analytical spectroscopy", "electrochemistry ", "mass spectrometry", "separation science", "chemical biology",
                  "enzymology", "bioinorganic chemistry ", "inorganic materials ", "physical inorganic chemistry", "synthetic inorganic chemistry"],
    "biology": ["Biochemistry", "Biophysics", "Structural Biology", "Cell Biology",
                "Cancer", "Genetics", "Genomics", "Microbiology", "Virology", "Neuroscience"],
    "computer_sciences": ["Systems", "Networking", "Security", "Privacy", "Artificial Intelligence", "Theoretical Computer Science", "Machine Learning",
                          "Human-Computer Interaction", "Information Visualization", "Vision", "Graphics", "Robotics", "Computer Engineering", "Software Engineering"],
    "physics": ["planetary astronomy", "infrared astronomy", "theoretical astrophysics", "radio astronomy", "Plasma physics", "Nanoscience", "Nanotechnology",
                "Condensed Matter", "Materials Physics", "Energy Systems", "Biophysics", "Microfluidics", "Microsystems", "Optical Physics", "Quantum Information Science"],
    "medicine": ["Cardiology", "Endocrinology", "Diabetes", "Metabolism", "Gastroenterology", "Hepatology", "Internal Medicine", "Clinical Innovation ", "Geriatric Medicine ",
                 "Palliative Care ", "Hematology", "Infectious Diseases", "Immunology", "Nephrology", "Precision Medicine", "Pulmonary", "Critical Care", "Rheumatology"]
}


def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def main():
    for year in range(2023, 2008, -1):
        log_message(f"Processing year {year}")
        for field, terms in fields.items():
            for term in terms:
                log_message(f"Processing field: {field}, term: {term}")
                results = fetch_all_pages(
                    f"{term} doi in:readme,description created:{year}", pageSize=50)
                log_message(
                    f"Fetched {len(results)} results for {term} in {field} for {year}")
                formatted_results = list(map(format_repo, results))
                relative_path = f"out/{year}/{field}/{term}.json"
                directory = path.dirname(relative_path)
                if not path.exists(directory):
                    makedirs(directory)
                log_message(f"Saving results to {relative_path}")
                with open(relative_path, "w") as file:
                    file.write(json.dumps(formatted_results, indent=2))
                log_message(f"Results saved for {term} in {field} for {year}")


if __name__ == "__main__":
    main()
