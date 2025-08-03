# constants.py
# Módulo para centralizar constantes utilizadas na aplicação SaudMed Analytics.



######################################################################################



from typing import Tuple, List



######################################################################################



# --- Fatores de Negócio ---
FATOR_REPOSICAO_ESTOQUE: float = 1.1
FATOR_CUSTO_REVERSO_IMPOSTO: float = 1.14



######################################################################################



# --- Constantes em consulta SQL no Filtro WHERE 
CODIGO_FILIAL_LOJA: int = 1
CODIGO_GRUPO_CONTROLADOS: int = 2
# CFOPs indicam operações fiscais (Vendas Estaduais neste caso)
CFOP_VENDAS_ESTADUAIS: Tuple[int, ...] = (5102, 5405, 6102, 6108, 6403)
MODO_VENDA_CONCLUIDA: str = 'O'  # Estoque movimentado
MODO_VENDA_NAO_REMOVIDO: str = 'R' # Usado para filtrar itens não removidos (<> 'R')
STATUS_VENDA_EFETIVADA: str = 'Efetivada'
VENDA_FATURADA_SIM: str = 'S'
MERCADORIA_ATIVA: str = 'S'
NATUREZA_OPERACAO_VENDA: str = 'Venda'
NATUREZAS_OPERACAO_VENDA_REMESSA: Tuple[str, ...] = ('Venda', 'Remessa de Saída')
CODIGO_CAMPO_PERSONALIZADO_FRETE: int = 13 # ID do campo personalizado para valor do frete
FILTRO_NOME_FANTASIA_STANLEY: str = 'STANLEY%HAIR%' # Padrão LIKE para cliente Stanley



######################################################################################



# Colunas mais comuns
COL_MARCA: str = "Marca"
COL_CATEGORIA: str = "Categoria"
COL_CODIGO_BR: str = "Código BR"
COL_CODIGO_PY: str = "Cod PY"
COL_PRODUTO: str = "Produto"
COL_CUSTO_UNITARIO: str = "Custo Unitário" # Custo calculado (reverso ou direto do DB)
COL_FORNECEDOR: str = "Último Fornecedor"
COL_ULTIMA_ENTRADA: str = "Última Entrada"
COL_UNIDADE: str = "Unidade"
COL_ESTOQUE: str = "Estoque" # Genérico, especificar BR/PY quando possível
COL_CUSTO_PREVISTO: str = "Custo Previsto"
COL_TEXTO: str = "Texto" # Para mensagens/descrições
COL_DATA: str = "Data"
COL_VENDEDOR: str = "Vendedor"
COL_CLIENTE: str = "Cliente"
COL_VENDA: str = "Venda" # Código da venda
COL_CODIGO: str = "Código" # Código genérico (produto)
COL_QUANTIDADE: str = "Quantidade" # Quantidade formatada/final
COL_NF: str = "NF" # Número da NF (Stanley Vendas)
COL_NFE: str = "NFe" # Número da NFe (Controlados)



######################################################################################



# Compras Brasil Específico
COL_PRODUTOS_VENDIDOS: str = "Produtos Vendidos"
COL_QTD_VENDAS: str = "Qtd de Vendas"
COL_ESTOQUE_BR: str = "Estoque BR"
COL_RECOMENDACAO_BR: str = "Recomendação BR" # Nome no backup para recomendação BR



######################################################################################



# Compras Paraguai Específico (Após Renomeação Posicional do backup)
COL_PRODUTO_PY: str = "Produto" # Nome no backup após rename
COL_MARCA_PY: str = "Marca" # Nome no backup após rename
COL_VENDAS_PY: str = "Vendas PY"
COL_ESTOQUE_PY: str = "Estoque PY"
COL_RECOMENDACAO_PY: str = "Recomendação PY"



######################################################################################



# Compras Geral (Merge) - Nomes conforme backup
COL_CUSTO_GERAL: str = "Custo" # Custo unitário na aba geral
COL_VENDAS_BR: str = "Vendas BR" # Vendas BR agrupadas para merge
COL_TEM_P_PY: str = "Tem p/ PY?"
COL_QUANTO_COMPRAR: str = "Quanto comprar?"
COL_COMPRAR_TEXTO: str = "Comprar" # Texto formatado
COL_SEPARAR_P_PY: str = "Separar p/ PY" # Texto formatado



