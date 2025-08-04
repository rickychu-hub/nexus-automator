import os
import json
import zipfile 
import tempfile 
import shutil 
import time
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

# --- 1. Cargar configuración y clientes ---
print("Cargando configuración e inicializando clientes...")
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("No se encontró la GOOGLE_API_KEY en el archivo .env")
genai.configure(api_key=google_api_key)

client = chromadb.PersistentClient(path="./n8n_db")
collection = client.get_or_create_collection(name="n8n_workflows")
print("¡Clientes listos!")

# --- 2. Descomprimir el Archivo ZIP Local ---
zip_filename = 'workflows.zip'
temp_extract_path = tempfile.mkdtemp()

print(f"Extrayendo archivos de '{zip_filename}' en: {temp_extract_path}")
with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
    zip_ref.extractall(temp_extract_path)
print("Extracción completa.")

# --- 3. Funciones de IA ---
def get_description_from_json(workflow_json_str):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Genera una descripción muy concisa en español del objetivo principal de este workflow de n8n:\n\n{workflow_json_str}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"  -> Error con la API de Gemini: {e}")
        return None

# --- 4. Procesar y Guardar en la Base de Datos ---
workflows_path = os.path.join(temp_extract_path, 'workflows')
if os.path.exists(workflows_path):
    json_files = [f for f in os.listdir(workflows_path) if f.endswith('.json')]
    total_files = len(json_files)
    print(f"\n--- Empezando el procesamiento de {total_files} archivos .json ---")
    
    for i, filename in enumerate(json_files):
        print(f"Procesando archivo {i+1}/{total_files}: {filename}")
        
        # Comprobación para reanudar
        existing = collection.get(ids=[filename])
        if existing['ids']:
            print(f"  -> Ya existe en la base de datos. Saltando.")
            continue
        
        try:
            with open(os.path.join(workflows_path, filename), 'r', encoding='utf-8') as f:
                content_str = f.read()
            
            description = get_description_from_json(content_str)
            if description:
                print(f"  -> Descripción: {description}")
                embedding = genai.embed_content(model='models/embedding-001', content=description)
                collection.add(
                    embeddings=[embedding['embedding']],
                    documents=[content_str],
                    metadatas=[{"description": description, "filename": filename}],
                    ids=[filename]
                )
            time.sleep(1) 
        except Exception as e:
            print(f"  -> Error procesando el archivo {filename}: {e}")
else:
    print(f"Error: No se encontró la ruta de workflows: {workflows_path}")

# --- 5. Limpieza ---
print("\nLimpiando archivos temporales...")
# Ya no borramos el zip, lo dejamos en el servidor
shutil.rmtree(temp_extract_path)
print("Limpieza completada.")
print("\n--- ¡PROCESO DE CREACIÓN DE MEMORIA FINALIZADO! ---")