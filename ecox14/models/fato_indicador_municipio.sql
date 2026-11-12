-- Fato. Grao: 1 linha = 1 municipio em 1 ano.
-- A origem e o municipio_enriquecido (a juncao da aula 7 ja resolveu quem
-- tem municipio no cadastro); o ano vem da populacao (ano de referencia da
-- estimativa do IBGE).
-- populacao, nascimentos e obitos_infantis podem ser somados entre municipios;
-- as taxas NAO (para uma regiao, soma-se numerador e denominador e divide-se
-- depois). O where e o filtro de integridade da fato.
select
    m.codigo_municipio_6        as municipio_id,
    p.ano                       as ano,
    m.populacao                 as populacao,
    m.nascimentos               as nascimentos,
    m.obitos_infantis           as obitos_infantis,
    m.taxa_natalidade           as taxa_natalidade,
    m.taxa_mortalidade_infantil as taxa_mortalidade_infantil
from {{ source('prata', 'municipio_enriquecido') }} m
left join {{ source('prata', 'populacao') }} p using (codigo_municipio_6)
where m.codigo_municipio_6 is not null
