## Fontes de dados
| Fonte | Formato | Acesso | Extraído | Link |
|---|---|---|---|---|
| SIM (Mortalidade) | CSV | aberto (DATASUS) | 29/08/2026 | https://dadosabertos.saude.gov.br/dataset/sim |
| SINASC (Nascidos Vivos) | CSV | aberto (DATASUS) | 29/08/2026 | https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc |
| População residente estimada por município (IBGE) | JSON (API), gravado como CSV | aberto (API de Agregados/SIDRA, tabela 6579, variável 9324) | 17/09/2026 | https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos/2024/variaveis/9324?localidades=N6[all] |

SIM e SINASC foram baixados manualmente (recorte de 2024). A população do IBGE é
ingerida por script (`src/ingerir_ibge_populacao.py`). A proveniência de cada
extração fica registrada em `proveniencia.jsonl`, na bronze e na prata.


## Defeitos conhecidos das fontes

### SIM (DATASUS)
- 'TIPOBITO' é constante (só valor 2, óbito não fetal); explica a ausência de ~98%
  nos campos ligados à gestação/mãe (IDADEMAE, ESCMAE, GRAVIDEZ, PESO, PARTO etc.) -
  ausência estrutural, não erro.
- 'CB_PRE' está 100% ausente e com tipo não suportado; candidata a descarte na prata.
- 'ESC' e 'ESC2010' são duas codificações de escolaridade (antiga e pós-2010) para o
  mesmo conceito - redundantes.
- Ausência real (não condicionada por tipo de óbito): RACACOR (1,3%), ESTCIV (4,2%),
  ASSISTMED (30,4%), NECROPSIA (28,5%), TPPOS (34,4%).
- Campos de investigação (FONTEINV, DTINVESTIG, CIRCOBITO, ACIDTRAB etc.) só se
  aplicam a mortes violentas/investigadas - alta ausência esperada.

### SINASC (DATASUS)
- 'CODPAISRES' é constante (base só tem nascimentos no Brasil).
- 'NATURALMAE', 'CODMUNNATU' e 'CODUFNATU' ausentes juntos em 1,8% dos registros -
  mesmo bloco de informação (naturalidade da mãe) faltando nas mesmas linhas.
- Zeros em QTDFILVIVO, QTDFILMORT, QTDPARTNOR, QTDPARTCES, PARIDADE são valores
  legítimos (ex.: primeira gestação), não ausência.
- 'IDADEPAI' ausente em 67,1% e 'DTULTMENST' em 53,2% - esperado (pai nem sempre
  presente no registro; data nem sempre sabida).
- 'SERIESCMAE' (34,3%) e 'CODOCUPMAE' (6,5%) têm ausência real.

### IBGE (população por município)
- O código do município tem 7 dígitos (com dígito verificador); o DATASUS usa 6
  (sem o dígito). Sem ajuste, as chaves não casam.
- A tabela não traz a região do município; ela precisa ser derivada.
- A API devolve 5.571 unidades: os 5.570 anteriores mais Boa Esperança do Norte (MT),
  município criado recentemente. A conta inclui o Distrito Federal e Fernando de Noronha.


## Decisões de tratamento

### SIM (DATASUS)
- 'CB_PRE' removida: 100% vazia e com tipo não suportado pelo profiling.
- 'ESC' removida, mantida 'ESC2010' (padrão mais recente do MEC para escolaridade) -
  resolve a redundância identificada na exploração.
- 'ESC2010' tipada como categoria ordenada (0 = sem escolaridade até 5 = superior
  completo). O código 9 (ignorado) fica fora da escala e vira ausente: 139.266 registros
  com código 9 na fonte.
- 'DTOBITO' e 'DTNASC' convertidas de texto (ddmmaaaa) para tipo data.
- 'idade_anos' criada a partir da decodificação de 'IDADE' (campo composto: 1º dígito
  = unidade, 2 dígitos seguintes = quantidade, conforme dicionário oficial do SIM).
