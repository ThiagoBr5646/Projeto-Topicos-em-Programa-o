-- A tabela achatada da aula 7, reconstruida a partir da estrela.
-- View: nao guarda dado, roda o join na hora e nunca fica desatualizada.
-- Grao: o mesmo da fato (uma sessao por linha).

{{ config(materialized='view') }}

select
    f.*,
    p.genero,
    p.idade,
    p.peso_kg,
    p.altura_m,
    p.imc,
    p.gordura_pct,
    p.bpm_repouso,
    p.agua_litros,
    p.treinos_por_semana,
    p.nivel_experiencia,
    p.experiencia,
    t.tipo_treino,
    t.codigo_compendio,
    t.atividade_compendio,
    t.met,
    t.met_estimado
from {{ ref('fato_sessao') }} f
join {{ ref('dim_praticante') }} p using (praticante_id)
join {{ ref('dim_treino') }} t using (treino_id)
