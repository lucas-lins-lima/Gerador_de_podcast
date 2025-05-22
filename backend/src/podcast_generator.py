# backend/src/podcast_generator.py

import os
import io
import fitz # Importa PyMuPDF (fitz)
from PIL import Image
import google.generativeai as genai
import base64
import re
import tempfile # Para criação de arquivos temporários
import pyttsx3 # Biblioteca para Text-to-Speech offline (usa vozes do sistema)
import time # Para adicionar delays em caso de erro de permissão
from dotenv import load_dotenv # Importa para carregar variáveis de ambiente

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Configuração (agora lida por variáveis de ambiente) ---
# A chave da API do Gemini será lida do .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY não configurada. Por favor, adicione-a ao seu arquivo .env.")

genai.configure(api_key=GEMINI_API_KEY)

# Nomes dos apresentadores do podcast
PRESENTER_1_NAME = os.getenv("PRESENTER_1_NAME", "Apresentador João")
PRESENTER_2_NAME = os.getenv("PRESENTER_2_NAME", "Apresentadora Maria")

# IDs das vozes para pyttsx3.
# Agora lidos de variáveis de ambiente.
MALE_VOICE_ID = os.getenv("MALE_VOICE_ID", "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_PT-BR_DANIEL_11.0")
FEMALE_VOICE_ID = os.getenv("FEMALE_VOCHKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_PT-BR_MARIA_11.0")

# Tempo médio desejado para o podcast em minutos.
TARGET_PODCAST_DURATION_MINUTES = int(os.getenv("TARGET_PODCAST_DURATION_MINUTES", 15))

# --- Funções ---

def extract_content_from_pdf(pdf_bytes: bytes):
    """
    Extrai texto e imagens de um arquivo PDF em bytes usando PyMuPDF (fitz).
    Retorna o conteúdo de texto e uma lista de dados de imagem em base64.
    """
    text_content = ""
    image_data_for_gemini = []

    print(f"Iniciando a extração de conteúdo do PDF a partir dos bytes.")
    try:
        # Abre o documento PDF a partir dos bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Extrai o texto da página
            text_content += page.get_text() + "\n"

            # Extrai imagens da página
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                
                if base_image and 'image' in base_image and base_image['image']:
                    img_bytes = base_image['image']
                    
                    try:
                        img = Image.open(io.BytesIO(img_bytes))
                        buffered = io.BytesIO()
                        img.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                        image_data_for_gemini.append({
                            "mime_type": "image/png",
                            "data": img_str
                        })
                        print(f"  Imagem da página {page_num+1} extraída e convertida para base64.")
                    except Exception as img_e:
                        print(f"  Aviso: Não foi possível processar a imagem da página {page_num+1} (xref {xref}): {img_e}")
                else:
                    print(f"  Aviso: Imagem vazia ou inválida encontrada na página {page_num+1} (xref {xref}).")

        doc.close()
        print("Extração de texto e imagens concluída.")
    except Exception as e:
        print(f"Erro ao extrair conteúdo do PDF: {e}")
        return "", []

    return text_content, image_data_for_gemini