######################################################################################



# Controlados Específico
COL_NOME_MEDICAMENTO: str = "Nome do Medicamento"
COL_QTD_VENDIDA: str = "Quantidade Vendida" # Formatada com unidade
COL_LOTE: str = "Lote"
COL_ENDERECO: str = "Endereço"
COL_CNPJ: str = "CNPJ"
COL_CPF: str = "CPF"
COL_DOC: str = "DOC"



######################################################################################



# Stanley Vendas Específico
COL_CIDADE: str = "Cidade"
COL_UNIDADE_STANLEY: str = "Unidade" # Nome cliente Stanley
COL_PEDIDO_COMPRA: str = "Pedido de Compra" # Extraído
COL_VALOR_PRODUTOS: str = "Valor Produtos"
COL_FRETE: str = "Frete"
COL_TOTAL_NOTA: str = "Total da Nota"
COL_LUCRO: str = "Lucro"
COL_TRANSPORTADORA: str = "Transportadora"
COL_CHAVE_ACESSO: str = "Chave de Acesso"
COL_OBSERVACOES_NOTA: str = "Observações da Nota"



######################################################################################



# Stanley Produtos Específico
COL_COMPRA_STANLEY: str = "Compra" # Pedido Compra extraído
COL_PRECO_UNITARIO: str = "Preço Unitário"
COL_MARGEM: str = "Margem"
COL_TOTAL_VENDA: str = "Total Venda" # Total do item

# Stanley Faturamento por Unidade
COL_FATURAMENTO_PRODUTOS: str = "Faturamento em Produtos"


######################################################################################



# Orçamento Específico
COL_CUSTO_TOTAL: str = "Custo Total" # Custo total dos itens
COL_PRECO_TOTAL: str = "Preço Total" # Preço total dos itens sem desc. geral
COL_VALOR_EM_PRODUTOS: str = "Valor em Produtos" # Total Venda bruto
COL_DESCONTO: str = "Desconto" # Desconto geral da venda
COL_VALOR_FINAL: str = "Valor Final" # Valor final da venda



######################################################################################



# Ligeirinho Específico
COL_DATA_HORA: str = "Data e Hora"
COL_VALOR_FRETE: str = "Valor Frete"



######################################################################################



# --- Nomes de Colunas Internas (para cálculo/processamento) ---
# Usadas para buscar dados brutos antes de calcular/renomear
COL_CUSTO_ORIGINAL: str = "CUSTO" # Custo direto do DB
COL_QUANTIDADE_RAW: str = "_QUANTIDADE_RAW_DB" # Quantidade antes de formatar
COL_V_TOT: str = "_V_TOT_DB" # Valor total do item (VENDASPRODUTOS)
COL_MERCADORIA_ORIGINAL: str = "_MERCADORIA_ORIGINAL_DB" # Nome original (Controlados)
COL_UNIDADE_DESC: str = "_UNIDADE_DESC_DB" # Descrição da unidade (Controlados)
COL_INFO_COMPLEMENTARES: str = "_INFO_COMPLEMENTARES_DB" # Campo obs NFE (Stanley)



######################################################################################



# --- Configuração Leitura Excel "Informes" (LÓGICA ORIGINAL DO BACKUP) ---
INFORMES_SKIP_ROWS: int = 2
# Índices das colunas a serem REMOVIDAS (0-based) após ler com skiprows
INFORMES_COLS_TO_DROP_INDICES: Tuple[int, ...] = (0, 2, 3, 5, 6, 7, 8, 9)
# Nomes temporários atribuídos às colunas restantes (antes de dropar 'PRECIO')
_INFORMES_TEMP_COL_NAMES: Tuple[str, ...] = ('Cod PY', 'Produto', 'Marca', 'Vendas PY', 'Estoque PY', 'PRECIO')
# Nome da coluna temporária a ser dropada no final
_INFORMES_COL_TO_DROP_NAME: str = 'PRECIO'
# Nomes finais desejados para as 5 colunas restantes (usando constantes COL_*)
# A ordem DEVE corresponder à ordem após drops e antes do drop de 'PRECIO'
INFORMES_FINAL_COL_NAMES: Tuple[str, ...] = (COL_CODIGO_PY, COL_PRODUTO_PY, COL_MARCA_PY, COL_VENDAS_PY, COL_ESTOQUE_PY)



