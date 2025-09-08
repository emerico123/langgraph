
from fastapi import FastAPI, HTTPException, Form, UploadFile, File ,  Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from agent.graph import add_website_content, query_rag, get_available_content_sources, add_document_content, delete_content_source # Updated import
import os # For file operations
import shutil # For saving uploaded files
import traceback # For detailed error logging
from fastapi.templating import Jinja2Templates

app = FastAPI(title="RAG Chat Dashboard", description="A RAG system for website and document content with OpenAI fallback")
templates = Jinja2Templates(directory="templates")
# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create a directory for uploaded documents
UPLOAD_DIR = "./uploaded_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class WebsiteRequest(BaseModel):
    url: str

class QueryRequest(BaseModel):
    query: str
    website_url: str | None = None

class DeleteContentRequest(BaseModel):
    source: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with RAG interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add-website")
async def add_website_endpoint(request: WebsiteRequest):
    """Add a website to the RAG database"""
    try:
        success = add_website_content(request.url)
        if success:
            return {"message": "Website added successfully", "url": request.url}
        else:
            raise HTTPException(status_code=500, detail="Failed to add website")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-document")
async def upload_document_endpoint(file: UploadFile = File(...)):
    """Upload a document to the RAG database"""
    try:
        # Save the uploaded file temporarily
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the document using the graph function
        success = add_document_content(file_location)
        if success:
            return {"message": "Document uploaded and processed successfully", "filename": file.filename}
        else:
            # If processing fails, ensure the temporary file is removed
            if os.path.exists(file_location):
                os.remove(file_location)
            raise HTTPException(status_code=500, detail="Failed to process document")
    except Exception as e:
        # Ensure temporary file is removed on error
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=f"Error uploading or processing document: {str(e)}")

@app.post("/delete-content")
async def delete_content_endpoint(request: DeleteContentRequest):
    """Delete content associated with a source from the RAG database"""
    try:
        success = delete_content_source(request.source)
        if success:
            # Content was actually deleted
            return {"message": "Content deleted successfully", "source": request.source}
        else:
            # No items found to delete, which is not a server error but a client-side misunderstanding or stale data
            raise HTTPException(
                status_code=404, 
                detail=f"Content for source '{request.source}' not found for deletion." # Use 404 for not found
            )
    except HTTPException as http_exc:
        # Re-raise HTTPException directly
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors and log the traceback
        print(f"ERROR: An unexpected error occurred during content deletion for source '{request.source}': {e}")
        print(traceback.format_exc()) # Log the full traceback
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

@app.post("/query")
async def query_content_endpoint(request: QueryRequest):
    """Query the RAG system"""
    try:
        response = query_rag(request.query, request.website_url)
        return {"response": response, "query": request.query}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-content-sources")
async def get_content_sources_endpoint():
    """Get list of available content sources (websites and documents)"""
    try:
        sources = get_available_content_sources()
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
