import asyncio
import logging
import os
import traceback
from typing import List, Dict, Any

import fitz  # PyMuPDF
import httpx
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

# Constants for better readability and maintainability
OLLAMA_API_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma3:27b-16k"
CHUNK_SIZE = 40000  # Approximately 32K tokens
CHUNK_OVERLAP = 100
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 5  # Seconds
HTTP_TIMEOUT = httpx.Timeout(connect=60, read=3600, write=60, pool=60)  # 15-minute read timeout


class URLRequest(BaseModel):
    url: str


@app.get("/health")
def health_check():
    """Performs a health check and returns a status message."""
    return {"status": "ok", "message": "FastAPI backend is running!"}


@app.post("/summarize_arxiv/")
async def summarize_arxiv(request: URLRequest):
    """Downloads an Arxiv PDF, extracts text, and summarizes it using Ollama (Gemma 3) in parallel."""
    try:
        url = request.url
        logger.info("---------------------------------------------------------")
        logger.info(f"Downloading PDF from: {url}")

        pdf_path = await download_pdf(url)
        if not pdf_path:
            return {"error": "Failed to download PDF. Check the URL."}

        logger.info(f"PDF saved at: {pdf_path}")

        text = await extract_text_from_pdf(pdf_path)
        if not text:
            return {"error": "No text extracted from PDF"}

        logger.info(f"Extracted text length: {len(text)} characters")
        logger.info("---------------------------------------------------------")

        summary = await summarize_text_parallel(text)
        logger.info("Summarization complete")

        return {"summary": summary}

    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return {"error": "Failed to process PDF"}


async def download_pdf(url: str) -> str | None:
    """Downloads a PDF from a given URL and saves it locally."""
    try:
        if not url.startswith("https://arxiv.org/pdf/"):
            logger.error(f"Invalid URL: {url}")
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

            if "application/pdf" not in response.headers.get("Content-Type", ""):
                logger.error(
                    f"Failed to download PDF: Invalid Content-Type: {response.headers.get('Content-Type', '')}"
                )
                return None

            pdf_filename = "arxiv_paper.pdf"
            with open(pdf_filename, "wb") as f:
                f.write(response.content)
            return pdf_filename

    except httpx.RequestError as e:
        logger.error(f"Error downloading PDF: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading PDF: {e}")
        return None


async def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts text from a PDF file using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        text = "\n".join(page.get_text("text") for page in doc)
        return text
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        return ""


async def summarize_chunk_with_retry(
    chunk: str, chunk_id: int, total_chunks: int, max_retries: int = MAX_RETRIES
) -> str:
    """Retry mechanism wrapper for summarize_chunk_wrapper."""
    retries = 0
    while retries <= max_retries:
        try:
            if retries > 0:
                logger.info(
                    f"🔄 Retry attempt {retries}/{max_retries} for chunk {chunk_id}/{total_chunks}"
                )

            result = await summarize_chunk_wrapper(chunk, chunk_id, total_chunks)

            if isinstance(result, str) and result.startswith("Error"):
                logger.warning(
                    f"⚠️ Soft error on attempt {retries+1}/{max_retries+1} for chunk {chunk_id}: {result}"
                )
                retries += 1
                if retries <= max_retries:
                    wait_time = RETRY_BACKOFF_BASE * (2 ** (retries - 1))
                    logger.info(
                        f"⏳ Waiting {wait_time}s before retry for chunk {chunk_id}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ All retry attempts failed for chunk {chunk_id}")
                    return result
            else:
                if retries > 0:
                    logger.info(
                        f"✅ Successfully processed chunk {chunk_id} after {retries} retries"
                    )
                return result

        except Exception as e:
            retries += 1
            logger.error(
                f"❌ Exception on attempt {retries}/{max_retries+1} for chunk {chunk_id}: {str(e)}"
            )

            if retries <= max_retries:
                wait_time = RETRY_BACKOFF_BASE * (2 ** (retries - 1))
                logger.info(
                    f"⏳ Waiting {wait_time}s before retry for chunk {chunk_id}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ All retry attempts exhausted for chunk {chunk_id}")
                return f"Error processing chunk {chunk_id} after {max_retries+1} attempts: {str(e)}"

    return f"Error: Unexpected end of retry loop for chunk {chunk_id}"


