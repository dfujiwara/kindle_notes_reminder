from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.notebook_parser import parse_notebook_html, NotebookParseError

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
    html_content = await file.read()
    try:
        result = parse_notebook_html(html_content.decode("utf-8"))
        return result.to_dict()  # Return the result as a dictionary
    except NotebookParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
