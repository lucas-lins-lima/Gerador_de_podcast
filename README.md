# 🎙️ PodGenius

Este projeto ambicioso visa transformar documentos PDF em podcasts dinâmicos e envolventes, utilizando o poder da Inteligência Artificial. A ideia é proporcionar uma forma inovadora de consumir conteúdo acadêmico ou informativo, otimizando o tempo e a acessibilidade através da conversão de texto e imagens em áudio com vozes distintas para diferentes apresentadores.

## ✨ Funcionalidades Atuais

* **Extração de Conteúdo de PDF:** Capacidade de extrair texto e imagens de arquivos PDF.

* **Interação com Gemini API:** Utiliza o modelo Gemini para gerar roteiros de podcast inteligentes e contextuais.

* **Geração de Áudio Offline:** Converte o roteiro gerado em segmentos de áudio WAV usando vozes de Text-to-Speech (TTS) do sistema operacional (via `pyttsx3`), com distinção entre vozes masculinas e femininas.

* **Arquitetura Separada (Backend/Frontend):** O projeto está estruturado para ter um backend robusto em Python (FastAPI) e um frontend interativo em React.js, permitindo um desenvolvimento full-stack e escalável.

* **Ambiente de Desenvolvimento em Nuvem (Codespaces):** Configurado para facilitar o setup e a colaboração através do GitHub Codespaces.

## 🚀 Tecnologias Utilizadas

Este projeto é construído com uma arquitetura full-stack, separando o backend (lógica de servidor) do frontend (interface do usuário).

### Backend (Python)

* **Python 3.x**: Linguagem principal para a lógica de negócio.

* **FastAPI**: Framework web moderno e de alta performance para construir a API REST.

* **PyMuPDF (`fitz`)**: Para extração eficiente de texto e imagens de PDFs.

* **Google Generative AI SDK (`google-generativeai`)**: Para interação com a API do Gemini (geração de roteiros).

* **`pyttsx3`**: Biblioteca para Text-to-Speech offline, utilizando as vozes instaladas no sistema operacional.

* **`python-dotenv`**: Para gerenciar variáveis de ambiente de forma segura.

* **Uvicorn**: Servidor ASGI para rodar a aplicação FastAPI.

### Frontend (React.js)

* **React.js**: Biblioteca JavaScript para construir interfaces de usuário interativas e componentes reutilizáveis.

* **Vite**: Ferramenta de build rápida e moderna para configurar o ambiente de desenvolvimento React.

* **Tailwind CSS**: Framework CSS utilitário para estilização rápida, responsiva e altamente personalizável.

* **Axios / Fetch API (futuro)**: Para fazer requisições HTTP ao backend.

## 📁 Estrutura de Pastas

A organização do projeto segue uma estrutura modular para separar as preocupações do backend e do frontend, além de incluir documentação e configurações de ambiente.
```
Gerador_de_podcast/
├── .devcontainer/              # Configurações para GitHub Codespaces (ambiente de desenvolvimento em nuvem)
│   └── devcontainer.json       # Define como o Codespace deve ser construído e configurado
├── backend/                    # Contém todo o código e configurações do servidor Python
│   ├── src/                    # Código fonte do backend
│   │   ├── main.py             # Ponto de entrada da API FastAPI
│   │   └── podcast_generator.py # Lógica principal de geração de podcast (extração, Gemini, TTS)
│   ├── requirements.txt        # Lista de dependências Python (pip)
│   └── .env.example            # Exemplo de variáveis de ambiente para o backend
├── frontend/                   # Contém todo o código e configurações da interface web (React)
│   ├── public/                 # Arquivos estáticos (como index.html)
│   ├── src/                    # Código fonte do frontend
│   │   ├── App.jsx             # Componente principal da aplicação React
│   │   ├── components/         # (Futuro) Pasta para componentes React reutilizáveis
│   │   ├── pages/              # (Futuro) Pasta para páginas específicas da aplicação
│   │   ├── styles/             # (Futuro) Pasta para arquivos CSS personalizados
│   │   └── main.jsx            # Ponto de entrada do React (renderiza App.jsx)
│   ├── package.json            # Lista de dependências Node.js/React (npm)
│   ├── postcss.config.js       # Configuração do PostCSS (usado pelo Tailwind)
│   ├── tailwind.config.js      # Configuração do Tailwind CSS
│   └── .env.example            # Exemplo de variáveis de ambiente para o frontend
├── docs/                       # (Futuro) Documentação adicional do projeto
│   ├── API.md                  # (Futuro) Documentação da API
│   └── deployment.md           # (Futuro) Notas de deploy
├── .github/                    # (Futuro) Configurações para GitHub Actions (CI/CD)
│   └── workflows/
├── .gitignore                  # Arquivos e pastas a serem ignorados pelo Git (ex: node_modules, venv, .env)
├── README.md                   # Este arquivo
└── LICENSE                     # Licença do projeto (MIT)
```
## 📝 Descrição dos Arquivos Chave

* **`.devcontainer/devcontainer.json`**:

  * **Função:** Configura o ambiente de desenvolvimento do GitHub Codespaces. Define a imagem base, instalações pós-criação (como ambientes virtuais e dependências), encaminhamento de portas e inicia automaticamente os servidores de backend e frontend.

  * **Importância:** Garante que qualquer pessoa que abra o projeto no Codespaces tenha um ambiente de desenvolvimento idêntico e funcional sem configuração manual complexa.

* **`backend/src/main.py`**:

  * **Função:** É o ponto de entrada da API REST do backend, construída com FastAPI. Define os endpoints (rotas) que o frontend irá consumir, como o endpoint para upload de PDF e geração de podcast.

  * **Importância:** Atua como a interface entre o frontend e a lógica de negócio do Python.

