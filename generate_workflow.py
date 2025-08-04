import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
import json
from datetime import datetime
import math
import re

# --- Supervisor de Calidad y Diseñador Avanzado ---
def finalize_and_layout(ai_response_str, user_request):
    """
    Función definitiva que toma la respuesta de la IA, la valida, la corrige,
    crea las notas y diseña la presentación final.
    """
    try:
        ai_parts = json.loads(ai_response_str)
        nodes = ai_parts.get('nodes', [])
        connections = ai_parts.get('connections', {})
        instructions_text = ai_parts.get('instructions_text', 'No se generaron instrucciones.')

        # --- Auto-Corrección de Conexiones ---
        if nodes and connections:
            target_nodes = {conn['node'] for src in connections.values() for out in src.get('main', []) for conn in out}
            # Un trigger no es un target y no es una sticky note
            trigger_node = next((n for n in nodes if n['name'] not in target_nodes and n['type'] not in ['n8n-nodes-base.stickyNote']), None)
            
            if trigger_node and trigger_node['name'] not in connections:
                # Encontrar el primer nodo que SÍ es un target para conectarlo
                first_node_in_chain = next((n['name'] for n in nodes if n['name'] in target_nodes), None)
                if first_node_in_chain:
                    print(f"...Supervisor: Detectado trigger '{trigger_node['name']}' desconectado. Conectando a '{first_node_in_chain}'...")
                    connections[trigger_node['name']] = {"main": [[{"node": first_node_in_chain, "type": "main", "index": 0}]]}
        
        # --- Creación de la Nota Única de Instrucciones ---
        note_color = "#EAEAEA" # Gris claro
        
        # Cálculo de tamaño dinámico
        lines = instructions_text.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0
        dynamic_width = max(350, max_line_length * 8 + 40) # Ancho mínimo de 350px
        dynamic_height = len(lines) * 20 + 40 # Altura basada en número de líneas
        
        single_note = {
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "name": "Instrucciones de Configuración",
            "parameters": { 
                "content": instructions_text, 
                "color": note_color,
                "width": dynamic_width,
                "height": dynamic_height
            },
            "position": [200, 100] # Posición fija superior izquierda
        }
        
        # Bajar todos los nodos funcionales para hacer espacio
        for node in nodes:
            if 'position' in node and len(node['position']) == 2:
                node['position'][1] += 350

        final_nodes = [single_note] + nodes

        # Ensamblaje final del workflow
        final_workflow = {
            "name": user_request[:60],
            "nodes": final_nodes,
            "connections": connections,
            "active": False,
            "settings": {}
        }
        return json.dumps(final_workflow, indent=2)

    except Exception as e:
        print(f"\nAdvertencia: Ocurrió un error en el post-procesamiento. Error: {e}")
        return None

# --- El resto del script principal ---

# 1. Cargar configuración y clientes
print("Cargando configuración...")
load_dotenv(); google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key: raise ValueError("No se encontró la GOOGLE_API_KEY")
genai.configure(api_key=google_api_key)
client = chromadb.PersistentClient(path="./n8n_db")
collection = client.get_or_create_collection(name="n8n_workflows")
print("✅ Conexión exitosa.")

# 2. La Petición del Usuario (Aquí pondrás las peticiones de prueba)
user_request = "Cuando reciba una nueva fila en una hoja de Google Sheets, envía un mensaje a un canal de Slack."
print(f"\nGenerando workflow para: '{user_request}'")

# 3. Búsqueda de Ejemplos
print("Buscando ejemplos...")
query_embedding = genai.embed_content(model='models/embedding-001', content=user_request)['embedding']
results = collection.query(query_embeddings=[query_embedding], n_results=5, include=["documents"])
examples = "\n\n---\n\n".join(results['documents'][0])
print(f"✅ Encontrados {len(results['documents'][0])} ejemplos.")

# 4. Construcción del "Mega-Prompt" para Gemini
print("Construyendo el prompt final para la IA...")
mega_prompt = f"""
Actúa como un consultor de automatización experto en n8n que está documentando un workflow para un cliente o un colega junior.

**TAREA:**
Genera la lógica de un workflow de n8n basado en la petición de un usuario.

**REGLAS DE SALIDA:**
1. Tu respuesta DEBE ser un único objeto JSON que contenga TRES claves: "nodes", "connections" y "instructions_text".
2. La clave "instructions_text" debe ser un manual de configuración **extremadamente detallado** en texto plano. No uses Markdown.
3. Para CADA nodo que requiera configuración, las instrucciones deben incluir:
   - Un TÍTULO claro (ej: "1. NODO: Google Forms (Disparador)").
   - El OBJETIVO del nodo (ej: "Objetivo: Iniciar el flujo con cada nueva respuesta del formulario.").
   - La CONFIGURACIÓN EXACTA, explicando qué campo cambiar (ej: "Configuración: En el campo 'Form ID', debes pegar el ID de tu formulario.").
   - INSTRUCCIONES PRÁCTICAS de cómo obtener la información (ej: "Instrucciones: El ID del formulario se encuentra en la URL de tu Google Form.").

---
**EJEMPLOS DE WORKFLOWS EXISTENTES (PARA TU INSPIRACIÓN):**
{examples}
---
**PETICIÓN DEL USUARIO:**
"{user_request}"
---
**OBJETO JSON CON NODES, CONNECTIONS, E INSTRUCTIONS_TEXT:**
"""

# 5. Generación y Bucle de Auto-Corrección
print("Enviando petición a Gemini...")
# ... (Aquí iría la lógica de bucle si la implementamos, por ahora es una llamada directa)
model = genai.GenerativeModel('gemini-1.5-pro-latest')
response = model.generate_content(mega_prompt)
clean_response = response.text.strip().replace("```json", "").replace("```", "")

# 6. Ensamblaje, Post-procesamiento y Guardado
print("\n--- ¡WORKFLOW GENERADO POR IA! ---")
print(clean_response)
final_json = finalize_and_layout(clean_response, user_request)

if final_json:
    print("\n--- WORKFLOW FINAL, CORREGIDO Y DISEÑADO ---")
    print(final_json)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"workflow_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(final_json)
    print(f"\n✅ El workflow se ha guardado en '{filename}'")
else:
    print("\n❌ No se pudo generar un workflow válido.")