def upload_images_to_gemini(image_data_list):
    """
    Salva imagens base64 em arquivos temporários e as envia para o Gemini File API.
    Retorna uma lista de objetos File (referências para as imagens no Gemini).
    """
    uploaded_files = []
    temp_file_paths = [] # Armazena os caminhos dos arquivos temporários
    print("Iniciando upload de imagens para o Gemini...")
    try:
        for i, img_data in enumerate(image_data_list):
            if img_data["mime_type"] == "image/png":
                img_bytes = base64.b64decode(img_data["data"])
                
                # Cria um arquivo temporário e obtém o descritor e o caminho
                fd, temp_file_path = tempfile.mkstemp(suffix=".png")
                os.close(fd) # Fecha o descritor de arquivo imediatamente
                temp_file_paths.append(temp_file_path) # Armazena o caminho para limpeza posterior

                # Escreve os bytes no arquivo
                with open(temp_file_path, 'wb') as tmp:
                    tmp.write(img_bytes)
                
                # Envia o arquivo para o Gemini
                file = genai.upload_file(path=temp_file_path, display_name=f"podcast_image_{i}.png")
                uploaded_files.append(file)
                print(f"  Imagem {i+1} enviada para o Gemini (URI: {file.uri}).")
        print("Upload de imagens concluído.")
    except Exception as e:
        print(f"Erro durante o upload de imagens para o Gemini: {e}")
        # Garante que os arquivos temporários locais sejam limpos mesmo em caso de erro
        for f_path in temp_file_paths:
            if os.path.exists(f_path):
                try:
                    time.sleep(0.1) # Pequeno atraso para liberar o handle do arquivo
                    os.remove(f_path)
                except PermissionError as pe:
                    print(f"Aviso: Não foi possível deletar o arquivo temporário {f_path} devido a erro de permissão: {pe}")
        # Tenta deletar arquivos que já foram enviados para o Gemini se o erro ocorreu no meio do processo
        for uploaded_file in uploaded_files:
            try:
                genai.delete_file(uploaded_file.name)
            except Exception as delete_e:
                print(f"Aviso: Não foi possível deletar o arquivo enviado {uploaded_file.name}: {delete_e}")
        return []
    finally:
        # Limpa os arquivos temporários locais, garantindo que estejam fechados
        for f_path in temp_file_paths:
            if os.path.exists(f_path):
                try:
                    time.sleep(0.1) # Pequeno atraso para liberar o handle do arquivo
                    os.remove(f_path)
                except PermissionError as pe:
                    print(f"Aviso: Não foi possível deletar o arquivo temporário {f_path} no bloco finally: {pe}")
    return uploaded_files

def delete_uploaded_gemini_files(uploaded_files):
    """
    Deleta os arquivos enviados para o Gemini File API.
    """
    print("Iniciando exclusão de arquivos do Gemini...")
    for file in uploaded_files:
        try:
            genai.delete_file(file.name)
        except Exception as e:
            print(f"Erro ao deletar arquivo {file.display_name} (URI: {file.uri}): {e}")
    print("Exclusão de arquivos do Gemini concluída.")