- 'idade_anos': 56.732 registros marcados como extremos pelo IQR, 34.721 pelo z-score.
  A maioria (30.020) são óbitos com idade < 1 ano; a distribuição geral de óbitos é
  concentrada em idade avançada (mediana 71 anos), então o IQR marca óbito infantil e
  infanto-juvenil como "extremo" por serem raros relativamente ao resto, não por serem
  erro. Apenas 9 registros extremos têm idade >= 90 anos (máximo 124 anos) - plausível,
  mantido. Nenhum registro removido: não há erro comprovado de idade nesta base (faixa
  0-130 respeitada em 100% dos casos).
- Chave adotada: 'contador' (sequencial da extração). Não há chave natural entre
  registros anonimizados; duplicidade de entidade (mesma pessoa registrada duas vezes)
  não é verificável com confiança a partir dos campos disponíveis - limitação
  documentada, não resolvida.

### SINASC (DATASUS)
- Base nacional: 5.583 códigos de município de residência distintos (inclui códigos de
  "município ignorado"), cobrindo 04/01/2024 a 31/12/2024.
- 'DTNASC', 'DTULTMENST' e 'DTDECLARAC' convertidas de texto (ddmmaaaa) para tipo data.
- 'PESO', 'APGAR1', 'APGAR5', 'IDADEMAE', 'QTDFILVIVO', 'QTDFILMORT' e 'SEMAGESTAC'
  convertidas para número.
- 'ESCMAE2010' tipada como categoria ordenada (0 = sem escolaridade até 5 = superior
  completo). O código 9 (ignorado) fica fora da escala e vira ausente: 5.740 registros
  com código 9 na fonte.
- 'APGAR1' (1.962) e 'APGAR5' (21) fora da escala 0-10 removidos - erro comprovado,
  escala fechada por definição clínica.
- 'PESO' fora de 200-7000 g removido: 131 registros - erro comprovado (limite
  biológico de sobrevivência ao parto).
- 'PESO': 84.037 extremos por IQR, 36.620 por z-score. Não são erro: 70.453 são baixo
  peso (< 2.500 g, categoria clínica real - prematuridade) e 13.584 são alto peso
  (> 4.000 g, macrossomia). O IQR marca mais que o z-score porque a distribuição de
  peso é assimétrica para baixo peso, o mesmo padrão observado na idade do SIM.
  Mantidos e sinalizados, não removidos.
- Chave adotada: 'contador' (sequencial da extração). Mesma limitação do SIM:
  duplicidade de entidade não é verificável com confiança.

### IBGE (população por município)
- 'ano' e 'populacao' convertidos para Int64.
- 'codigo_municipio_6' criada: remove o dígito verificador do código de 7 dígitos,
  ficando compatível com o código do DATASUS.
- 'regiao' derivada do primeiro dígito do código do município (1 Norte, 2 Nordeste,
  3 Sudeste, 4 Sul, 5 Centro-Oeste). O ano fica como inteiro, não como data.


## Junção

SIM e SINASC foram enriquecidos com o cadastro de municípios (tabela de população do
IBGE) pela chave CODMUNRES (DATASUS) = codigo_municipio_6 (IBGE sem dígito verificador),
com how=left e validate=many_to_one. As tabelas de eventos mantêm o grão original
(1 óbito / 1 nascimento por linha) e ganham município, região e população.
CODMUNRES foi convertida para Int64, o mesmo tipo do cadastro, antes de juntar.

| Tabela | Linhas antes | Linhas depois | Sem par |
|---|---|---|---|
| SIM | 1.532.015 | 1.532.015 | 2.290 (0,15%) |
| SINASC | 2.387.211 | 2.387.211 | 49 (0,002%) |

Antes da junção, 5.570 códigos existiam nas duas fontes; 25 (SIM) e 12 (SINASC) só
existiam no DATASUS; 1 só existia no cadastro. Nenhuma linha tinha chave vazia.

Resultado da junção: `sim_enriquecido`, `sinasc_enriquecido` (grão de evento) e
`municipio_enriquecido` (1 linha por município, 5.571 linhas, com contagens e taxas).

