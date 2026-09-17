## Fontes de dados
| Fonte | Formato | Acesso | Extraido | Link |
|---|---|---|---|---|
| SIM (Mortalidade) | CSV | aberto (DATASUS) | 29/08/2026 | https://dadosabertos.saude.gov.br/dataset/sim |
| SINASC (Nascidos Vivos) | CSV | aberto (DATASUS) | 29/08/2026 | https://dadosabertos.saude.gov.br/dataset/sistema-de-informacao-sobre-nascidos-vivos-sinasc |


## Defeitos conhecidos das fontes

### SIM (DATASUS)
- 'TIPOBITO' e constante (so valor 2, obito nao fetal); explica a
  ausencia de ~98% nos campos ligados a gestacao/mae (IDADEMAE,
  ESCMAE, GRAVIDEZ, PESO, PARTO etc) - ausencia estrutural, nao erro.
- 'CB_PRE' esta 100% ausente e com tipo nao suportado; candidata a
  descarte na prata.
- 'ESC' e 'ESC2010' sao duas codificacoes de escolaridade
  (antiga e pos-2010) para o mesmo conceito - redundantes.
- Ausencia real (nao condicionada por tipo de obito): RACACOR (1,3%),
  ESTCIV (4,2%), ASSISTMED (30,4%), NECROPSIA (28,5%), TPPOS (34,4%).
- Campos de investigacao (FONTEINV, DTINVESTIG, CIRCOBITO, ACIDTRAB
  etc) so se aplicam a mortes violentas/investigadas - alta ausencia
  esperada.

### SINASC (DATASUS)
- 'CODPAISRES' e constante (base so tem nascimentos no Brasil).
- 'NATURALMAE', 'CODMUNNATU' e 'CODUFNATU' ausentes juntos em 1,8%
  dos registros - mesmo bloco de informacao (naturalidade da mae)
  faltando nas mesmas linhas.
- Zeros em QTDFILVIVO, QTDFILMORT, QTDPARTNOR, QTDPARTCES, PARIDADE
  sao valores legitimos (ex: primeira gestacao), nao ausencia.
- 'IDADEPAI' ausente em 67,1% e 'DTULTMENST' em 53,2% - esperado
  (pai nem sempre presente no registro; data nem sempre sabida).
- 'SERIESCMAE' (34,3%) e 'CODOCUPMAE' (6,5%) tem ausencia real.

## Decisões de tratamento

### SIM (DATASUS)
- 'CB_PRE' removida: 100% vazia e com tipo nao suportado pelo profiling.
- 'ESC' removida, mantida 'ESC2010' (padrao mais recente do MEC para
  escolaridade) - resolve a redundancia identificada na exploracao.
- 'DTOBITO' e 'DTNASC' convertidas de texto (ddmmaaaa) para tipo data.
- 'idade_anos' criada a partir da decodificacao de 'IDADE' (campo
  composto: 1o digito = unidade, 2 digitos seguintes = quantidade,
  conforme dicionario oficial do SIM).
- 'idade_anos': 56.732 registros marcados como extremos pelo IQR,
  34.721 pelo z-score. A maioria (30.020) sao obitos com idade < 1 ano;
  a distribuicao geral de obitos e concentrada em idade avancada
  (mediana 71 anos), entao o IQR marca obito infantil e infanto-juvenil
  como "extremo" por serem raros relativamente ao resto, nao por serem
  erro. Apenas 9 registros extremos tem idade >= 90 anos (maximo 124
  anos) - plausivel, mantido. Nenhum registro removido: nao ha erro
  comprovado de idade nesta base (faixa 0-130 respeitada em 100% dos
  casos).
- Chave adotada: 'contador' (sequencial da extracao). Nao ha chave
  natural entre registros anonimizados; duplicidade de entidade (mesma
  pessoa registrada duas vezes) nao e verificavel com confianca a
  partir dos campos disponiveis - limitacao documentada, nao resolvida.

### SINASC (DATASUS)
- Base confirmada como nacional: 5.583 municipios distintos, cobrindo
  04/01/2024 a 31/12/2024.
- 'DTNASC', 'DTULTMENST' e 'DTDECLARAC' convertidas de texto
  (ddmmaaaa) para tipo data.
- 'PESO', 'APGAR1', 'APGAR5', 'IDADEMAE', 'QTDFILVIVO', 'QTDFILMORT'
  e 'SEMAGESTAC' convertidas para numero.
- 'APGAR1' (1.962) e 'APGAR5' (21) fora da escala 0-10 removidos -
  erro comprovado, escala fechada por definicao clinica.
- 'PESO' fora de 200-7000g removido: 131 registros - erro comprovado
  (limite biologico de sobrevivencia ao parto).
- 'PESO': 84.037 extremos por IQR, 36.620 por z-score. Nao sao erro:
  70.453 sao baixo peso (<2500g, categoria clinica real -
  prematuridade) e 13.584 sao alto peso (>4000g, macrossomia). O IQR
  marca mais que o z-score porque a distribuicao de peso e assimetrica
  para baixo peso, o mesmo padrao observado na idade do SIM. Mantidos
  e sinalizados, nao removidos.
- Chave adotada: 'contador' (sequencial da extracao). Mesma limitacao
  do SIM: duplicidade de entidade nao e verificavel com confianca.

## Atributos derivados

### PESO_faixa (SINASC)
Faixa de peso ao nascer (baixo peso / peso normal / alto peso), a partir
de cortes clinicos fixos (2500g e 4000g), nao por quartil. Serve para
categorizar recem-nascidos em grupos de risco reconhecidos na literatura
de saude publica. Ausente quando PESO ja era ausente na fonte (219 casos).

### regiao (populacao IBGE)
Macrorregiao do Brasil, derivada do primeiro digito do codigo do
municipio (IBGE). Serve como chave de agregacao para responder a
pergunta norteadora por regiao.

### taxa_mortalidade_infantil (Ouro, combinacao de fontes)
Obitos com idade_anos == 0 (SIM) dividido por nascidos vivos (SINASC),
por 1000 nascidos vivos, agregado por regiao. Responde diretamente a
primeira metade da pergunta norteadora. Calculada somando numerador e
denominador de todos os municipios da regiao antes de dividir (nao e
media das taxas municipais).

### taxa_natalidade (Ouro, combinacao de fontes)
Nascidos vivos (SINASC) dividido por populacao residente estimada
(IBGE), por 1000 habitantes, agregado por regiao. Responde a segunda
metade da pergunta norteadora.

## Resultado (2024)
Norte e Nordeste apresentam as maiores taxas de mortalidade infantil
(15,68 e 13,55 por mil) e tambem as maiores taxas de natalidade (14,23
e 11,68 por mil), enquanto Sul e Sudeste apresentam os menores valores
em ambos os indicadores. A diferenca entre a regiao com maior e menor
mortalidade infantil (Norte vs Sul) e de aproximadamente 50%.

## Limitacoes
17 registros (12 no SINASC, 5 no SIM) usam codigo de municipio "ignorado"
(UF + 0000, convencao do DATASUS) e ficam fora da agregacao regional por
nao existirem na base de populacao do IBGE - volume irrelevante frente
ao total de ~2,4 milhoes de registros.