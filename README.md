## Fontes de dados
| Fonte | Formato | Acesso | Extraido | Link |
|---|---|---|---|---|
| SIM (Mortalidade) | CSV | aberto (DATASUS) | 29/08/2026 | https://svs.aids.gov.br/dantps/centrais-de-conteudos/dados-abertos/sim/ |
| SINASC (Nascidos Vivos) | CSV | aberto (DATASUS) | 29/08/2026 | https://svs.aids.gov.br/dantps/centrais-de-conteudos/dados-abertos/sinasc/ |


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