### Quem não casou
- SIM: 2.290 linhas em 25 códigos distintos. Todos têm o formato código da UF + 0000
  (RJ, SP, BA, MG, PE, ES, GO, PR, MA, PA e outras 15 UFs), que indica município
  ignorado dentro da UF. Mantidas na tabela com município, região e população
  ausentes; ficam fora das contagens por município e região. Entre elas há 6 óbitos
  infantis (30.020 óbitos com idade < 1 ano, 30.014 usados nas taxas).
- SINASC: 49 linhas em 12 códigos distintos. Todos têm o formato código da UF + 0000
  (RJ, AM, GO, SP, ES, PE, MG, RR, PR, BA, AL, SC). Mesmo tratamento do SIM.
- Boa Esperança do Norte (MT), município criado recentemente (desmembrado de Sorriso
  e Nova Ubiratã), consta no cadastro do IBGE mas não tem registro no SIM nem no SINASC
  de 2024. Recebe 0 nascimentos e 0 óbitos infantis. O zero possivelmente reflete como
  o DATASUS registrou o município em 2024, não ausência real de nascimentos. Impacto
  na região: menos de 0,04% da população do Centro-Oeste.

### Armadilha do grão
Somar 'populacao' na tabela de eventos repete cada município uma vez por linha: dá
2,0 trilhões no SIM e 2,7 trilhões no SINASC. A soma correta, no cadastro (uma linha
por município), é 212.583.750. Por isso as taxas são calculadas no grão de município.


## Atributos derivados

### PESO_faixa (SINASC)
Faixa de peso ao nascer a partir de cortes clínicos fixos, não por quartil: baixo peso
(menos de 2.500 g), peso normal (2.500 a 3.999 g) e alto peso (4.000 g ou mais). Serve
para categorizar recém-nascidos em grupos de risco reconhecidos na saúde pública.
Ausente apenas quando PESO já era ausente na fonte.

### regiao (população IBGE)
Macrorregião do Brasil, derivada do primeiro dígito do código do município. É a chave
de agregação para responder à pergunta norteadora por região.

### taxa_natalidade (município_enriquecido)
Nascidos vivos (SINASC) dividido pela população residente estimada (IBGE), por 1.000
habitantes. Só existe depois da junção: depende de duas fontes na mesma linha.
Responde à segunda metade da pergunta norteadora.

### taxa_mortalidade_infantil (município_enriquecido)
Óbitos com idade_anos == 0 (SIM) dividido por nascidos vivos (SINASC), por 1.000
nascidos vivos. Responde à primeira metade da pergunta norteadora.

Por região, numerador e denominador são somados no grão de município e só depois
divididos (não é média das taxas municipais).


## Modelo da camada Ouro

A Ouro mora num banco DuckDB, que é um arquivo só: `dados/ouro/projeto.duckdb`. Dentro
dele há dois esquemas: `prata` (os Parquets da Prata, como estão; criado pela etapa
`carga`) e `ouro` (nasce da prata, dentro do banco, construído pelo dbt na etapa
`modelagem`). O modelo é um esquema estrela: uma fato no meio, com os números, e uma
dimensão em volta, com as palavras pelas quais se agrupa e filtra.

**Grão: uma linha de `fato_indicador_municipio` é um município em um ano.**

Dessa frase decorre o resto:
- a chave primária da fato é o par (`municipio_id`, `ano`), e não o município sozinho;
- entre municípios do mesmo ano, `populacao`, `nascimentos` e `obitos_infantis` podem ser
  somados. As taxas não: para uma região, somam-se numerador e denominador e só depois se
  divide. `populacao` também não se soma entre anos (é um estoque, não um fluxo);
- duplicata é o mesmo município no mesmo ano duas vezes, e nada além disso.

| Tabela | Tipo | Uma linha é | Vem de |
|---|---|---|---|
| `ouro.dim_municipio` | dimensão | um município (5.571) | `prata.populacao` |
| `ouro.fato_indicador_municipio` | fato | um município em um ano | `prata.municipio_enriquecido` (+ `ano` de `prata.populacao`) |
| `ouro.vw_indicador_completo` | view | um município em um ano, com nome, UF e região | fato + dimensão |
| `ouro.vw_indicador_regiao` | view | uma região em um ano | `vw_indicador_completo` |