async def summarize_text_parallel(text: str) -> str:
    """Process text in chunks with full parallelism and retry logic."""
    token_estimate = len(text) // 4
    logger.info(f"📝 Token Estimate: {token_estimate}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    logger.info("---------------------------------------------------------")
    logger.info(f"📚 Split text into {len(chunks)} chunks")
    logger.info("---------------------------------------------------------")

    for i, chunk in enumerate(chunks, 1):
        chunk_length = len(chunk)
        logger.info(
            f"📊 Length: {chunk_length} characters ({chunk_length // 4} estimated tokens)"
        )

    logger.info("---------------------------------------------------------")
    logger.info(f"🔄 Processing {len(chunks)} chunks in parallel with retry mechanism...")

    tasks = [
        summarize_chunk_with_retry(chunk, i + 1, len(chunks))
        for i, chunk in enumerate(chunks)
    ]

    try:
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        processed_summaries: List[str] = []
        for i, result in enumerate(summaries):
            if isinstance(result, Exception):
                logger.error(f"❌ Task for chunk {i+1} returned an exception: {str(result)}")
                processed_summaries.append(f"Error processing chunk {i+1}: {str(result)}")
            else:
                processed_summaries.append(result)

        summaries = processed_summaries

    except Exception as e:
        logger.error(f"❌ Critical error in gather operation: {str(e)}")
        return f"Critical error during processing: {str(e)}"

    logger.info("✅ All chunks processed (with or without errors)")

    successful_summaries = [
        s for s in summaries if not (isinstance(s, str) and s.startswith("Error"))
    ]
    if not successful_summaries:
        logger.warning("⚠️ No successful summaries were generated.")
        return "No meaningful summary could be generated. All chunks failed processing."

    combined_chunk_summaries = "\n\n".join(
        f"Section {i+1}:\n{summary}" for i, summary in enumerate(summaries)
    )
    logger.info(f"📝 Combined summaries length: {len(combined_chunk_summaries)} characters")
    logger.info("🔄 Generating final summary...")

    final_summary = await generate_final_summary(combined_chunk_summaries)
    return final_summary


async def generate_final_summary(combined_chunk_summaries: str) -> str:
    """Generates the final summary from combined chunk summaries."""
    final_messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": "You are a technical documentation writer. Focus ONLY on technical details, implementations, and results. DO NOT mention papers, citations, or authors.",
        },
        {
            "role": "user",
            "content": f"""Create a comprehensive technical document focusing ONLY on the implementation and results.
            Structure the content into these sections:

            1. System Architecture
            2. Technical Implementation
            3. Infrastructure & Setup
            4. Performance Analysis
            5. Optimization Techniques

            CRITICAL INSTRUCTIONS:
            - Focus ONLY on technical details and implementations
            - Include specific numbers, metrics, and measurements
            - Explain HOW things work
            - DO NOT include any citations or references
            - DO NOT mention other research or related work
            - Some sections may contain error messages - please ignore these and work with available information

            Content to organize:
            {combined_chunk_summaries}
            """,
        },
    ]

    retry_count = 0
    final_response: Dict[str, Any] | None = None

    while retry_count <= MAX_RETRIES:
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": final_messages,
                "stream": False,
            }

            logger.info(
                f"📤 Sending final summary request (attempt {retry_count+1}/{MAX_RETRIES+1})"
            )
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    OLLAMA_API_URL, json=payload, timeout=HTTP_TIMEOUT
                )
                response.raise_for_status()

                logger.info(
                    f"📥 Received final summary response, status code: {response.status_code}"
                )

                final_response = response.json()
                break

        except httpx.HTTPError as e:
            retry_count += 1
            logger.error(
                f"❌ Error generating final summary (attempt {retry_count}/{MAX_RETRIES+1}): {str(e)}"
            )

            if retry_count <= MAX_RETRIES:
                wait_time = 10 * (2 ** (retry_count - 1))
                logger.info(
                    f"⏳ Waiting {wait_time}s before retrying final summary generation"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ All retry attempts for final summary failed")
                return "Failed to generate final summary after multiple attempts. Please check the logs for details."
        except Exception as e:
            logger.error(f"❌ Unexpected error generating final summary: {e}")
            return "Failed to generate final summary due to an unexpected error. Please check the logs for details."

    if not final_response:
        return "Failed to generate final summary. Please check the logs for details."

    logger.info("✅ Final summary generated")
    logger.info(
        f"📊 Final summary length: {len(final_response['message']['content'])} characters"
    )
    return final_response["message"]["content"]


async def summarize_chunk_wrapper(
    chunk: str, chunk_id: int, total_chunks: int
) -> str:
    """Asynchronous wrapper for summarizing a single chunk using Ollama via async httpx."""
    logger.info("---------------------------------------------------------")
    logger.info(f"🎯 Starting processing of chunk {chunk_id}/{total_chunks}")
    try:
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": "Extract only technical details. No citations or references.",
            },
            {"role": "user", "content": f"Extract technical content: {chunk}"},
        ]

        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                logger.info(
                    f"📤 Sending request for chunk {chunk_id}/{total_chunks} to Ollama API - {OLLAMA_MODEL}"
                )
                response = await client.post(OLLAMA_API_URL, json=payload)
                response.raise_for_status()

                logger.info("---------------------------------------------------------")
                logger.info(
                    f"📥 Received response for chunk {chunk_id}/{total_chunks}, status code: {response.status_code}"
                )

                response_data = response.json()
                summary = response_data["message"]["content"]

            logger.info(f"✅ Completed chunk {chunk_id}/{total_chunks}")
            logger.info(f"📑 Summary length: {len(summary)} characters")
            logger.info("---------------------------------------------------------")
            return summary

        except httpx.TimeoutException as te:
            error_msg = f"Timeout error for chunk {chunk_id}: {str(te)}"
            logger.error(error_msg)
            return f"Error in chunk {chunk_id}: Request timed out. Consider increasing the timeout or reducing chunk size."

        except httpx.ConnectError as ce:
            error_msg = f"Connection error for chunk {chunk_id}: {str(ce)}"
            logger.error(error_msg)
            return f"Error in chunk {chunk_id}: Could not connect to Ollama API. Check if Ollama is running correctly."

        except httpx.HTTPError as he:
            error_msg = f"HTTP error for chunk {chunk_id}: {str(he)}"
            logger.error(error_msg)
            return f"Error in chunk {chunk_id}: HTTP error from Ollama API. Status code: {he.response.status_code}"

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"❌ Error processing chunk {chunk_id}: {str(e)}")
        logger.error(f"Traceback: {error_details}")
        return f"Error processing chunk {chunk_id}: {str(e)}"


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting FastAPI server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

