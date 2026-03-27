import os
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pubmedclient.models import Db, EFetchRequest, ESearchRequest
from pubmedclient.sdk import efetch, esearch, pubmedclient_client
from pydantic import BaseModel, Field
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


class SearchAbstractsRequest(BaseModel):
    """
    Request parameters for NCBI ESearch API for searching abstracts on the PubMed database.

    Functions:
        - Provides a list of abstracts matching a text query

    Examples:
        >>> # Basic search in PubMed for 'asthma' articles abstracts
        >>> SearchAbstractsRequest(term="asthma")

        >>> # Search with publication date range
        >>> ESearchRequest(
        ...     term="asthma",
        ...     mindate="2020/01/01",
        ...     maxdate="2020/12/31",
        ...     datetype="pdat"
        ... )

        >>> # Search with field restriction
        >>> ESearchRequest(term="asthma[title]")
        >>> # Or equivalently:
        >>> ESearchRequest(term="asthma", field="title")

        >>> # Search with proximity operator
        >>> ESearchRequest(term='"asthma treatment"[Title:~3]')

        >>> # Sort results by publication date
        >>> ESearchRequest(
        ...     term="asthma",
        ...     sort="pub_date"
        ... )
    """

    term: str = Field(
        ...,
        description="""Entrez text query. All special characters must be URL encoded.
        Spaces may be replaced by '+' signs. For very long queries (more than several
        hundred characters), consider using an HTTP POST call. See PubMed or Entrez
        help for information about search field descriptions and tags. Search fields
        and tags are database specific.""",
    )

    retmax: Optional[int] = Field(
        20,
        description="""Number of UIDs to return (default=20, max=10000).""",
    )

    sort: Optional[str] = Field(
        None,
        description="""Sort method for results. PubMed values:
        - pub_date: descending sort by publication date
        - Author: ascending sort by first author
        - JournalName: ascending sort by journal name
        - relevance: default sort order ("Best Match")""",
    )
    field: Optional[str] = Field(
        None,
        description="""Search field to limit entire search. Equivalent to adding [field]
        to term.""",
    )
    datetype: Optional[Literal["mdat", "pdat", "edat"]] = Field(
        None,
        description="""Type of date used to limit search:
        - mdat: modification date
        - pdat: publication date
        - edat: Entrez date
        Generally databases have only two allowed values.""",
    )
    reldate: Optional[int] = Field(
        None,
        description="""When set to n, returns items with datetype within the last n
        days.""",
    )
    mindate: Optional[str] = Field(
        None,
        description="""Start date for date range. Format: YYYY/MM/DD, YYYY/MM, or YYYY.
        Must be used with maxdate.""",
    )
    maxdate: Optional[str] = Field(
        None,
        description="""End date for date range. Format: YYYY/MM/DD, YYYY/MM, or YYYY.
        Must be used with mindate.""",
    )


# add a tool
@mcp.tool()
async def search_abstracts(request: SearchAbstractsRequest) -> str:
    """Search abstracts on PubMed database based on the request parameters.

    While it returns a free-form text in practice this is a list of strings containing:

    * the title of the article
    * the abstract content
    * the authors
    * the journal name
    * the publication date
    * the DOI
    * the PMID

    Args:
        request: SearchAbstractsRequest
    """

    async with pubmedclient_client() as client:
        # perform a search and get the ids
        search_request = ESearchRequest(db=Db.PUBMED, **request.model_dump())
        search_response = await esearch(client, search_request)
        ids = search_response.esearchresult.idlist

        # get the abstracts of each ids
        # in practice it returns something like the following:
        #
        # 1. Allergy Asthma Proc. 2025 Jan 1;46(1):1-3. doi: 10.2500/aap.2025.46.240102.
        #
        # Exploring mast cell disorders: Tryptases, hereditary alpha-tryptasemia, and MCAS
        # treatment approaches.
        # Bellanti JA, Settipane RA.
        # DOI: 10.2500/aap.2025.46.240102
        # PMID: 39741377
        #
        # 2. ...
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
