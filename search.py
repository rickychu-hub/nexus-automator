import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

# --- 1. Cargar configuración y clientes ---
print("Cargando configuración y conectando a la base de datos...")
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("No se encontró la GOOGLE_API_KEY en el archivo .env")
genai.configure(api_key=google_api_key)

client = chromadb.PersistentClient(path="./n8n_db")
collection = client.get_or_create_collection(name="n8n_workflows")
print("✅ Conexión exitosa.")

# --- 2. La Pregunta del Usuario ---
user_query = "un flujo que me avise en discord cuando hay una nueva venta en stripe"
print(f"\nBuscando flujos para: '{user_query}'")

# --- CAMBIO CLAVE ---
# 1. Convertimos la pregunta del usuario en un embedding
query_embedding = genai.embed_content(
    model='models/embedding-001',
    content=user_query
)['embedding']

# 2. Buscamos usando el embedding, no el texto
results = collection.query(
    query_embeddings=[query_embedding], # Usamos el vector numérico para la búsqueda
    n_results=5 # Pedimos 5 resultados para tener más opciones
)

# --- 4. Mostrar los Resultados ---
print("\n--- Resultados Más Relevantes Encontrados ---")
if results['metadatas'][0]:
    for i, metadata in enumerate(results['metadatas'][0]):
        print(f"\nResultado #{i+1}:")
        print(f"  -> Archivo: {metadata['filename']}")
        print(f"  -> Descripción: {metadata['description']}")
else:
    print("No se encontraron resultados relevantes.")