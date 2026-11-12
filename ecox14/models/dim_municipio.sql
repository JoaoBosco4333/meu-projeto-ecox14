-- Dimensao: 1 linha = 1 municipio (5.571).
-- A UF vem embutida no nome da fonte ("Ariquemes - RO"); aqui ela vira
-- coluna propria e o nome fica sem ela.
select
    codigo_municipio_6                              as municipio_id,
    codigo_municipio                                as codigo_ibge,
    regexp_replace(municipio, ' - [A-Z]{2}$', '')   as nome,
    regexp_extract(municipio, ' - ([A-Z]{2})$', 1)  as uf,
    regiao
from {{ source('prata', 'populacao') }}
