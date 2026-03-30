import os
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pubmedclient.models import Db, EFetchRequest, ESearchRequest
from pubmedclient.sdk import efetch, esearch, pubmedclient_client
from starlette.requests import Request
from starlette.responses import JSONResponse

# Create an MCP server
# stateless_http and json_response only affect streamable-http transport;
# they are no-ops for stdio transport.
mcp = FastMCP("PubMedMCP", stateless_http=True, json_response=True)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return JSONResponse({"status": "healthy", "service": "pubmedmcp"})


@mcp.tool()
async def search_abstracts(
    term: str,
    retmax: int = 20,
    sort: Optional[Literal["pub_date", "Author", "JournalName", "relevance"]] = None,
    field: Optional[str] = None,
    datetype: Optional[Literal["mdat", "pdat", "edat"]] = None,
    reldate: Optional[int] = None,
    mindate: Optional[str] = None,
    maxdate: Optional[str] = None,
) -> str:
    """Search PubMed for article abstracts matching a query.

    Returns a list of matching articles, each containing the title, abstract,
    authors, journal name, publication date, DOI, and PMID.

    Args:
        term: PubMed search query (e.g. "SARS-CoV-2", "asthma[title]",
              "cancer AND immunotherapy"). Supports PubMed Advanced Search syntax
              including field tags like [title], [author], and Boolean operators.
        retmax: Maximum number of articles to return (default 20, max 10000).
        sort: Sort order for results. Options: "pub_date" (newest first),
              "Author" (first author A-Z), "JournalName" (journal A-Z),
              "relevance" (best match, default).
        field: Restrict search to a specific field (e.g. "title", "author",
               "journal"). Equivalent to appending [field] to the term.
        datetype: Type of date to filter by: "mdat" (modification date),
                  "pdat" (publication date), or "edat" (Entrez date).
        reldate: Return only articles with datetype within the last N days.
        mindate: Start of date range filter (format: YYYY/MM/DD, YYYY/MM,
                 or YYYY). Must be used together with maxdate.
        maxdate: End of date range filter (format: YYYY/MM/DD, YYYY/MM,
                 or YYYY). Must be used together with mindate.
    """
    # Build the search request from flat parameters
    search_params: dict = {"term": term, "retmax": retmax}
    if sort is not None:
        search_params["sort"] = sort
    if field is not None:
        search_params["field"] = field
    if datetype is not None:
        search_params["datetype"] = datetype
    if reldate is not None:
        search_params["reldate"] = reldate
    if mindate is not None:
        search_params["mindate"] = mindate
    if maxdate is not None:
        search_params["maxdate"] = maxdate

    async with pubmedclient_client() as client:
        # perform a search and get the ids
        search_request = ESearchRequest(db=Db.PUBMED, **search_params)
        search_response = await esearch(client, search_request)
        ids = search_response.esearchresult.idlist

        # fetch the abstracts for each id
        fetch_request = EFetchRequest(
            db=Db.PUBMED,
            id=",".join(ids),
            retmode="text",
            rettype="abstract",
        )
        fetch_response = await efetch(client, fetch_request)

        return fetch_response


def main():
    transport = os.environ.get("TRANSPORT", "stdio")

    if transport == "streamable-http":
        mcp.settings.host = os.environ.get("HOST", "0.0.0.0")
        mcp.settings.port = int(os.environ.get("PORT", "8000"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