def clean_script_text(text):
    """
    Remove todos os caracteres especiais de uma string, exceto vírgulas e pontos.
    """
    # Remove caracteres que não são letras, números, espaços, vírgulas ou pontos
    cleaned_text = re.sub(r'[^\w\s,.]', '', text)
    # Substitui múltiplos espaços por um único espaço
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def generate_podcast_script(text_content, uploaded_image_files, presenter1, presenter2, target_duration_minutes):
    """
    Gera um roteiro de podcast usando o modelo Gemini, com base no conteúdo textual e nas imagens referenciadas.
    Divide o processo para lidar com o limite de payload e tenta controlar a duração.
    """
    print("Gerando roteiro do podcast com IA (Gemini)...")
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        full_script = ""

        # Estimativa de palavras por minuto para o roteiro (média de fala natural)
        WORDS_PER_MINUTE = 150
        # Estimativa de palavras por segmento
        estimated_words_per_segment = (target_duration_minutes * WORDS_PER_MINUTE) / 5 # Assume 5 tópicos inicialmente

        # --- Etapa 1: Gerar tópicos principais (texto-base) ---
        print("  Gerando tópicos principais do conteúdo...")
        # Limita o texto inicial para o prompt de tópicos para garantir que não exceda limites
        limited_text_for_topics = text_content[:8000] 

        topics_prompt = [
            f"Com base no seguinte conteúdo do material de faculdade, liste os 5 a 10 tópicos principais "
            f"que seriam ideais para uma discussão em podcast. O podcast terá uma duração de aproximadamente {target_duration_minutes} minutos. "
            f"Formate como uma lista numerada de títulos de tópicos.\n\n"
            f"Conteúdo:\n{limited_text_for_topics}"
        ]
        
        topics_response = model.generate_content(topics_prompt)
        topics_raw = topics_response.text
        print("  Tópicos principais gerados.")
        
        # Extrair tópicos de uma lista numerada (ex: "1. Tópico A\n2. Tópico B")
        topics = [line.strip() for line in topics_raw.split('\n') if line.strip() and re.match(r'^\d+\.', line.strip())]
        if not topics:
            print("  Não foi possível extrair tópicos numerados. Tentando gerar roteiro com o texto completo como um único segmento.")
            topics = ["Discussão Completa do Material"] # Fallback para um único tópico
        
        # Ajusta a estimativa de palavras por segmento com base no número real de tópicos
        if len(topics) > 0:
            estimated_words_per_segment = (target_duration_minutes * WORDS_PER_MINUTE) / len(topics)
            print(f"  Estimativa de {int(estimated_words_per_segment)} palavras por segmento para atingir {target_duration_minutes} minutos.")

        # --- Etapa 2: Gerar roteiro detalhado para cada tópico ---
        for i, topic in enumerate(topics):
            print(f"  Gerando segmento do roteiro para: '{topic}' ({i+1}/{len(topics)})")
            
            # Tenta encontrar um trecho relevante do texto para o tópico
            text_chunk = ""
            if topic in text_content:
                start_index = text_content.find(topic)
                if start_index != -1:
                    chunk_start = max(0, start_index - 500)
                    chunk_end = min(len(text_content), start_index + len(topic) + 3500)
                    text_chunk = text_content[chunk_start:chunk_end]
            
            if not text_chunk and len(topics) == 1:
                text_chunk = text_content
            elif not text_chunk:
                chunk_size = 4000
                text_chunk = text_content[i * chunk_size : (i + 1) * chunk_size]
                if not text_chunk:
                    continue

            segment_prompt_parts = [
                f"Você é um roteirista de podcast profissional. "
                f"Crie um segmento de roteiro de podcast para uma discussão entre {presenter1} e {presenter2} "
                f"sobre o tópico '{topic}'. O segmento deve ser dinâmico, envolvente e educativo em português. "
                f"Tente manter este segmento com aproximadamente {int(estimated_words_per_segment)} palavras. "
                f"Incorpore as informações do seguinte trecho de texto e, se relevante, as informações visuais "
                f"das imagens fornecidas. Explique a relevância das imagens para o tópico.\n\n"
                f"Trecho de texto:\n{text_chunk}\n\n"
            ]
            
            for file_ref in uploaded_image_files:
                segment_prompt_parts.append(file_ref)
                segment_prompt_parts.append(f"\nPor favor, analise esta imagem (URI: {file_ref.uri}) e incorpore suas informações "
                                             f"e insights na discussão do podcast, explicando o que ela representa "
                                             f"e como se relaciona com o tópico atual.\n")

            segment_prompt_parts.append(f"\nFormato do diálogo esperado (sem aspas ou marcadores de fala):"
                                         f"\n{presenter1}: [Fala do {presenter1}]"
                                         f"\n{presenter2}: [Fala do {presenter2}]"
                                         f"\nNão use aspas ou marcadores como 'Abre aspas', 'Fecha aspas'."
                                         f"\nMantenha as falas relativamente curtas para um fluxo natural."
                                         f"\nAs falas devem conter apenas letras, números, espaços, vírgulas e pontos. Não use outros caracteres especiais."
                                        )

            segment_response = model.generate_content(segment_prompt_parts)
            full_script += segment_response.text + "\n\n"
            print(f"  Segmento gerado para '{topic}'.")

        # Adiciona a seção de tópicos abordados no final do script completo
        full_script += "\nPrincipais tópicos abordados:\n"
        for i, topic in enumerate(topics):
            full_script += f"{i+1}. {topic}\n"

        print("Roteiro gerado com sucesso!")
        # Limpa o script antes de retorná-lo
        cleaned_full_script = clean_script_text(full_script)
        return cleaned_full_script
    except Exception as e:
        print(f"Erro ao gerar o roteiro com Gemini: {e}")
        return None

