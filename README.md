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
  completo). O código 9 (ignorado) fica fora da escala e vira ausente: XXXX registros
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
  completo). O código 9 (ignorado) fica fora da escala e vira ausente: YYYY registros
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
python src/ingerir_ibge_populacao.py
python src/transformar_sim.py
python src/transformar_sinasc.py
python src/transformar_populacao.py
python src/enriquecer.py
```

A prata é reconstruível: apagar `dados/prata/` e rodar os scripts de novo recria tudo
a partir da bronze.