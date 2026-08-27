## Fontes de dados
| Fonte | Formato | Acesso | Extraido | Link |
|---|---|---|---|---|
| Spotify | CSV | token | 20/08/2026 | kaggle.com/... |
| Banco Mundial | JSON | aberto | 20/08/2026 | api.worldbank.org/... |
## Defeitos conhecidos das fontes
- A API do Banco Mundial devolve agregados
regionais junto com os paises.

## Defeitos conhecidos das fontes
### Spotify (Kaggle)
- 'Artist Type' tem espaco no inicio do nome.
- Total, Lead e Feature sao redundantes:
Total = Lead + Feature.
- Debut Year tem N valores ausentes.
### Banco Mundial
- Devolve agregados regionais junto com os paises.
- Nomes de regiao tem espaco no fim.