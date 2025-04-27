from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.notebook_parser import parse_notebook_html, NotebookParseError
from src.additional_context import get_additional_context
from src.openai_client import OpenAIClient

app = FastAPI(
    title="FastAPI App", description="A sample FastAPI application", version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI!"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/notebooks")
async def parse_notebook_endpoint(file: UploadFile = File(...)):
    # Initialize the OpenAI client
    openai_client = OpenAIClient()

    html_content = await file.read()
    try:
        # Attempt to parse the notebook HTML content
        result = parse_notebook_html(html_content.decode("utf-8"))
    except NotebookParseError as e:
        raise HTTPException(status_code=400, detail=f"Parsing error: {str(e)}")

    try:
        # Get additional context from OpenAI using dependency injection
        additional_context = await get_additional_context(openai_client, result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting additional context: {str(e)}")

    return {
        "parsed_result": result.to_dict(),  # Return the parsed result
        "additional_context": additional_context  # Include the additional context
    }