Como as tabelas se ligam: `fato_indicador_municipio.municipio_id` aponta para
`dim_municipio.municipio_id` (muitos para um). `municipio_id` é o código de 6 dígitos, o
mesmo `codigo_municipio_6` que liga o DATASUS ao IBGE; o código completo, de 7 dígitos,
fica em `dim_municipio.codigo_ibge`.

```
dim_municipio                         fato_indicador_municipio
  municipio_id  <-------------------   municipio_id
  codigo_ibge                           ano
  nome, uf, regiao                      populacao, nascimentos, obitos_infantis
                                        taxa_natalidade, taxa_mortalidade_infantil
```

Decisões de modelagem:
- A `municipio_enriquecido` (saída do enriquecimento) é a entrada da fato: ela já resolveu
  quem tem município no cadastro, então esse trabalho não é refeito. A tabela achatada
  deixa de ser mantida como arquivo e vira a view `vw_indicador_completo`, com o mesmo
  resultado.
- A UF vem embutida no nome da fonte ("Ariquemes - RO"); na dimensão ela vira a coluna `uf`
  e o `nome` fica sem ela.
- Não há `dim_tempo`: o projeto só usa o ano, que fica na fato. Como `ano` faz parte do
  grão, acrescentar outros anos não muda as tabelas, só acrescenta linhas.
- Região é atributo de `dim_municipio`; não há `dim_regiao`.
- `vw_indicador_regiao` existe para que ninguém calcule a taxa regional como média das
  taxas municipais: ela soma numerador e denominador e só então divide. É a consulta que
  responde à pergunta norteadora.
- `sim` e `sinasc` (sem o enriquecimento) não são carregados no banco: as versões
  enriquecidas têm as mesmas linhas e as mesmas colunas, mais 4. Carregar as duas seria
  guardar tudo duas vezes (o banco passaria de cerca de 330 MB para cerca de 630 MB).
- Municípios com código ignorado (UF + 0000) não existem no cadastro e ficam fora da fato
  (49 nascimentos e 6 óbitos infantis); continuam em `prata.sinasc_enriquecido` e
  `prata.sim_enriquecido`.
- Boa Esperança do Norte (MT) tem população ausente na fonte do IBGE: `populacao`,
  `taxa_natalidade` e `taxa_mortalidade_infantil` ficam nulas na fato (nascimentos e óbitos
  são 0). A soma da população da região ignora o nulo.

A etapa `modelagem` confere o modelo depois que o dbt termina e para o pipeline se algo
não fecha:
nenhum município repetido no mesmo ano; nenhuma linha da fato sem município na dimensão
(fato órfão); nenhuma linha sem ano; a dimensão com 5.571 municípios, sem repetição e sem
região ausente; a fato e a view com o mesmo número de linhas da `municipio_enriquecido`;
e as contagens da fato batendo com os eventos da Prata (2.387.162 nascimentos e 30.014
óbitos infantis com município).

Consultas de exemplo (a segunda usa o join da estrela):

```sql
SELECT regiao, taxa_natalidade, taxa_mortalidade_infantil
FROM ouro.vw_indicador_regiao
WHERE ano = 2024
ORDER BY taxa_mortalidade_infantil DESC;

SELECT d.uf, SUM(f.nascimentos) AS nascimentos
FROM ouro.fato_indicador_municipio f
JOIN ouro.dim_municipio d USING (municipio_id)
WHERE f.ano = 2024
GROUP BY d.uf
ORDER BY nascimentos DESC
LIMIT 5;
```

Para rodar uma consulta a partir do Python (`read_only=True` evita travar o arquivo para
quem for abri-lo depois):

```python
import duckdb
con = duckdb.connect("dados/ouro/projeto.duckdb", read_only=True)
print(con.execute("SELECT * FROM ouro.vw_indicador_regiao").df())
```


