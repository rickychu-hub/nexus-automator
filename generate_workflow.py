import os
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
import json
from datetime import datetime
import math
import re

# La función de diseño se queda como está, fuera de la función principal
def finalize_and_layout(ai_response_str, user_request):
    # ... (esta función se mantiene exactamente igual que en la versión anterior) ...
    try:
        ai_parts = json.loads(ai_response_str)
        nodes = ai_parts.get('nodes', [])
        connections = ai_parts.get('connections', {})
        instructions_text = ai_parts.get('instructions_text', 'No se generaron instrucciones.')
        target_nodes = {conn['node'] for src in connections.values() for out in src.get('main', []) for conn in out}
        trigger_node = next((n for n in nodes if n['name'] not in target_nodes and n['type'] not in ['n8n-nodes-base.stickyNote', 'n8n-nodes-base.start']), None)
        if trigger_node and trigger_node['name'] not in connections:
             first_node_in_chain = nodes[1]['name'] if len(nodes) > 1 else None
             if first_node_in_chain:
                print("...Supervisor: Detectado trigger desconectado. Corrigiendo...")
                connections[trigger_node['name']] = {"main": [[{"node": first_node_in_chain, "type": "main", "index": 0}]]}
        note_color = "#EAEAEA"
        lines = instructions_text.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0
        dynamic_width = max(350, max_line_length * 8 + 40)
        dynamic_height = len(lines) * 20 + 40
        single_note = {
            "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "name": "Instrucciones de Configuración",
            "parameters": { "note": instructions_text, "color": note_color, "width": dynamic_width, "height": dynamic_height },
            "position": [200, 100]
        }
        for node in nodes:
            if 'position' in node and len(node['position']) == 2:
                node['position'][1] += 350
        final_nodes = [single_note] + nodes
        final_workflow = {
            "name": user_request[:60], "nodes": final_nodes,
            "connections": connections, "active": False, "settings": {}
        }
        return json.dumps(final_workflow, indent=2)
    except Exception as e:
        print(f"\nAdvertencia: Ocurrió un error en el post-procesamiento. Error: {e}")
        return None

# --- LA NUEVA FUNCIÓN PRINCIPAL ---
def run_generation_pipeline(user_request: str) -> str | None:
    """
    Toma una petición de usuario y ejecuta todo el proceso de generación de workflow.
    Devuelve el JSON del workflow como una cadena de texto, o None si falla.
    """
    # 1. Cargar configuración y clientes
    print("Cargando configuración y conectando a la base de datos...")
    load_dotenv()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: No se encontró la GOOGLE_API_KEY")
        return None
    genai.configure(api_key=google_api_key)
    client = chromadb.PersistentClient(path="./n8n_db")
    collection = client.get_or_create_collection(name="n8n_workflows")
    print("✅ Conexión exitosa.")

    # 2. Búsqueda de Ejemplos Relevantes
    print("Buscando ejemplos...")
    query_embedding = genai.embed_content(model='models/embedding-001', content=user_request)['embedding']
    results = collection.query(query_embeddings=[query_embedding], n_results=5, include=["documents"])
    examples = "\n\n---\n\n".join(results['documents'][0])
    print(f"✅ Encontrados {len(results['documents'][0])} ejemplos.")

    # 3. Construcción del "Mega-Prompt" para Gemini
    print("Construyendo el prompt final para la IA...")
    mega_prompt = f"""
    Actúa como un consultor de automatización experto en n8n que está documentando un workflow para un cliente o un colega junior.
    **TAREA:**
    Genera la lógica de un workflow de n8n basado en la petición de un usuario.
    **REGLAS DE SALIDA:**
    1. Tu respuesta DEBE ser un único objeto JSON que contenga TRES claves: "nodes", "connections" y "instructions_text".
    2. La clave "instructions_text" debe ser un manual de configuración detallado en texto plano. No uses Markdown.
    3. Para CADA nodo que requiera configuración, las instrucciones deben incluir TÍTULO, OBJETIVO, CONFIGURACIÓN e INSTRUCCIONES PRÁCTICAS.
    ---
    **EJEMPLOS DE WORKFLOWS EXISTENTES (PARA TU INSPIRACIÓN):**
    {examples}
    ---
    **PETICIÓN DEL USUARIO:**
    "{user_request}"
    ---
    **OBJETO JSON CON NODES, CONNECTIONS, E INSTRUCTIONS_TEXT:**
    """

    # 4. Generación con Gemini
    print("Enviando petición a Gemini...")
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    response = model.generate_content(mega_prompt)
    clean_response = response.text.strip().replace("```json", "").replace("```", "")

    # 5. Ensamblaje y Diseño Final
    print("\n--- ¡WORKFLOW GENERADO POR IA! ---")
    print(clean_response)
    final_json = finalize_and_layout(clean_response, user_request)

    return final_json

# --- BLOQUE PARA PROBAR EL SCRIPT DIRECTAMENTE ---
if __name__ == "__main__":
    # Esta parte solo se ejecuta si corres `python generate_workflow.py`
    # No se ejecutará cuando lo importemos desde webapp.py
    
    # 1. Definimos una petición de prueba
    test_request = "Cuando reciba una nueva fila en una hoja de Google Sheets, envía un mensaje a un canal de Slack."
    print(f"--- MODO DE PRUEBA: Ejecutando para la petición: '{test_request}' ---")
    
    # 2. Llamamos a la función principal
    generated_workflow_json = run_generation_pipeline(test_request)
    
    # 3. Guardamos el resultado si es válido
    if generated_workflow_json:
        print("\n--- WORKFLOW FINAL, CORREGIDO Y DISEÑADO ---")
        print(generated_workflow_json)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workflow_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(generated_workflow_json)
        print(f"\n✅ El workflow de prueba se ha guardado en '{filename}'")
    else:
        print("\n❌ No se pudo generar un workflow válido en el modo de prueba.")