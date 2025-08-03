SaudMed Analytics
Dashboard interativo desenvolvido com Streamlit para análise de dados de vendas, estoque e compras da SaudMed. Este projeto visa fornecer insights valiosos para otimização de processos e tomada de decisões estratégicas.

📊 Funcionalidades Principais
Análise de Vendas: Visualização de dados de vendas, tendências e desempenho.

Gestão de Estoque: Monitoramento de entradas e saídas de produtos.

Controle de Compras: Ferramentas para auxiliar no processo de compras e anotações de itens em falta.

Relatórios Dinâmicos: Geração de relatórios filtrados e exportáveis em formato XLSX.

🚀 Como Rodar o Projeto
Siga os passos abaixo para configurar e executar o dashboard em sua máquina.

Pré-requisitos
Certifique-se de ter o Python 3.8 ou superior instalado em seu sistema.

Download Python: Visite o site oficial do Python: python.org

Instalação no Windows: Durante a instalação, é crucial marcar a opção "Add Python to PATH" (Adicionar Python ao PATH) para que o Python e o pip (gerenciador de pacotes) sejam reconhecidos no terminal.

📦 Instalação das Dependências
Navegue até a pasta do projeto:
Abra o seu terminal (Prompt de Comando no Windows, Terminal no macOS/Linux) e use o comando cd (change directory) para ir até a pasta onde você salvou os arquivos do projeto.

cd caminho\para\SuaPastaDoProjeto\saudmed_analytics
# Exemplo no Windows: cd C:\Users\SeuUsuario\Desktop\Cássio\saudmed_analytics

Instale as bibliotecas necessárias:
Com o terminal na pasta do projeto, execute o seguinte comando para instalar todas as dependências listadas no arquivo requirements.txt:

pip install -r requirements.txt

▶️ Executando o Dashboard
Após a instalação das dependências, você pode iniciar o aplicativo Streamlit:

Certifique-se de estar na pasta raiz do projeto no terminal.

Execute o comando:

streamlit run pagina_principal.py

Se o comando acima não funcionar diretamente, você pode tentar com o módulo Python:

python -m streamlit run pagina_principal.py

Observação: O comando que você forneceu (cd /d "C:\Users\Saudmed Terminal\Desktop\Cássio\saudmed_analytics\" && python -m streamlit run pagina_principal.py) é útil para executar diretamente de um script ou atalho, pois ele primeiro navega até a pasta e depois executa o Streamlit.

Acesso ao Dashboard:
Após executar o comando, o Streamlit abrirá automaticamente o dashboard em seu navegador padrão (geralmente em http://localhost:8501).

📁 Estrutura do Projeto
pagina_principal.py: O arquivo principal da aplicação Streamlit, onde o dashboard é construído.

database.py: Módulo responsável pela interação com o banco de dados Firebird.

utils.py: Contém funções utilitárias para formatação, processamento de dados e outras operações auxiliares.

constants.py: Define constantes e variáveis globais utilizadas em todo o projeto.

requirements.txt: Lista todas as dependências Python necessárias para o projeto.

anotacoes_compras.txt: Arquivo de texto para anotações específicas da aba de compras.

ajuste.txt: (Descrever a finalidade deste arquivo, se houver)

saudmed_logo.jpg: Logo da SaudMed utilizada no dashboard.

🤝 Contribuição
Contribuições são bem-vindas! Se você tiver sugestões, melhorias ou encontrar algum problema, sinta-se à vontade para:

Me mandar um pix para 07191419903

📄 Licença
Este projeto é desenvolvido para uso interno da SaudMed.

📧 Contato
Desenvolvido por Cássio Cândido Ribeiro (LinkedIn).

CassioCandidoRibeiro@gmail.com