## Construção da Ouro com dbt

Desde a Aula 10, quem constrói a Ouro é o dbt (data build tool), e não o Python. Cada
ferramenta fica com o que sabe fazer:
- `src/carga.py` (Python) abre o banco e carrega os Parquets no esquema `prata`: ler
  arquivo não é transformação, então continua em Python;
- `ecox14/` (dbt) guarda um arquivo `.sql` por tabela da Ouro, só com o `select`. O dbt
  coloca o `create` em volta, descobre a ordem de execução e entrega o SQL ao DuckDB, que
  é quem executa. O dbt não processa nenhuma linha.

```
ecox14/
  dbt_project.yml                    nome do projeto; padrão: todo modelo vira tabela
  profiles.yml                       como conectar: ../dados/ouro/projeto.duckdb, esquema ouro
  models/
    sources.yml                      origens: tabelas do esquema prata que o dbt não constrói
    dim_municipio.sql                tabela
    fato_indicador_municipio.sql     tabela
    vw_indicador_completo.sql        view
    vw_indicador_regiao.sql          view
```

A ordem de execução não está escrita em lugar nenhum: sai das referências.
`{{ source('prata', 'populacao') }}` aponta para uma tabela que o dbt não constrói;
`{{ ref('fato_indicador_municipio') }}` aponta para outro modelo e cria a dependência. Daí o
dbt deduz: primeiro a dimensão e a fato, depois `vw_indicador_completo`, por último
`vw_indicador_regiao`. Trocar tabela por view (ou o contrário) é mudar uma palavra, no
`{{ config(materialized='view') }}` do topo do arquivo.

O `profiles.yml` fica dentro de `ecox14/` (o dbt procura primeiro na pasta de onde roda)
porque o DuckDB não tem usuário nem senha: não há segredo ali, e quem clonar o repositório
não precisa configurar nada em `C:\Users\...\.dbt`. O caminho do banco é relativo a
`ecox14/`, que é de onde o dbt deve rodar.

Comandos, de dentro de `ecox14/` e com o ambiente virtual ativado:

```
dbt debug                            # mostra qual profile esta lendo e testa a conexao
dbt run                              # constroi tudo
dbt run --select dim_municipio+      # so a dimensao e o que depende dela
```

O SQL que o dbt de fato envia ao banco fica legível em `ecox14/target/run/ecox14/models/`.
Dois programas não podem ficar com o arquivo do banco abertos ao mesmo tempo: se aparecer
"file is locked", feche a outra conexão (DBeaver, extensão do VS Code, outro terminal) e
rode de novo.

A migração não mudou o resultado: as quatro tabelas e views saíram com as mesmas linhas, as
mesmas colunas e os mesmos tipos de quando eram construídas por `carga.construir_ouro` (que
continua no arquivo, sem ser chamada, para comparação).


## Prévia do resultado (2024)

| Região | Natalidade (por 1.000 hab.) | Mortalidade infantil (por 1.000 nascidos vivos) |
|---|---|---|
| Norte | 14,23 | 15,68 |
| Centro-Oeste | 12,61 | 12,62 |
| Nordeste | 11,68 | 13,55 |
| Sul | 10,82 | 10,41 |
| Sudeste | 10,19 | 11,73 |

- Mortalidade infantil: maior no Norte (15,68) e no Nordeste (13,55), menor no Sul
  (10,41) e no Sudeste (11,73). O Norte tem taxa cerca de 50% maior que a do Sul.
- Natalidade: maior no Norte (14,23) e no Centro-Oeste (12,61), menor no Sudeste
  (10,19) e no Sul (10,82).
- Taxas nacionais implícitas: 12,6 óbitos infantis por 1.000 nascidos vivos e 11,2
  nascimentos por 1.000 habitantes.
- São taxas brutas observadas. Nenhum teste estatístico foi aplicado, então a prévia
  ainda não responde se a diferença entre regiões é "significativa".
- Estes mesmos valores saem do banco, de `ouro.vw_indicador_regiao`, calculados em SQL.