* **`backend/src/podcast_generator.py`**:

  * **Função:** Contém a lógica central do projeto: extração de texto e imagens de PDFs, interação com a API do Gemini para gerar o roteiro, e conversão do roteiro em segmentos de áudio usando `pyttsx3`.

  * **Importância:** Encapsula a inteligência principal do gerador de podcast, separando-a da camada de API.

* **`backend/requirements.txt`**:

  * **Função:** Lista todas as bibliotecas Python necessárias para o backend (ex: `fastapi`, `uvicorn`, `PyMuPDF`, `google-generativeai`, `pyttsx3`).

  * **Importância:** Permite que as dependências sejam instaladas de forma consistente usando `pip install -r requirements.txt`.

* **`frontend/public/index.html`**:

  * **Função:** É o arquivo HTML base que o navegador carrega. Ele contém um `div` com `id="root"`, onde toda a aplicação React será "injetada".

  * **Importância:** O ponto de entrada visual da aplicação.

* **`frontend/src/main.jsx`**:

  * **Função:** O ponto de entrada JavaScript/React da aplicação frontend. Ele inicializa o React e renderiza o componente `App.jsx` no `index.html`.

  * **Importância:** Conecta a lógica React com o HTML da página.

* **`frontend/src/App.jsx`**:

  * **Função:** O componente React principal que define a estrutura inicial da interface do usuário, incluindo o título e o botão "Carregar PDF", já estilizado com Tailwind CSS.

  * **Importância:** O primeiro componente visual que o usuário vê e interage.

* **`frontend/package.json`**:

  * **Função:** Define as informações do projeto frontend, suas dependências (React, Vite, Tailwind CSS, etc.) e os scripts para desenvolvimento (`npm run dev`) e build (`npm run build`).

  * **Importância:** Gerencia as dependências JavaScript/Node.js e os comandos de desenvolvimento do frontend.

## 👣 Histórico de Desenvolvimento e Próximos Passos

Este projeto está em fase inicial de desenvolvimento, com o objetivo de construir uma aplicação full-stack funcional.

### Passos Concluídos (até 23/05/2025)

1. **Concepção da Ideia:** Definição do objetivo de transformar PDFs em podcasts.

2. **Desenvolvimento do Core Python:** Criação do script inicial em Python para extração de PDF, interação com Gemini e geração de áudio com `pyttsx3`.

3. **Estruturação do Projeto:** Definição da estrutura de pastas para backend, frontend e arquivos de configuração.

4. **Refatoração do Backend para FastAPI:** Adaptação do código Python para funcionar como uma API RESTful usando FastAPI, com separação de lógica em `podcast_generator.py` e `main.py`.

5. **Configuração de Variáveis de Ambiente:** Implementação do uso de arquivos `.env` para gerenciar chaves de API e outras configurações sensíveis.

6. **Configuração Inicial do Frontend (React + Vite + Tailwind CSS):** Criação dos arquivos essenciais (`package.json`, `index.html`, `main.jsx`, `App.jsx`, `tailwind.config.js`, `postcss.config.js`) para uma interface web moderna e responsiva.

7. **Configuração do GitHub Codespaces:** Criação e ajuste do arquivo `.devcontainer/devcontainer.json` para automatizar a configuração do ambiente de desenvolvimento em nuvem, incluindo a instalação de dependências e o início automático dos servidores de backend e frontend.

8. **Depuração Inicial:** Resolução de problemas de instalação de dependências e execução de servidores no ambiente WSL e Codespaces.

### Próximos Passos (A Fazer)

1. **Desenvolvimento da Interface de Upload no Frontend:**

   * Criar um formulário no React para o usuário fazer o upload do arquivo PDF.

   * Implementar a lógica para enviar o arquivo PDF para o endpoint `/generate-podcast/` do backend.

   * Adicionar indicadores de carregamento e mensagens de feedback para o usuário.

2. **Manipulação da Resposta do Backend no Frontend:**

   * Receber o arquivo ZIP com os segmentos de áudio do backend.

   * Implementar a funcionalidade de download do podcast gerado.

   * (Opcional) Explorar a combinação dos segmentos de áudio no frontend ou no backend para um único arquivo MP3.

3. **Melhorias na Experiência do Usuário (UX):**

   * Adicionar histórico de podcasts gerados.

   * Permitir a personalização de vozes ou estilos de podcast.

   * Melhorar a estilização e a responsividade da interface.

4. **Tratamento de Erros:**

   * Implementar tratamento de erros mais robusto no frontend para lidar com falhas na API ou no processamento.

5. **Testes:**

   * Escrever testes unitários e de integração para o backend e frontend.

6. **Deploy:**

   * Configurar o deploy da aplicação para um serviço de hospedagem (ex: Heroku, Google Cloud Run, Vercel para frontend, etc.).

### Histórico de Commits

Até o momento (23/05/2025), a maioria das alterações e configurações iniciais foram consolidadas em um único ou poucos commits, focando na estruturação e no setup do ambiente. O histórico de commits será mais detalhado à medida que novas funcionalidades forem implementadas.

## 🤝 Contribuição

Contribuições são muito bem-vindas! Se você tiver ideias para melhorias, encontrar bugs ou quiser adicionar novas funcionalidades, sinta-se à vontade para:

1. Fazer um fork do projeto.

2. Criar uma nova branch (`git checkout -b feature/minha-nova-funcionalidade`).

3. Realizar suas alterações e commitar (`git commit -m 'feat: adiciona nova funcionalidade X'`).

4. Fazer push para a branch (`git push origin feature/minha-nova-funcionalidade`).

5. Abrir um Pull Request, descrevendo suas alterações.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📞 Contato

Lucas Lins Lima - [https://www.linkedin.com/in/lucas-lins-lima/]
