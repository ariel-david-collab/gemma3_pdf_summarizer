"""
Script de prueba para el PDF Summarizer con archivos locales
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_local_file():
    """Prueba el procesamiento de un archivo local"""
    url = f"{BASE_URL}/summarize_local/"
    
    # Cambiar esta ruta por la ruta real de tu archivo PDF
    file_path = r"C:\Users\Usuario\Documents\Rains_2004_principios_de_Neuro.pdf"
    
    payload = {
        "file_path": file_path
    }
    
    print(f"Enviando solicitud para archivo local: {file_path}")
    
    try:
        response = requests.post(url, json=payload, timeout=300)  # 5 minutos timeout
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Éxito!")
            print(f"Fuente: {result['source']}")
            print(f"Tipo: {result['source_type']}")
            print(f"Resumen: {result['final_summary'][:200]}...")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")

def test_unified_endpoint():
    """Prueba el endpoint unificado con auto-detección"""
    url = f"{BASE_URL}/summarize/"
    
    # Cambiar esta ruta por la ruta real de tu archivo PDF
    file_path = r"C:\Users\Usuario\Documents\Rains_2004_principios_de_Neuro.pdf"
    
    payload = {
        "source": file_path,
        "source_type": "auto"
    }
    
    print(f"Enviando solicitud unificada para: {file_path}")
    
    try:
        response = requests.post(url, json=payload, timeout=300)  # 5 minutos timeout
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Éxito!")
            print(f"Fuente: {result['source']}")
            print(f"Tipo detectado: {result['source_type']}")
            print(f"Resumen: {result['final_summary'][:200]}...")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")

def test_health():
    """Verifica que el servidor esté funcionando"""
    url = f"{BASE_URL}/health"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("✅ Servidor funcionando correctamente")
            return True
        else:
            print(f"❌ Servidor respondió con código: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ No se puede conectar al servidor: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Probando PDF Summarizer con archivos locales")
    print("=" * 60)
    
    # Verificar que el servidor esté funcionando
    if not test_health():
        print("\n⚠️ Asegúrate de que el servidor esté ejecutándose:")
        print("   python main.py")
        exit(1)
    
    print("\n1. Probando endpoint específico para archivos locales:")
    print("-" * 50)
    test_local_file()
    
    print("\n2. Probando endpoint unificado con auto-detección:")
    print("-" * 50)
    test_unified_endpoint()
    
    print("\n✅ Pruebas completadas")
