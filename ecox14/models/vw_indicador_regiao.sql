{{ config(materialized='view') }}

-- A resposta da pergunta, por regiao e ano. Soma numerador e denominador no
-- grao de municipio e so depois divide (nao e media das taxas municipais).
select
    regiao,
    ano,
    cast(sum(populacao) as bigint)                    as populacao,
    cast(sum(nascimentos) as bigint)                  as nascimentos,
    cast(sum(obitos_infantis) as bigint)              as obitos_infantis,
    sum(nascimentos) * 1000.0 / sum(populacao)        as taxa_natalidade,
    sum(obitos_infantis) * 1000.0 / sum(nascimentos)  as taxa_mortalidade_infantil
from {{ ref('vw_indicador_completo') }}
group by regiao, ano
