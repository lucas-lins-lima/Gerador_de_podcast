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

# --- Configuração ---
# Substitua 'YOUR_GEMINI_API_KEY' pela sua chave de API do Gemini.
# Você pode obter uma chave de API em https://aistudio.google.com/app/apikey
# Para o modelo 'gemini-2.0-flash', pode não ser necessário uma chave de API em alguns ambientes,
# mas é uma boa prática tê-la para uso mais robusto e para evitar limites de uso.
# IMPORTANTE: Mantenha sua chave de API segura e não a compartilhe publicamente!
GEMINI_API_KEY = "AIzaSyAJKkS4jclV7FqgG0VAd29CV1P-bD1Bxww" # <--- INSIRA SUA CHAVE DE API AQUI
genai.configure(api_key=GEMINI_API_KEY)

# Nomes dos apresentadores do podcast
PRESENTER_1_NAME = "Apresentador João"
PRESENTER_2_NAME = "Apresentadora Maria"

# IDs das vozes para pyttsx3.
# Estas IDs referem-se às vozes instaladas no seu sistema operacional.
# Para português do Brasil (Windows), as vozes comuns são:
# Microsoft Daniel Desktop - Portuguese(Brazil) para masculino
# Microsoft Maria Desktop - Portuguese(Brazil) para feminino
# Se estas vozes não estiverem instaladas, pyttsx3 usará a voz padrão do sistema.
# Você pode verificar as vozes disponíveis executando o script e olhando a seção "Vozes pyttsx3 disponíveis".
MALE_VOICE_ID = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_PT-BR_DANIEL_11.0" # <--- ID da voz masculina (Português - Brasil)
FEMALE_VOICE_ID = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_PT-BR_MARIA_11.0" # <--- ID da voz feminina (Português - Brasil)

# Nome do diretório de saída para os arquivos de áudio individuais
OUTPUT_AUDIO_DIR = "podcast_audios_separados" # <-- Novo diretório de saída

# Tempo médio desejado para o podcast em minutos.
# O Gemini tentará ajustar o roteiro para esta duração, mas não é uma garantia exata.
TARGET_PODCAST_DURATION_MINUTES = 15 # <--- Defina a duração desejada aqui (em minutos)

# --- Funções ---

def extract_content_from_pdf(pdf_path):
    """
    Extrai texto e imagens de um arquivo PDF usando PyMuPDF (fitz).
    Esta função não requer a instalação do Poppler.
    """
    text_content = ""
    image_data_for_gemini = []

    print(f"Iniciando a extração de conteúdo do PDF: {pdf_path}")
    try:
        # Abre o documento PDF com PyMuPDF
        doc = fitz.open(pdf_path)
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
            print(f"  Arquivo {file.display_name} (URI: {file.uri}) deletado.")
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
                                             "e insights na discussão do podcast, explicando o que ela representa "
                                             "e como se relaciona com o tópico atual.\n")

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