def generate_audio_segments(script_text, presenter1_name, presenter2_name, male_voice_id, female_voice_id):
    """
    Gera arquivos de áudio WAV separados para cada fala, usando pyttsx3.
    Retorna uma lista de tuplas (nome_do_arquivo, bytes_do_audio).
    """
    print(f"Gerando arquivos de áudio WAV individuais com pyttsx3.")
    
    generated_audio_data = [] # Lista para armazenar os bytes dos arquivos gerados

    try:
        engine = pyttsx3.init()
        
        print("  Tentando auto-detectar vozes masculinas e femininas disponíveis no sistema...")
        voices = engine.getProperty('voices')
        
        pt_br_male_voice_id = None
        pt_br_female_voice_id = None

        for voice in voices:
            voice_name_lower = voice.name.lower()
            if "brazil" in voice_name_lower or "portuguese" in voice_name_lower or "português" in voice_name_lower:
                if ("male" in voice_name_lower or "masculino" in voice_name_lower or "daniel" in voice_name_lower) and pt_br_male_voice_id is None:
                    pt_br_male_voice_id = voice.id
                    print(f"  Voz masculina (PT-BR) auto-detectada: {voice.name}")
                elif ("female" in voice_name_lower or "feminino" in voice_name_lower or "maria" in voice_name_lower) and pt_br_female_voice_id is None:
                    pt_br_female_voice_id = voice.id
                    print(f"  Voz feminina (PT-BR) auto-detectada: {voice.name}")
            
            if pt_br_male_voice_id and pt_br_female_voice_id:
                break

        if male_voice_id is None and pt_br_male_voice_id:
            male_voice_id = pt_br_male_voice_id
        if female_voice_id is None and pt_br_female_voice_id:
            female_voice_id = pt_br_female_voice_id
        
        if not male_voice_id:
            print("  Aviso: Voz masculina específica não encontrada. Tentando voz masculina genérica.")
            for voice in voices:
                if voice.gender == 'male' or 'male' in voice.name.lower():
                    male_voice_id = voice.id
                    print(f"  Voz masculina genérica auto-detectada: {voice.name}")
                    break
            if not male_voice_id and voices:
                male_voice_id = voices[0].id

        if not female_voice_id:
            print("  Aviso: Voz feminina específica não encontrada. Tentando voz feminina genérica.")
            for voice in voices:
                if voice.gender == 'female' or 'female' in voice.name.lower():
                    female_voice_id = voice.id
                    print(f"  Voz feminina genérica auto-detectada: {voice.name}")
                    break
            if not female_voice_id and voices:
                female_voice_id = voices[1].id if len(voices) > 1 else voices[0].id

        if not male_voice_id or not female_voice_id:
            print("Erro: Não foi possível encontrar vozes masculina e/ou feminina adequadas no sistema. A geração de áudio pode não ter distinção de gênero.")
            if male_voice_id:
                engine.setProperty('voice', male_voice_id)
            elif female_voice_id:
                engine.setProperty('voice', female_voice_id)
            else:
                print("Erro: Nenhuma voz de Text-to-Speech utilizável encontrada no sistema. A geração de áudio não pode prosseguir.")
                return []
            if not male_voice_id: male_voice_id = female_voice_id
            if not female_voice_id: female_voice_id = male_voice_id

        joao_rate = 160
        maria_rate = 190
        joao_volume = 1.0
        maria_volume = 0.9

        lines = script_text.split('\n')

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            text_to_synthesize = line
            current_voice_id = None
            current_rate = engine.getProperty('rate')
            current_volume = engine.getProperty('volume')

            if line.startswith(f"{presenter1_name}:"):
                current_voice_id = male_voice_id
                text_to_synthesize = line.replace(f"{presenter1_name}:", "").strip()
                current_rate = joao_rate
                current_volume = joao_volume
            elif line.startswith(f"{presenter2_name}:"):
                current_voice_id = female_voice_id
                text_to_synthesize = line.replace(f"{presenter2_name}:", "").strip()
                current_rate = maria_rate
                current_volume = maria_volume
            else:
                current_voice_id = male_voice_id 
                current_rate = joao_rate 
                current_volume = joao_volume

            if text_to_synthesize and current_voice_id:
                engine.setProperty('voice', current_voice_id)
                engine.setProperty('rate', current_rate)
                engine.setProperty('volume', current_volume)
                
                # Salva o áudio em um buffer de memória em vez de um arquivo
                # pyttsx3 não suporta salvar diretamente para um buffer, então usamos um tempfile
                with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as fp:
                    engine.save_to_file(text_to_synthesize, fp.name)
                    engine.runAndWait()
                    fp.seek(0) # Volta ao início do arquivo
                    audio_bytes = fp.read()
                    generated_audio_data.append((f"segment_{i:03d}.wav", audio_bytes))
                    print(f"  Gerado segmento de áudio {i:03d}.")
                
                time.sleep(0.5)

        if not generated_audio_data:
            print("Erro: Nenhum arquivo de áudio foi gerado com sucesso. Verifique o roteiro e as vozes.")
            return []

        print(f"Todos os segmentos de áudio foram gerados com sucesso.")
        return generated_audio_data
    except Exception as e:
        print(f"Erro ao gerar o áudio com pyttsx3: {e}.")
        print("Verifique se as vozes de Text-to-Speech estão instaladas no seu sistema,")
        print("e se pyttsx3 está instalado.")
        return []