######################################################################################



# --- Textos UI (Interface do Usuário) ---
TEXTO_UPLOAD_INFORMES: str = "Atualização do **Informes**"
TEXTO_INFO_UPLOAD: str = "⬆️ Faça upload do Informes para análises do Paraguai e Geral."
TEXTO_ERRO_UPLOAD: str = "⚠️ Arquivo inválido ou formato incorreto."
TEXTO_ERRO_LEITURA_EXCEL: str = "⚠️ Erro ao processar o arquivo Excel 'Informes': {e}"
TEXTO_NENHUM_DADO: str = "ℹ️ Nenhum dado encontrado com os filtros selecionados."
TEXTO_ERRO_CARREGAR_DADOS: str = "❌ Erro ao carregar dados do banco: {e}"
TEXTO_ERRO_CONEXAO_BD: str = "❌ Erro: Não foi possível conectar ao banco de dados."
TEXTO_DIGITE_CODIGO_ORCAMENTO: str = "ℹ️ Digite um código de orçamento para visualizar."
TEXTO_ORCAMENTO_NAO_ENCONTRADO: str = "⚠️ Orçamento não encontrado para o código {codigo}."
TEXTO_EM_CONSTRUCAO: str = "🚧 EM CONSTRUÇÃO"



######################################################################################



# Ajuste manual do valor do Frete Ligeirinho
ARQUIVO_AJUSTE = "ajuste.txt"



######################################################################################

# --- Constantes para Aba INFOSERVE ---

INFOSERVE_PASTA_DADOS: str = "infoserve" # CONFIRMADO: Nome da pasta onde estão os TXT
INFOSERVE_ARQUIVO_MOVTO: str = "movto_productos.txt"
INFOSERVE_ARQUIVO_CLIENTES: str = "lista_de_clientes.txt" # CORRIGIDO: Nome exato do arquivo de clientes
INFOSERVE_ARQUIVO_ESTOQUE: str = "lista_del_stock.txt"
INFOSERVE_ENCODING: str = "latin1"
INFOSERVE_SKIPROWS: int = 7 # Linhas a pular no início dos 3 arquivos

# Larguras EXATAS do script original
INFOSERVE_MOVTO_WIDTHS: List[int] = [15, 9, 7, 18, 4, 7, 17, 30, 8, 11, 12, 5, 5, 9]
INFOSERVE_CLIENTES_WIDTHS: List[int] = [13, 28] # CORRIGIDO: Larguras exatas do script para clientes
INFOSERVE_ESTOQUE_WIDTHS: List[int] = [10, 60] # CORRIGIDO: Larguras exatas do script para estoque

# Nomes das colunas FINAIS desejadas (após toda limpeza e merges, conforme script original)
# O script original parecia focar nestas:
COL_IS_DATA: str = "Data"
# COL_IS_HORA: str = "Hora" # Script original removia Hora
COL_IS_COD_CLIENTE: str = "Cód. Cliente" # Nome final após rename
COL_IS_NOME_CLIENTE: str = "Cliente" # Nome final após rename
COL_IS_NOTA: str = "Nota"
COL_IS_COD_PRODUTO: str = "Cód. Produto" # Nome final após rename
COL_IS_NOME_PRODUTO: str = "Produto" # Nome final após rename
COL_IS_QTD: str = "Quantidade" # Nome final após rename e cálculo
# COL_IS_REFERENCIA: str = "Referência" # Script original removia Referencia
# COL_IS_CUSTO_NF: str = "Custo NF" # Script original removia Custo N.F