def generate_audio(script_text, output_dir, presenter1_name, presenter2_name, male_voice_id, female_voice_id):
    """
    Gera arquivos de áudio WAV separados para cada fala, usando pyttsx3.
    Distinguir entre vozes masculinas e femininas ajustando as propriedades da voz.
    """
    print(f"Gerando arquivos de áudio WAV individuais com pyttsx3 no diretório: {output_dir}")
    
    # Cria o diretório de saída se ele não existir
    os.makedirs(output_dir, exist_ok=True)

    try:
        engine = pyttsx3.init()
        
        # Auto-detecção de vozes (mantido do código anterior, é útil)
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

        # Atribui os IDs detectados ou mantém os configurados manualmente (se houver)
        if male_voice_id is None and pt_br_male_voice_id:
            male_voice_id = pt_br_male_voice_id
        if female_voice_id is None and pt_br_female_voice_id:
            female_voice_id = pt_br_female_voice_id
        
        # Fallback para vozes genéricas se as específicas não forem encontradas
        if not male_voice_id:
            print("  Aviso: Voz masculina específica não encontrada. Tentando voz masculina genérica.")
            for voice in voices:
                if voice.gender == 'male' or 'male' in voice.name.lower():
                    male_voice_id = voice.id
                    print(f"  Voz masculina genérica auto-detectada: {voice.name}")
                    break
            if not male_voice_id and voices:
                male_voice_id = voices[0].id # Último recurso: primeira voz disponível

        if not female_voice_id:
            print("  Aviso: Voz feminina específica não encontrada. Tentando voz feminina genérica.")
            for voice in voices:
                if voice.gender == 'female' or 'female' in voice.name.lower():
                    female_voice_id = voice.id
                    print(f"  Voz feminina genérica auto-detectada: {voice.name}")
                    break
            if not female_voice_id and voices:
                female_voice_id = voices[1].id if len(voices) > 1 else voices[0].id # Último recurso: segunda ou primeira voz

        if not male_voice_id or not female_voice_id:
            print("Erro: Não foi possível encontrar vozes masculina e/ou feminina adequadas no sistema. A geração de áudio pode não ter distinção de gênero.")
            # Se uma das vozes não foi encontrada, usa a que encontrou ou a primeira padrão
            if male_voice_id:
                engine.setProperty('voice', male_voice_id)
            elif female_voice_id:
                engine.setProperty('voice', female_voice_id)
            else:
                print("Erro: Nenhuma voz de Text-to-Speech utilizável encontrada no sistema. A geração de áudio não pode prosseguir.")
                return False
            # Define a voz padrão para ambas se uma delas estiver faltando
            if not male_voice_id: male_voice_id = female_voice_id
            if not female_voice_id: female_voice_id = male_voice_id

        # Configurações de velocidade e volume para cada apresentador
        # Ajuste esses valores para tentar tornar as vozes mais distintas
        joao_rate = 160  # Palavras por minuto para João (mais lento)
        maria_rate = 190 # Palavras por minuto para Maria (mais rápido)
        joao_volume = 1.0 # Volume normal para João
        maria_volume = 0.9 # Ligeiramente mais baixo para Maria (pode dar a sensação de uma voz diferente)

        lines = script_text.split('\n')
        generated_audio_files = [] # Lista para armazenar os nomes dos arquivos gerados

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
                # Para introduções, conclusões ou outros textos não atribuídos, usa a voz masculina como padrão
                current_voice_id = male_voice_id 
                current_rate = joao_rate 
                current_volume = joao_volume

            if text_to_synthesize and current_voice_id:
                engine.setProperty('voice', current_voice_id)
                engine.setProperty('rate', current_rate)
                engine.setProperty('volume', current_volume)
                
                # Nome do arquivo para este segmento
                segment_filename = os.path.join(output_dir, f"segment_{i:03d}.wav")
                
                engine.save_to_file(text_to_synthesize, segment_filename)
                engine.runAndWait() # Processa e salva a fala atual
                generated_audio_files.append(segment_filename)
                print(f"  Gerado: {segment_filename}")
                
                # Adiciona um pequeno atraso entre as falas para simular uma pausa natural
                time.sleep(0.5) # 0.5 segundos de pausa

        if not generated_audio_files:
            print("Erro: Nenhum arquivo de áudio foi gerado com sucesso. Verifique o roteiro e as vozes.")
            return False

        print(f"Todos os segmentos de áudio foram gerados com sucesso no diretório '{output_dir}'.")
        print("Para criar um único arquivo de podcast, você precisará combinar esses arquivos manualmente usando um software de edição de áudio (ex: Audacity).")
        return True
    except Exception as e:
        print(f"Erro ao gerar o áudio com pyttsx3: {e}.")
        print("Verifique se as vozes de Text-to-Speech estão instaladas no seu sistema,")
        print("e se pyttsx3 está instalado.")
        return False


