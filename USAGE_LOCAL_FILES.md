# Ejemplo de uso del PDF Summarizer con archivos locales

## Rutas disponibles:

### 1. Procesar archivo local:
```
POST http://localhost:8000/summarize_local/
Content-Type: application/json

{
    "file_path": "C:\\Users\\Usuario\\Documents\\Rains_2004_principios_de_Neuro.pdf"
}
```

### 2. Ruta unificada (detecta automáticamente URL o archivo local):
```
POST http://localhost:8000/summarize/
Content-Type: application/json

{
    "source": "C:\\Users\\Usuario\\Documents\\Rains_2004_principios_de_Neuro.pdf",
    "source_type": "auto"
}
```

### 3. Ruta unificada para URL:
```
POST http://localhost:8000/summarize/
Content-Type: application/json

{
    "source": "https://arxiv.org/pdf/2301.00001.pdf",
    "source_type": "auto"
}
```

## Ejemplos con curl:

### Archivo local:
```bash
curl -X POST "http://localhost:8000/summarize_local/" \
     -H "Content-Type: application/json" \
     -d '{"file_path": "C:\\Users\\Usuario\\Documents\\Rains_2004_principios_de_Neuro.pdf"}'
```

### Ruta unificada (auto-detección):
```bash
curl -X POST "http://localhost:8000/summarize/" \
     -H "Content-Type: application/json" \
     -d '{"source": "C:\\Users\\Usuario\\Documents\\Rains_2004_principios_de_Neuro.pdf", "source_type": "auto"}'
```

## Validaciones implementadas:

1. **Detección automática**: El sistema detecta si es URL o archivo local
2. **Validación de existencia**: Verifica que el archivo local exista
3. **Validación de formato**: Confirma que sea un archivo PDF
4. **Manejo de errores**: Respuestas apropiadas para errores comunes

## Respuesta:

```json
{
    "source": "C:\\Users\\Usuario\\Documents\\Rains_2004_principios_de_Neuro.pdf",
    "source_type": "local_file",
    "final_summary": "Resumen técnico del documento..."
}
```
