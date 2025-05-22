# backend/src/main.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware # Importa para permitir requisições do frontend
import io
import os
import zipfile
from dotenv import load_dotenv

# Importa a função principal de geração de podcast do seu módulo
from .podcast_generator import generate_podcast_from_pdf

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = FastAPI(
    title="Gerador de Podcast a partir de PDF",
    description="API para transformar documentos PDF em podcasts com IA.",
    version="1.0.0"
)

# Configuração do CORS (Cross-Origin Resource Sharing)
# Isso é crucial para permitir que seu frontend (que estará em um domínio/porta diferente)
# se comunique com o seu backend.
# Em produção, você deve restringir 'origins' aos domínios do seu frontend.
origins = [
    "http://localhost",
    "http://localhost:3000", # Porta padrão do Create React App/Vite
    # Adicione aqui o domínio do seu frontend em produção, ex: "https://seusite.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todos os headers
)

@app.get("/")
async def read_root():
    """
    Endpoint de teste simples para verificar se a API está funcionando.
    """
    return {"message": "Bem-vindo à API do Gerador de Podcast!"}

@app.post("/generate-podcast/")
async def generate_podcast_endpoint(pdf_file: UploadFile = File(...)):
    """
    Endpoint para receber um arquivo PDF, gerar um podcast e retornar os segmentos de áudio.
    """
    if not pdf_file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos.")

    try:
        # Lê o conteúdo do PDF como bytes
        pdf_bytes = await pdf_file.read()

        # Chama a função principal de geração de podcast
        audio_segments, metrics = generate_podcast_from_pdf(pdf_bytes)

        if audio_segments is None:
            raise HTTPException(status_code=500, detail=metrics) # metrics aqui é a mensagem de erro

        # Cria um arquivo ZIP em memória para os segmentos de áudio
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for filename, audio_bytes in audio_segments:
                zip_file.writestr(filename, audio_bytes)
        zip_buffer.seek(0) # Volta ao início do buffer

        # Retorna o arquivo ZIP como um StreamingResponse
        # O frontend poderá baixar este arquivo ZIP
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=podcast_segments_{os.path.basename(pdf_file.filename).replace('.pdf', '')}.zip",
                "X-Podcast-Metrics": metrics # Você pode passar métricas no header, se quiser
            }
        )
    except HTTPException as e:
        # Re-lança exceções HTTP para que FastAPI as trate
        raise e
    except Exception as e:
        # Captura outras exceções e retorna um erro 500
        print(f"Erro inesperado no endpoint /generate-podcast/: {e}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")