def calculate_podcast_metrics(script_text, presenter1, presenter2):
    """
    Calcula e exibe métricas relevantes para o podcast, como número de participantes,
    nomes e tempo estimado. Também tenta extrair os tópicos abordados do roteiro.
    """
    print("\n--- Métricas do Podcast ---")
    num_participants = 2
    presenter_names = f"{presenter1}, {presenter2}"

    # Estima o tempo de duração do podcast baseado na contagem de palavras do roteiro.
    # Uma média de 150 palavras por minuto é frequentemente usada para estimar o tempo de fala.
    word_count = len(script_text.split())
    estimated_minutes = word_count / 150
    estimated_time = f"{estimated_minutes:.2f} minutos"

    # Tenta extrair a seção de "Principais tópicos abordados" do final do script.
    # Usamos uma expressão regular para encontrar essa seção, que foi instruída ao Gemini.
    topics_pattern = r"Principais tópicos abordados:\s*(.*)"
    match = re.search(topics_pattern, script_text, re.DOTALL | re.IGNORECASE)
    topics = "Não foi possível extrair os tópicos do roteiro."
    script_text_for_audio = script_text # Por padrão, usa o script completo para o áudio.

    if match:
        topics = match.group(1).strip()
        # Remove a seção de tópicos do script principal para que ela não seja lida no áudio.
        script_text_for_audio = script_text.replace(match.group(0), "").strip()
    else:
        print("Aviso: A seção 'Principais tópicos abordados' não foi encontrada no roteiro. "
              "O script completo será usado para a geração de áudio.")

    print(f"  Número de Participantes: {num_participants}")
    print(f"  Nomes dos Participantes: {presenter_names}")
    print(f"  Tempo Estimado: {estimated_time}")
    print(f"  Tópicos Abordados:\n{topics}")

    # Retorna o script sem a seção de tópicos para ser usado na geração de áudio.
    return script_text_for_audio

# --- Função Principal (Main) ---

