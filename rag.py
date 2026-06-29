from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore[reportMissingImports]
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

CHROMA_DB = "chroma_db"
def load_pdf_to_chroma(pdf_path: str):
    print(f"loading PDF: {pdf_path} into ChromaDB")

    #Loading the pdf file
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    #split the pages into smaller chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(pages)
    print(f"Split into {len(chunks)} chunks")

    #Embed and store into ChromaDB
    embeddings = GoogleGenerativeAIEmbeddings(model = "models/text-embedding-004")
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_DB)
    print(f"stored in ChromaDB at ./{CHROMA_DB}")

    return vectorstore

def get_vectorstore():
    
    embeddings = GoogleGenerativeAIEmbeddings(model = "models/text-embedding-004")

    return Chroma(persist_directory=CHROMA_DB, embedding_function=embeddings)

def search_notes(vectorstore, query: str, k: int =3) ->str:
    """Search the notes for the most relevant chunks"""

    docs = vectorstore.similarity_search(query, k=k)    

    return "\n\n".join([doc.page_content for doc in docs])


