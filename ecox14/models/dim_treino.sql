-- Dimensao: o tipo de treino, com o que o Compendio diz dele.
-- Grao: uma linha por tipo de treino (4 hoje).
--
-- O codigo, o MET e a descricao vieram da juncao da aula 7. O filtro
-- "codigo is not null" deixa de fora o treino que nao achou par no
-- Compendio (hoje: nenhum) - e o mesmo filtro da fato_sessao.

select distinct
    treino_chave         as treino_id,
    Workout_Type         as tipo_treino,
    codigo               as codigo_compendio,
    atividade_compendio,
    met,
    met_estimado
from {{ source('prata', 'gym_members_enriquecida') }}
where codigo is not null