def calculate_podcast_metrics(script_text, presenter1, presenter2):
    """
    Calcula e exibe métricas relevantes para o podcast, como número de participantes,
    nomes e tempo estimado. Também tenta extrair os tópicos abordados do roteiro.
    """
    print("\n--- Métricas do Podcast ---")
    num_participants = 2
    presenter_names = f"{presenter1}, {presenter2}"

    word_count = len(script_text.split())
    estimated_minutes = word_count / 150
    estimated_time = f"{estimated_minutes:.2f} minutos"

    topics_pattern = r"Principais tópicos abordados:\s*(.*)"
    match = re.search(topics_pattern, script_text, re.DOTALL | re.IGNORECASE)
    topics = "Não foi possível extrair os tópicos do roteiro."
    script_text_for_audio = script_text

    if match:
        topics = match.group(1).strip()
        script_text_for_audio = script_text.replace(match.group(0), "").strip()
    else:
        print("Aviso: A seção 'Principais tópicos abordados' não foi encontrada no roteiro. "
              "O script completo será usado para a geração de áudio.")

    print(f"  Número de Participantes: {num_participants}")
    print(f"  Nomes dos Participantes: {presenter_names}")
    print(f"  Tempo Estimado: {estimated_time}")
    print(f"  Tópicos Abordados:\n{topics}")

    return script_text_for_audio, {
        "num_participants": num_participants,
        "presenter_names": presenter_names,
        "estimated_time": estimated_time,
        "topics": topics
    }

def generate_podcast_from_pdf(pdf_bytes: bytes):
    """
    Função principal que orquestra todo o processo de geração do podcast,
    recebendo os bytes do PDF diretamente.
    """
    print("Iniciando o processo de geração de podcast a partir do PDF...")

    # 1. Análise do PDF e Extração de Conteúdo (Texto e Imagens)
    print("\n--- Etapa 1: Análise e Extração de Conteúdo do PDF ---")
    text_content, image_data = extract_content_from_pdf(pdf_bytes)
    if not text_content and not image_data:
        print("Não foi possível extrair nenhum conteúdo (texto ou imagem) do PDF.")
        return None, "Não foi possível extrair nenhum conteúdo do PDF."

    # Upload das imagens para o Gemini File API
    uploaded_image_files = []
    if image_data:
        uploaded_image_files = upload_images_to_gemini(image_data)
        if not uploaded_image_files and image_data:
            print("Aviso: Nenhuma imagem foi enviada com sucesso para o Gemini. O roteiro será gerado apenas com base no texto.")

    # 2. Criação do Roteiro com IA (Gemini)
    print("\n--- Etapa 2: Criação do Roteiro do Podcast com IA ---")
    podcast_script = generate_podcast_script(text_content, uploaded_image_files, PRESENTER_1_NAME, PRESENTER_2_NAME, TARGET_PODCAST_DURATION_MINUTES)
    if not podcast_script:
        print("Não foi possível gerar o roteiro do podcast.")
        if uploaded_image_files:
            delete_uploaded_gemini_files(uploaded_image_files)
        return None, "Não foi possível gerar o roteiro do podcast."

    # 3. Métricas do Podcast
    print("\n--- Etapa 3: Cálculo de Métricas do Podcast ---")
    script_for_audio, metrics = calculate_podcast_metrics(podcast_script, PRESENTER_1_NAME, PRESENTER_2_NAME)

    # 4. Geração de Áudio para o Podcast (pyttsx3)
    print("\n--- Etapa 4: Geração dos Arquivos de Áudio ---")
    audio_segments = generate_audio_segments(script_for_audio, PRESENTER_1_NAME, PRESENTER_2_NAME, MALE_VOICE_ID, FEMALE_VOICE_ID)

    # Limpeza: Deleta os arquivos enviados para o Gemini File API
    if uploaded_image_files:
        delete_uploaded_gemini_files(uploaded_image_files)

    if not audio_segments:
        print("Ocorreu uma falha na geração dos arquivos de áudio do podcast.")
        return None, "Ocorreu uma falha na geração dos arquivos de áudio do podcast."
    
    print("\nProcesso de geração de podcast concluído!")
    return audio_segments, metrics
