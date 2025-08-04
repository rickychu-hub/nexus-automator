import streamlit as st
import time
import json
# Importamos la función principal de nuestro otro script
from generate_workflow import run_generation_pipeline 

# --- Interfaz de Usuario de la Aplicación ---

st.set_page_config(page_title="Nexus Automator", layout="wide")

st.title("🤖 Nexus Automator")
st.write("Describe la automatización que necesitas y la IA generará el workflow de n8n por ti.")

# Área de texto para la petición del usuario
user_request = st.text_area("Por ejemplo: 'Cuando reciba un email con una factura, guárdala en Google Drive y avísame por Slack.'", height=150)

# Botón para iniciar la generación
if st.button("Generar Workflow"):
    if user_request:
        # Usar un spinner para mostrar que el proceso está en marcha
        with st.spinner("Buscando en la base de conocimiento y generando con IA... Este proceso puede tardar hasta un minuto."):
            # Llamamos a nuestra función de IA REAL importada
            generated_json = run_generation_pipeline(user_request)
        
        if generated_json:
            st.success("¡Workflow generado con éxito!")
            
            # Mostrar el código JSON resultante
            st.code(generated_json, language='json')
            
            # Añadir un botón para facilitar la descarga
            # Usamos un timestamp para que cada archivo tenga un nombre único
            timestamp = int(time.time())
            st.download_button(
                label="Descargar archivo .json",
                data=generated_json,
                file_name=f"workflow_{timestamp}.json",
                mime="application/json",
            )
        else:
            st.error("Hubo un error al generar el workflow. Por favor, intenta de nuevo o refina tu petición.")
    else:
        st.warning("Por favor, describe la automatización que necesitas antes de generar.")