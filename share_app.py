import os
import subprocess
import time
from pyngrok import ngrok

print("⭐️ Iniciando servidor Streamlit...")
# Inicia Streamlit en un proceso separado
streamlit_process = subprocess.Popen(
    ["streamlit", "run", "app_web.py", "--server.port=8501", "--server.headless=true"]
)

# Espera un momento para que Streamlit arranque
time.sleep(3)

# Configura ngrok - si tienes un token, descomenta la siguiente línea
# ngrok.set_auth_token("TU_TOKEN_NGROK") 

# Expone el puerto donde se ejecuta Streamlit
public_url = ngrok.connect(8501).public_url
print(f"🚀 ¡Tu aplicación está disponible públicamente en:")
print(f"👉 {public_url}")
print("\nComparte este enlace con quien quieras que pruebe tu chatbot.")
print("⚠️ Este enlace estará activo mientras este script se ejecute.")
print("⚠️ Presiona Ctrl+C para detener la aplicación.")

# Mantén el script ejecutándose
try:
    # Mantén el proceso en ejecución
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # Cierra adecuadamente al presionar Ctrl+C
    print("\n⏹️ Deteniendo servidor...")
    ngrok.kill()
    streamlit_process.terminate()
    print("✅ Servidor detenido correctamente.") 