def main():
    """
    Função principal que orquestra todo o processo de geração do podcast.
    """
    # Mostra o diretório de trabalho atual para ajudar na depuração de caminhos.
    current_directory = os.getcwd()
    print(f"Diretório de trabalho atual: {current_directory}")

    print("\n--- Configuração de Vozes ---")
    print("Esta versão utiliza as vozes de Text-to-Speech (TTS) instaladas no seu sistema operacional (via pyttsx3).")
    print("A qualidade e a naturalidade das vozes dependem diretamente das vozes que o seu sistema possui.")
    print("A distinção entre as vozes de João e Maria é feita ajustando a velocidade e o volume para cada um.")
    print("\nPara verificar as vozes disponíveis no seu sistema e escolher as melhores opções:")
    try:
        engine_test = pyttsx3.init()
        voices_test = engine_test.getProperty('voices')
        if not voices_test:
            print("Nenhuma voz de Text-to-Speech encontrada. A geração de áudio pode falhar.")
        for i, voice in enumerate(voices_test):
            print(f"  {i+1}. ID: {voice.id}")
            print(f"     Nome: {voice.name}")
            print(f"     Idiomas: {voice.languages}")
            print(f"     Gênero: {'Masculino' if voice.gender == 'male' else ('Feminino' if voice.gender == 'female' else 'Desconhecido')}")
            print(f"     Idade: {voice.age}")
            print("-" * 30)
        print("Por favor, copie os IDs das vozes masculina e feminina desejadas e cole nas variáveis MALE_VOICE_ID e FEMALE_VOICE_ID na seção de CONFIGURAÇÃO do script.")
        print("Para português do Brasil, procure por vozes como 'Microsoft Daniel Desktop - Portuguese(Brazil)' e 'Microsoft Maria Desktop - Portuguese(Brazil)'.")
        print("Isso garantirá que ambas as vozes falem português do Brasil (se instaladas e disponíveis no seu sistema).")
    except Exception as e:
        print(f"Erro ao listar vozes pyttsx3: {e}. Certifique-se de que pyttsx3 está instalado e configurado corretamente.")
    print("-" * 40)
    input("\nPressione Enter para continuar após revisar as vozes e configurar os IDs no script (se necessário)...")


    global PDF_PATH # Declara PDF_PATH como global para ser acessível e modificável

    # Loop para permitir retentativas de encontrar o PDF
    while True: 
        # Lista todos os arquivos PDF na pasta atual
        pdf_files = [f for f in os.listdir(current_directory) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print("\nNenhum arquivo PDF encontrado no diretório atual.")
            pdf_path_input = input("Por favor, digite o caminho COMPLETO para o seu arquivo PDF (ex: C:\\Users\\SeuUsuario\\Documentos\\F01CAP01.pdf ou D:/MeusDocumentos/F01CAP01.pdf): ")
            PDF_PATH = pdf_path_input.replace('\\', '/')
        else:
            print("\nArquivos PDF encontrados no diretório atual:")
            for i, pdf_file in enumerate(pdf_files):
                print(f"  {i+1}. {pdf_file}")
            
            # Loop para garantir uma escolha válida do usuário
            while True: 
                try:
                    choice = input(f"Digite o NÚMERO do PDF que deseja usar (1-{len(pdf_files)}) ou '0' para digitar o caminho completo: ")
                    choice_int = int(choice)

                    if choice_int == 0:
                        pdf_path_input = input("Por favor, digite o caminho COMPLETO para o seu arquivo PDF: ")
                        PDF_PATH = pdf_path_input.replace('\\', '/')
                        break
                    elif 1 <= choice_int <= len(pdf_files):
                        PDF_PATH = os.path.join(current_directory, pdf_files[choice_int - 1])
                        PDF_PATH = PDF_PATH.replace('\\', '/') # Normaliza o caminho
                        print(f"Você selecionou: {pdf_files[choice_int - 1]}")
                        break
                    else:
                        print("Escolha inválida. Por favor, digite um número da lista ou '0'.")
                except ValueError:
                    print("Entrada inválida. Por favor, digite um número.")
        
        # Verifica se o arquivo PDF especificado existe.
        if os.path.exists(PDF_PATH):
            break # Sai do loop principal se o arquivo for encontrado
        else:
            print(f"\nErro: O arquivo PDF '{PDF_PATH}' não foi encontrado ou está inacessível.")
            print("Isso pode acontecer se o arquivo estiver em um drive externo que foi desconectado ou entrou em modo de suspensão.")
            retry_choice = input("Por favor, verifique a conexão do seu drive externo e o caminho do arquivo. Deseja tentar novamente? (s/n): ").lower()
            if retry_choice != 's':
                print("Encerrando o processo.")
                return # Sai da função main se o usuário não quiser tentar novamente

    # 1. Análise do PDF e Extração de Conteúdo (Texto e Imagens)
    print("\n--- Etapa 1: Análise e Extração de Conteúdo do PDF ---")
    text_content, image_data = extract_content_from_pdf(PDF_PATH)
    if not text_content and not image_data:
        print("Não foi possível extrair nenhum conteúdo (texto ou imagem) do PDF. Encerrando o processo.")
        return

    # Upload das imagens para o Gemini File API
    uploaded_image_files = []
    if image_data:
        uploaded_image_files = upload_images_to_gemini(image_data)
        if not uploaded_image_files and image_data: # Verifica se havia dados de imagem mas nada foi enviado
            print("Aviso: Nenhuma imagem foi enviada com sucesso para o Gemini. O roteiro será gerado apenas com base no texto.")

    # 2. Criação do Roteiro com IA (Gemini)
    print("\n--- Etapa 2: Criação do Roteiro do Podcast com IA ---")
    # Passamos as referências dos arquivos enviados para a função de geração do roteiro
    podcast_script = generate_podcast_script(text_content, uploaded_image_files, PRESENTER_1_NAME, PRESENTER_2_NAME, TARGET_PODCAST_DURATION_MINUTES)
    if not podcast_script:
        print("Não foi possível gerar o roteiro do podcast. Encerrando o processo.")
        # Garante que os arquivos enviados sejam deletados mesmo em caso de falha na geração do roteiro
        if uploaded_image_files:
            delete_uploaded_gemini_files(uploaded_image_files)
        return

    # Opcional: Salvar o roteiro gerado em um arquivo de texto para revisão.
    script_output_filename = "roteiro_podcast.txt"
    with open(script_output_filename, "w", encoding="utf-8") as f:
        f.write(podcast_script)
    print(f"Roteiro completo salvo em '{script_output_filename}' para sua revisão.")


    # 4. Métricas do Podcast
    print("\n--- Etapa 4: Cálculo de Métricas do Podcast ---")
    # A função de métricas também retorna o script limpo (sem a seção de tópicos) para o áudio.
    script_for_audio = calculate_podcast_metrics(podcast_script, PRESENTER_1_NAME, PRESENTER_2_NAME)

    # 3. Geração de Áudio para o Podcast (pyttsx3)
    print("\n--- Etapa 3: Geração dos Arquivos de Áudio ---")
    # male_voice_id e female_voice_id são passados para a função generate_audio
    audio_generated = generate_audio(script_for_audio, OUTPUT_AUDIO_DIR, PRESENTER_1_NAME, PRESENTER_2_NAME, MALE_VOICE_ID, FEMALE_VOICE_ID)

    if audio_generated:
        print(f"\nProcesso concluído! Os arquivos de áudio individuais foram gerados com sucesso no diretório '{OUTPUT_AUDIO_DIR}'")
        print("Para ter um único arquivo de podcast, você precisará combinar esses arquivos manualmente usando um software de edição de áudio (ex: Audacity, que é gratuito).")
    else:
        print("\nOcorreu uma falha na geração dos arquivos de áudio do podcast.")
    
    # Limpeza: Deleta os arquivos enviados para o Gemini File API
    if uploaded_image_files:
        delete_uploaded_gemini_files(uploaded_image_files)

# Garante que a função 'main' seja executada apenas quando o script for iniciado diretamente.
if __name__ == "__main__":
    # Instruções de instalação das bibliotecas Python:
    print("---------------------------------------------------------------------------------------")
    print("INSTALAÇÃO DE DEPENDÊNCIAS:")
    print("Por favor, certifique-se de ter as seguintes bibliotecas Python instaladas.")
    print("Você pode instalá-las usando pip no seu terminal ou VS Code:")
    print("pip install PyMuPDF Pillow google-generativeai pyttsx3") 
    print("\nEsta versão do script NÃO requer a instalação do Poppler ou FFmpeg.")
    print("\n---------------------------------------------------------------------------------------")
    print("SOBRE A QUALIDADE E DISTINÇÃO DE VOZES:")
    print("Esta versão utiliza 'pyttsx3' para geração de áudio, que é gratuita e offline.")
    print("A qualidade e a naturalidade das vozes dependem **inteiramente das vozes de Text-to-Speech**")
    print("instaladas no seu sistema operacional (ex: vozes da Microsoft no Windows).")
    print("Se as vozes do seu sistema soam 'robotizadas', o pyttsx3 não pode melhorar isso diretamente.")
    print("A distinção entre as vozes de João e Maria é simulada através de:")
    print("  1. Seleção de vozes diferentes do seu sistema (se disponíveis, como Daniel e Maria para PT-BR).")
    print("  2. Pequenas variações na **velocidade** e no **volume** da fala para cada personagem.")
    print("\nIMPORTANTE: Este script gerará **múltiplos arquivos WAV**, um para cada fala.")
    print("Para criar um único arquivo de podcast, você precisará combiná-los manualmente")
    print("usando um software de edição de áudio externo (ex: Audacity, que é gratuito).")
    print("---------------------------------------------------------------------------------------")
    input("\nPressione Enter para continuar após instalar as dependências...")
    main()