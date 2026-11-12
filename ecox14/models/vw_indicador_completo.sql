{{ config(materialized='view') }}

-- A tabela achatada (fato + dimensao) como consulta salva: nao guarda dado,
-- o banco refaz o join na hora, entao nunca fica desatualizada.
select f.*, d.nome, d.uf, d.regiao
from {{ ref('fato_indicador_municipio') }} f
join {{ ref('dim_municipio') }} d using (municipio_id)