# Textos da UI para Infoserve (Manter como estavam ou ajustar se necessário)
TEXTO_IS_TITULO: str = "Relatório de Movimentação de Produtos (Infoserve)"
TEXTO_IS_DESCRICAO: str = f"Dados extraídos dos arquivos TXT ({INFOSERVE_ARQUIVO_MOVTO}, {INFOSERVE_ARQUIVO_CLIENTES}, {INFOSERVE_ARQUIVO_ESTOQUE})."
TEXTO_IS_ERRO_ARQUIVO_NAO_ENCONTRADO: str = "⚠️ **Erro:** Arquivo '{filename}' não encontrado na pasta '{C.INFOSERVE_PASTA_DADOS}'. Verifique o nome e o local."
TEXTO_IS_ERRO_LEITURA: str = "⚠️ **Erro:** Falha ao ler o arquivo '{filename}'. Verifique o conteúdo, formato e larguras definidas."
TEXTO_IS_ERRO_PROCESSAMENTO: str = "⚠️ **Erro:** Falha ao processar dados do arquivo '{filename}'."
TEXTO_IS_ERRO_COLUNA_NAO_ENCONTRADA: str = "⚠️ **Erro Interno:** Coluna essencial ('{col_name}') não encontrada após leitura do arquivo '{filename}'. Verifique o arquivo e as larguras (widths)."
TEXTO_IS_ERRO_MERGE: str = "⚠️ **Erro Interno:** Falha ao juntar dados de '{df_name}'. Coluna de junção não encontrada."
TEXTO_IS_SEM_DADOS: str = "ℹ️ Arquivos lidos, mas nenhum dado de movimentação válido foi encontrado após processamento."
TEXTO_IS_PROCESSANDO: str = "Processando arquivos Infoserve..."
TEXTO_IS_DOWNLOAD_BTN: str = "Download Relatório Infoserve (.xlsx)"
TEXTO_IS_FILTROS_EXPANDER: str = "Filtros de Visualização"
TEXTO_IS_FILTRO_DATA_INICIAL: str = "Data Inicial"
TEXTO_IS_FILTRO_DATA_FINAL: str = "Data Final"
TEXTO_IS_FILTRO_CLIENTE: str = "Cliente(s)"
TEXTO_IS_FILTRO_PRODUTO: str = "Produto(s)"
TEXTO_IS_FILTRO_AVISO_DATA: str = "A data final não pode ser anterior à data inicial."
TEXTO_IS_FILTRO_SEM_RESULTADOS: str = "ℹ️ Nenhum registro encontrado com os filtros aplicados."
TEXTO_IS_DOWNLOAD_BTN_FILTRADO: str = "Download Relatório Filtrado (.xlsx)"


######################################################################################


# nome do arquivo para salvar o Bloco de Natos na aba de Compras 
ARQUIVO_ANOTACOES_COMPRAS = "anotacoes_compras.txt"



######################################################################################



# pagina_principal.py, aba Produtos > Entradas
COL_ENT_DATA: str = "Data"
COL_ENT_NOTA: str = "NF"
COL_ENT_CODEMP: str = "Cod BR"
COL_ENT_DESCRICAO: str = "Produto"
COL_ENT_MARCA: str = "Marca"
COL_ENT_QUANTIDADE: str = "Quantidade"
COL_ENT_C_UNIT: str = "Custo Fornecedor"
COL_ENT_CUSTO_M: str = "Custo SaudMed"
COL_ENT_C_SUBTOTAL: str = "Subtotal"



######################################################################################



# --- Constantes para Aba Clientes > Clientes Geral ---
COL_ULT_COMPRA_DATA: str = "Data"
COL_ULT_COMPRA_CLIENTE: str = "Cliente"



######################################################################################



# --- Aba Stanley > Unidades ---
COL_ST_UNIDADE_NOME: str = "Unidade Stanley"
COL_ST_UNIDADE_CIDADE: str = "Cidade"
COL_ST_UNIDADE_UF: str = "Estado"



######################################################################################



# --- Constantes para Relatório de Faturamento Stanley ---
COL_SF_ANO: str = "Ano"
COL_SF_MES: str = "Mês"
COL_SF_FATURAMENTO_PRODUTOS: str = "Faturamento em Produtos"
COL_SF_CUSTO_TOTAL: str = "Custo Total"
COL_SF_LUCRO: str = "Lucro"
COL_SF_MARGEM: str = "Margem"



######################################################################################



# --- Constantes para Relatório de Orçamento/Estoque Stanley ---
# COL_CODIGO_BR: str = "Código BR"
# COL_PRODUTO: str = "Produto"
# COL_QUANTIDADE: str = "Quantidade"
# COL_ESTOQUE_BR: str = "Estoque BR"
COL_DIFERENCA: str = "Diferença" # Acima estão comentados para evitar mais duplicidade (que já tem)



######################################################################################