## Limitações
- 2.290 linhas do SIM (0,15%) e 49 do SINASC (0,002%) usam código de município
  ignorado (UF + 0000) e ficam fora das contagens por município e região, por não
  existirem na base de população do IBGE.
- Município e região são os de residência (SIM: do falecido; SINASC: da mãe), não os
  de ocorrência.
- A população é estimativa do IBGE para 2024, não contagem.
- Boa Esperança do Norte (MT) aparece com 0 nascimentos e 0 óbitos infantis; o zero
  pode ser efeito do registro em 2024 (ver "Quem não casou").
- Sem chave natural, duplicidade de entidade nos registros anonimizados não é
  verificável.


## Como reproduzir
SIM e SINASC (CSV de 2024) são baixados manualmente do portal e colocados em
`dados/bronze/`. Com o ambiente virtual ativado, a partir da raiz do projeto:

```
pip install -r requirements.txt
python src/pipeline.py
```

O pipeline roda as etapas em ordem (ingestão, transformação, enriquecimento, carga) e grava o
registro da execução em `pipeline.log` (tela e arquivo ao mesmo tempo; o arquivo não vai
para o GitHub). Se uma etapa falhar, o erro completo fica no log e o pipeline para.

Para retomar a partir de uma etapa, sem refazer as anteriores:

```
python src/pipeline.py enriquecimento
```

Etapas disponíveis: `ingestao`, `transformacao`, `enriquecimento`, `carga`, `modelagem`.
Para reconstruir só a camada Ouro (sem recarregar a Prata), rode
`python src/pipeline.py modelagem`.

A etapa `carga` (`src/carga.py`) cria o banco `dados/ouro/projeto.duckdb` e carrega a Prata
no esquema `prata`. A etapa `modelagem` roda o dbt (`ecox14/`), que constrói a Ouro no
esquema `ouro` (ver "Construção da Ouro com dbt"), e depois confere o resultado. A saída do
dbt também vai para o `pipeline.log`. Os pacotes `duckdb`, `dbt-core` e `dbt-duckdb` estão
no `requirements.txt`. Rodar de novo é seguro: as tabelas da prata são refeitas com
`CREATE OR REPLACE` e os modelos do dbt também, sem duplicar nada. A primeira execução da
carga gera um arquivo de cerca de 330 MB; ao rodar a carga de novo, o DuckDB não devolve ao
disco o espaço das tabelas substituídas, então o arquivo pode chegar a cerca de 650 MB e para
de crescer aí (a modelagem não aumenta o arquivo).
Para voltar ao tamanho mínimo, feche qualquer programa que esteja com o banco aberto, apague
`dados/ouro/projeto.duckdb` e rode `python src/pipeline.py carga`. Como o Ouro é
reconstruído a partir da prata, apagar o banco não perde nada.

A prata é reconstruível: apagar `dados/prata/` e rodar `python src/pipeline.py
transformacao` recria tudo a partir da bronze.

Os CSV do SIM e do SINASC (cerca de 550 MB cada) cabem na memória de um computador
comum só se forem tratados com cuidado. Ler cada um de uma vez pedia mais de 3 GB livres
e falhava com "out of memory". Por isso:
- `limpeza.ler_csv_por_partes` lê o CSV em partes de 100 mil linhas e monta o resultado
  coluna por coluna, com os mesmos tipos e valores de uma leitura única;
- `limpeza.filtrar_linhas` remove linhas inválidas sem copiar o DataFrame inteiro (e não
  faz nada quando não há o que remover);
- em `enriquecer.juntar`, o left join com `validate="many_to_one"` roda só sobre a coluna
  da chave, e as colunas do cadastro são acrescentadas à tabela de eventos.

O resultado de todas essas mudanças foi conferido contra a versão anterior (mesmas
colunas, tipos e valores). O pico de memória fica em torno de 2 a 3 GB por etapa. A carga
usa menos (cerca de 1,5 GB): o DuckDB lê o Parquet em fluxo, sem abrir a tabela inteira
na memória do Python.
