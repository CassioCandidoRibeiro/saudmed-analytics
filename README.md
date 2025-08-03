# README
# Este arquivo contém o conteúdo do README.TXT para o projeto SaudMed Analytics.

## SaudMed Analytics

Este repositório contém o código-fonte da aplicação **SaudMed Analytics**, um dashboard interativo desenvolvido com Streamlit para análises de dados relacionados a vendas, estoque e compras. O objetivo é centralizar e apresentar informações cruciais para a tomada de decisão no negócio.

### Funcionalidades Principais

* **Análise de Compras:**
    * **Brasil:** Recomendação de compra de produtos com base em vendas e estoque atual, cálculo de custo previsto e informações detalhadas de produtos.
    * **Paraguai:** Análise de dados de vendas e custos a partir de um arquivo "Informes.xls".
    * **Geral (BR + PY):** Visão consolidada das operações.
    * **Geral Sem Stanley:** Filtro para análises excluindo um cliente específico (Stanley).
* **Análise de Produtos Controlados:** Gerenciamento e visualização de produtos sujeitos a controle especial.
* **Gestão de Clientes:** Acompanhamento de clientes e histórico de compras.
* **Orçamento:** Funcionalidades relacionadas a orçamentos.
* **Ligeirinho:** Seção dedicada a operações rápidas ou específicas.
* **Produtos:** Visão geral e detalhe de produtos.
* **InfoServe:** Análise de dados provenientes do sistema InfoServe.
* **Filtros Dinâmicos:** Permite filtrar dados por período, marca, produto e categoria.
* **Download de Relatórios:** Possibilidade de exportar os dados exibidos em formato Excel.

### Tecnologias Utilizadas

O projeto é construído com as seguintes tecnologias:

* **Streamlit:** Framework principal para criação do dashboard interativo.
* **Pandas:** Biblioteca essencial para manipulação e análise de dados tabulares (DataFrames).
* **NumPy:** Biblioteca para computação numérica de alto desempenho.
* **FDB (Python Firebird Driver):** Driver para conexão com o banco de dados Firebird.
* **XlsxWriter:** Ferramenta para criação de arquivos Excel (.xlsx), utilizada para exportação de dados.

### Estrutura do Projeto

* `pagina_principal.py`:
    * Arquivo principal da aplicação Streamlit.
    * Configura a página, gerencia o estado da sessão, define a barra lateral com filtros (data, marca, produto, categoria, upload de arquivo "Informes").
    * Organiza o dashboard em abas (`COMPRAS`, `CONTROLADOS`, `CLIENTES`, `ORÇAMENTO`, `LIGEIRINHO`, `PRODUTOS`, `INFOSERVE`).
    * Exibe métricas e tabelas de dados formatadas, e botões de download.
* `constants.py`:
    * Módulo que centraliza todas as constantes utilizadas na aplicação.
    * Inclui fatores de negócio (ex: `FATOR_REPOSICAO_ESTOQUE`, `FATOR_CUSTO_REVERSO_IMPOSTO`), códigos para consultas SQL (ex: `CODIGO_FILIAL_LOJA`, `CFOP_VENDAS_ESTADUAIS`), e nomes padronizados para colunas de DataFrame.
* `database.py`:
    * Módulo responsável pela interação com o banco de dados Firebird.
    * Contém a função `get_db_connection()` para estabelecer e cachear a conexão com o banco de dados, utilizando credenciais seguras do Streamlit (`st.secrets`).
    * Inclui a função auxiliar `_execute_query` para execução segura de queries SQL e tratamento básico de dados.
    * Define funções específicas para carregamento de dados para cada seção do dashboard (ex: `load_marcas()`, `load_categorias()`, `load_compras_brasil_data()`).
* `utils.py`:
    * Módulo com funções utilitárias gerais.
    * Funções de formatação de valores (moeda, percentual, inteiro).
    * Funções de cálculo de negócio (ex: `calcular_recomendacao`, `calcular_custo_reverso`).
    * Funções para manipulação de DataFrames e exportação para Excel.
    * Função `ler_informes_excel` para processar o arquivo "Informes.xls".
* `requirements.txt`:
    * Lista todas as dependências do projeto com suas versões específicas para garantir a reprodutibilidade do ambiente.
* `Arquivo bat pra rodar o código.bat`:
    * Um script simples para iniciar a aplicação Streamlit via linha de comando. Contém o comando `python -m streamlit run pagina_principal.py`.

### Como Configurar e Rodar o Projeto

1.  **Pré-requisitos:**
    * Python 3.x instalado.
    * Acesso a um banco de dados Firebird com as credenciais necessárias.

2.  **Instalação das Dependências:**
    * Navegue até o diretório raiz do projeto no seu terminal.
    * Execute o comando para instalar as bibliotecas listadas no `requirements.txt`:
        ```bash
        pip install -r requirements.txt
        ```

3.  **Configuração do Banco de Dados:**
    * Crie um arquivo `.streamlit/secrets.toml` (se não existir) na raiz do seu projeto.
    * Adicione as credenciais do seu banco de dados Firebird neste arquivo, conforme o exemplo abaixo:
        ```toml
        # .streamlit/secrets.toml
        [db_credentials]
        host = "seu_host_firebird"
        port = 3050 # Ou a porta do seu Firebird
        database = "caminho/para/seu/banco.fdb"
        user = "seu_usuario"
        password = "sua_senha"
        charset = "UTF8" # Opcional, mas recomendado
        ```
    * **Segurança:** Mantenha este arquivo `secrets.toml` seguro e **NÃO** o inclua em repositórios públicos como o GitHub.

4.  **Executar a Aplicação:**
    * Você pode usar o arquivo `.bat` fornecido (se estiver no Windows):
        ```bash
        Arquivo bat pra rodar o código.bat
        ```
    * Ou execute diretamente pelo terminal:
        ```bash
        streamlit run pagina_principal.py
        ```
    * A aplicação será aberta automaticamente no seu navegador padrão.

### Uso

Ao iniciar a aplicação, você verá o dashboard interativo. Utilize a barra lateral para aplicar filtros de data, marca, produto e categoria. Na aba "COMPRAS", você poderá fazer o upload do arquivo "Informes.xls" para habilitar as análises relacionadas ao Paraguai e à visão geral. Navegue pelas diferentes abas para acessar os relatórios e análises específicas.

### Desenvolvedor

Cássio Cândido Ribeiro (2025)

