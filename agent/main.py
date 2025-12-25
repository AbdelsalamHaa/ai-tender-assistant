"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

import os
import httpx
from typing import List, Optional

from copilotkit import CopilotKitState
from langchain.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

# ML Service URL - for local dev use localhost, for Docker use service name
# The agent typically runs outside Docker (via npm run dev), so default to localhost
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8000")


class AgentState(CopilotKitState):
    proverbs: List[str]
    currentPage: Optional[str] = None  # Current page path the user is on
    pageTitle: Optional[str] = None    # Human-readable page title


@tool
def get_weather(location: str):
    """
    Get the weather for a given location.
    """
    return f"The weather for {location} is 70 degrees."


@tool
def search_documents(query: str, top_k: int = 5) -> str:
    """
    Search through ingested documents using semantic similarity.
    Use this tool to find relevant information from the document database.
    
    Args:
        query: The search query - describe what you're looking for
        top_k: Number of results to return (default: 5, max: 20)
    
    Returns:
        Relevant text chunks from documents that match the query
    """
    try:
        # Ensure top_k is within bounds
        top_k = min(max(1, top_k), 20)
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{ML_SERVICE_URL}/api/v1/search",
                json={"query": query, "top_k": top_k},
            )
            
            if response.status_code != 200:
                return f"Search failed with status {response.status_code}: {response.text}"
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                return "No relevant documents found for your query. Try rephrasing or uploading relevant documents first."
            
            # Format results for the LLM
            formatted_results = []
            for i, result in enumerate(results, 1):
                score = result.get("score", 0)
                text = result.get("text", "")
                job_id = result.get("job_id", "unknown")
                
                formatted_results.append(
                    f"**Result {i}** (relevance: {score:.2f}, document: {job_id[:8]}...)\n{text}"
                )
            
            return f"Found {len(results)} relevant passages:\n\n" + "\n\n---\n\n".join(formatted_results)
            
    except httpx.TimeoutException:
        return "Search timed out. The ML service may be busy. Please try again."
    except httpx.ConnectError:
        return "Could not connect to the ML service. Please ensure the service is running."
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def list_ingested_documents(status_filter: Optional[str] = None, limit: int = 10) -> str:
    """
    List all documents that have been ingested into the system.
    Use this to see what documents are available for searching.
    
    Args:
        status_filter: Optional filter by status (COMPLETED, PROCESSING, PENDING, FAILED)
        limit: Maximum number of documents to return (default: 10, max: 50)
    
    Returns:
        List of documents with their titles, authors, and metadata
    """
    try:
        limit = min(max(1, limit), 50)
        
        params = {"limit": limit}
        if status_filter:
            params["status"] = status_filter.upper()
        
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{ML_SERVICE_URL}/api/v1/documents",
                params=params,
            )
            
            if response.status_code != 200:
                return f"Failed to list documents: {response.text}"
            
            data = response.json()
            documents = data.get("documents", [])
            total = data.get("total", 0)
            
            if not documents:
                return "No documents have been ingested yet. Upload PDFs using the ingestion interface."
            
            # Format the document list
            formatted_docs = []
            for doc in documents:
                title = doc.get("title") or doc.get("filename", "Untitled")
                author = doc.get("author") or "Unknown author"
                doc_type = doc.get("document_type") or "Document"
                status = doc.get("status", "UNKNOWN")
                pages = doc.get("page_count") or "?"
                chunks = doc.get("chunk_count") or "?"
                job_id = doc.get("job_id", "")[:8]
                
                formatted_docs.append(
                    f"• **{title}** ({doc_type})\n"
                    f"  Author: {author} | Pages: {pages} | Chunks: {chunks} | Status: {status}\n"
                    f"  ID: {job_id}..."
                )
            
            header = f"📚 **Document Library** ({len(documents)} of {total} documents)\n\n"
            return header + "\n\n".join(formatted_docs)
            
    except httpx.TimeoutException:
        return "Request timed out. The ML service may be busy."
    except httpx.ConnectError:
        return "Could not connect to the ML service. Please ensure the service is running."
    except Exception as e:
        return f"Error listing documents: {str(e)}"


@tool
def get_document_details(job_id: str) -> str:
    """
    Get detailed information about a specific ingested document.
    Use this to see the full extracted information including summary, topics, and entities.
    
    Args:
        job_id: The document/job ID (can be partial, will try to match)
    
    Returns:
        Detailed document information including summary, key topics, and entities
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{ML_SERVICE_URL}/api/v1/documents/{job_id}",
            )
            
            if response.status_code == 404:
                return f"Document with ID '{job_id}' not found. Use list_ingested_documents to see available documents."
            
            if response.status_code != 200:
                return f"Failed to get document details: {response.text}"
            
            doc = response.json()
            
            # Format detailed output
            title = doc.get("title") or doc.get("filename", "Untitled")
            author = doc.get("author") or "Unknown"
            summary = doc.get("summary") or "No summary available"
            doc_type = doc.get("document_type") or "Unknown"
            language = doc.get("language") or "en"
            pages = doc.get("page_count") or "?"
            chunks = doc.get("chunk_count") or "?"
            
            key_topics = doc.get("key_topics") or []
            entities = doc.get("entities") or []
            content_preview = doc.get("content_preview") or ""
            
            result = f"""📄 **{title}**

**Author:** {author}
**Type:** {doc_type}
**Language:** {language.upper()}
**Pages:** {pages} | **Chunks:** {chunks}

**Summary:**
{summary}
"""
            
            if key_topics:
                result += f"\n**Key Topics:** {', '.join(key_topics)}\n"
            
            if entities:
                entity_list = [f"{e.get('name', '')} ({e.get('entity_type', '')})" for e in entities]
                result += f"\n**Entities:** {', '.join(entity_list)}\n"
            
            if content_preview:
                result += f"\n**Content Preview:**\n{content_preview[:300]}..."
            
            return result
            
    except httpx.TimeoutException:
        return "Request timed out."
    except httpx.ConnectError:
        return "Could not connect to the ML service."
    except Exception as e:
        return f"Error getting document details: {str(e)}"


# All backend tools
backend_tools = [
    get_weather,
    search_documents,
    list_ingested_documents,
    get_document_details,
]
backend_tool_names = [tool.name for tool in backend_tools]


async def chat_node(state: AgentState, config: RunnableConfig) -> Command[str]:
    # 1. Define the model
    model = ChatOpenAI(model="gpt-4.1-mini")

    # 2. Bind the tools to the model
    model_with_tools = model.bind_tools(
        [
            *state.get("copilotkit", {}).get("actions", []),
            *backend_tools,
        ],
        parallel_tool_calls=False,
    )

    # 3. Get current page context
    current_page = state.get("currentPage", "/")
    page_title = state.get("pageTitle", "Unknown Page")
    
    # Page-specific context
    page_context = ""
    if current_page == "/":
        page_context = "The user is on the Home page with the Proverbs Dashboard."
    elif current_page == "/ingest":
        page_context = """The user is on the Document Ingestion page where they can upload PDF files.
You can help them understand:
- How to upload tender documents
- What happens during ingestion (parsing, extraction, chunking, embedding)
- How to check ingestion status"""
    elif current_page == "/documents":
        page_context = """The user is on the Tender Document Library page where they can:
- View all ingested documents
- See extracted requirements from each document
- Filter documents by status
- Export requirements to CSV/JSON
You can help them search for specific requirements, analyze documents, or find compliance gaps."""
    else:
        page_context = f"The user is on page: {current_page}"

    # 4. Define the system message
    system_message = SystemMessage(
        content=f"""You are Enest AI Assistant - a helpful assistant for tender document management and requirements analysis.

**Current Context:**
- User is on: {page_title} ({current_page})
- {page_context}

**Available Tools:**

*Backend Tools (for data retrieval):*
- **search_documents**: Search through ingested tender documents using semantic similarity. Use this when users ask questions about requirements, specifications, or document content.
- **list_ingested_documents**: List all available documents in the system. Use this to show users what tender documents are available.
- **get_document_details**: Get detailed information about a specific document including its summary, extracted requirements, topics, and entities.
- **get_weather**: Get weather information for a location.

*Frontend Tools (for UI actions):*
- **navigateToPage**: Navigate the user to a different page. Use this when:
  - User wants to view/browse documents → navigate to "/documents"
  - User wants to upload a new document → navigate to "/ingest"
  - User wants to go home → navigate to "/"
- **setThemeColor**: Change the application's theme color.
- **updateProverbs**: Update the list of proverbs.

**Smart Navigation Guidelines:**
- When listing documents, ALSO navigate to /documents so the user can see them visually
- When user asks to upload or ingest a document, navigate to /ingest
- When user asks about requirements or wants to see document details, navigate to /documents
- Always tell the user you're navigating them and why

**How to Help:**
1. For questions about requirements → use search_documents
2. To see available documents → use list_ingested_documents AND navigateToPage to /documents
3. For specific document details → use get_document_details
4. To help user upload → use navigateToPage to /ingest
5. Provide context-aware suggestions based on the current page

**Additional Context:**
Current proverbs: {state.get('proverbs', [])}
"""
    )

    # 4. Run the model to generate a response
    response = await model_with_tools.ainvoke(
        [
            system_message,
            *state["messages"],
        ],
        config,
    )

    # only route to tool node if tool is not in the tools list
    if route_to_tool_node(response):
        print("routing to tool node")
        return Command(
            goto="tool_node",
            update={
                "messages": [response],
            },
        )

    # 5. We've handled all tool calls, so we can end the graph.
    return Command(
        goto=END,
        update={
            "messages": [response],
        },
    )


def route_to_tool_node(response: BaseMessage):
    """
    Route to tool node if any tool call in the response matches a backend tool name.
    """
    tool_calls = getattr(response, "tool_calls", None)
    if not tool_calls:
        return False

    for tool_call in tool_calls:
        if tool_call.get("name") in backend_tool_names:
            return True
    return False


# Define the workflow graph
workflow = StateGraph(AgentState)
workflow.add_node("chat_node", chat_node)
workflow.add_node("tool_node", ToolNode(tools=backend_tools))
workflow.add_edge("tool_node", "chat_node")
workflow.set_entry_point("chat_node")

graph = workflow.compile()
